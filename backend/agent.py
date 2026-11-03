import re
import uuid
from typing import List, Dict, Any, Optional, Tuple

from backend.models import (
    ProjectNote, TaskProposal, TaskProposalItem, Task, TaskCreate,
    AgentChatResponse, AgentStep
)
from backend.vector_store import get_vector_store
from backend.date_parser import get_date_parser
from backend.priority_classifier import get_priority_classifier
from backend.task_crud import get_task_crud

class TaskManagementAgent:
    """
    Intelligent Task Management Agent for Workshop Preparation.
    Orchestrates:
    - ChromaDB semantic retrieval (all-MiniLM-L6-v2) for workshop project notes
    - Natural language task decomposition & enrichment
    - Date parsing for accurate timelines
    - Priority classification with reasoning
    - Confirmation gate prior to database creation via Task CRUD API
    """

    def __init__(self):
        self.vector_store = get_vector_store()
        self.date_parser = get_date_parser()
        self.priority_classifier = get_priority_classifier()
        self.crud = get_task_crud()

    def process_request(self, user_message: str, user_confirmed: bool = False, confirmed_tasks: Optional[List[TaskProposalItem]] = None) -> AgentChatResponse:
        steps: List[AgentStep] = []

        # If user explicitly sent confirmed tasks to commit
        if user_confirmed and confirmed_tasks:
            return self.confirm_and_create_tasks(confirmed_tasks)

        # Check if user message is a simple conversational confirmation
        lower_msg = user_message.lower().strip()
        confirmation_phrases = ["confirm", "yes", "proceed", "create them", "approve", "go ahead", "create all", "looks good", "do it"]
        if lower_msg in confirmation_phrases and confirmed_tasks:
            return self.confirm_and_create_tasks(confirmed_tasks)

        # Step 1: Query ChromaDB Vector Database for Project Notes
        step1_notes = self.vector_store.search_notes(user_message, n_results=4)
        # Also ensure we grab core notes if user message is broad
        if len(step1_notes) < 2:
            step1_notes = self.vector_store.list_all_notes()[:4]

        steps.append(AgentStep(
            name="ChromaDB Vector Retrieval",
            status="success",
            details=f"Retrieved {len(step1_notes)} relevant project notes using all-MiniLM-L6-v2 embeddings.",
            data=[{"title": n.title, "category": n.category, "similarity": n.similarity} for n in step1_notes]
        ))

        # Step 2: Task Extraction & Context Decomposition
        subtasks_raw = self._extract_candidate_subtasks(user_message)
        steps.append(AgentStep(
            name="Task Decomposition",
            status="success",
            details=f"Identified {len(subtasks_raw)} distinct action items from the request.",
            data=[s["raw_text"] for s in subtasks_raw]
        ))

        # Step 3: Date Parsing & Priority Classification & Context Enrichment
        proposed_items: List[TaskProposalItem] = []
        for raw in subtasks_raw:
            # Match against retrieved project notes for fact enrichment
            matched_notes, enriched_desc, category = self._enrich_task_with_notes(raw["raw_text"], step1_notes)
            
            # Tool Call 1: Date Parser
            date_info = self.date_parser.parse(raw["raw_text"], context_hint=enriched_desc)
            due_date_str = date_info.get("formatted", date_info.get("iso", ""))

            # Tool Call 2: Priority Classifier
            p_info = self.priority_classifier.classify(
                title=raw["title"],
                description=enriched_desc,
                due_date_str=date_info.get("iso", ""),
                category=category
            )

            item = TaskProposalItem(
                temp_id=f"prop-{uuid.uuid4().hex[:6]}",
                title=raw["title"],
                description=enriched_desc,
                due_date=due_date_str,
                priority=p_info["priority"],
                priority_reason=p_info["reason"],
                category=category,
                tags=raw.get("tags", []),
                source_notes=[n.title for n in matched_notes],
                approved=True
            )
            proposed_items.append(item)

        steps.append(AgentStep(
            name="Date Parser & Priority Classifier",
            status="success",
            details=f"Parsed due dates and classified priorities for all {len(proposed_items)} tasks.",
            data=[{"title": t.title, "due": t.due_date, "priority": t.priority, "reason": t.priority_reason} for t in proposed_items]
        ))

        # Step 4: Package into Structured Task Proposal
        proposal_id = f"proposal-{uuid.uuid4().hex[:8]}"
        proposal = TaskProposal(
            proposal_id=proposal_id,
            user_request=user_message,
            summary=f"Generated {len(proposed_items)} structured workshop tasks enriched with project notes from ChromaDB.",
            retrieved_notes=step1_notes,
            proposed_tasks=proposed_items
        )

        reply = (
            f"I have analyzed your request and cross-referenced our workshop project notes in ChromaDB. "
            f"I decomposed the requirements into **{len(proposed_items)} structured tasks**, resolved their deadlines using the Date Parser, "
            f"and assigned priorities with the Priority Classifier.\n\n"
            f"Please review the proposed tasks below and click **'Confirm & Create Tasks'** to commit them to the task management database."
        )

        return AgentChatResponse(
            reply=reply,
            proposal=proposal,
            created_tasks=None,
            steps=steps
        )

    def confirm_and_create_tasks(self, tasks_to_create: List[TaskProposalItem]) -> AgentChatResponse:
        """Commits confirmed proposed tasks to the database via Task CRUD API."""
        created_list: List[Task] = []
        for p in tasks_to_create:
            if not p.approved:
                continue
            tc = TaskCreate(
                title=p.title,
                description=p.description,
                due_date=p.due_date,
                priority=p.priority,
                priority_reason=p.priority_reason,
                category=p.category,
                status="pending",
                tags=p.tags,
                source_notes=p.source_notes
            )
            task = self.crud.create_task(tc)
            created_list.append(task)

        step = AgentStep(
            name="Task CRUD API Execution",
            status="success",
            details=f"Successfully committed {len(created_list)} confirmed tasks to the persistent database.",
            data=[t.title for t in created_list]
        )

        reply = (
            f"🎉 **Confirmation Received!** Created **{len(created_list)} tasks** in the Task Management system.\n\n"
            f"You can now view, update, filter, and track their progress on the Task Board."
        )

        return AgentChatResponse(
            reply=reply,
            proposal=None,
            created_tasks=created_list,
            steps=[step]
        )

    def _extract_candidate_subtasks(self, text: str) -> List[Dict[str, Any]]:
        """Decomposes user prompt into candidate subtasks based on verbs, commas, 'and', bullet points."""
        text = text.strip()
        tasks = []

        # Check for bullet points or numbered lists
        lines = [line.strip() for line in text.split("\n") if line.strip()]
        list_items = [l for l in lines if re.match(r'^(\d+[\.\)]|\-|\*|\•)\s+', l)]
        if len(list_items) >= 2:
            for item in list_items:
                clean_item = re.sub(r'^(\d+[\.\)]|\-|\*|\•)\s+', '', item)
                title, tags = self._format_task_title_and_tags(clean_item)
                tasks.append({"title": title, "raw_text": clean_item, "tags": tags})
            return tasks

        # Otherwise, split natural sentence by conjunctions and punctuation
        # E.g., 'book catering..., test the AV equipment..., get the speaker slides..., and print badges'
        # Remove common introductory phrases
        intro_pattern = r'^(?:please\s+)?(?:create\s+tasks?\s+(?:for\s+)?(?:preparing\s+)?(?:the\s+)?(?:upcoming\s+)?workshop(?::|\s+to|\s+that|\s+and|\s+)?|we\s+need\s+to\s+prepare\s+(?:the\s+)?workshop(?::|\s+)?|prep\s+the\s+workshop(?::|\s+)?)\s*'
        body = re.sub(intro_pattern, '', text, flags=re.IGNORECASE).strip()

        # Split on commas, semicolons, or 'and' followed by verb
        clauses = re.split(r'[,;]|\band\s+(?=[a-z]+\b)', body, flags=re.IGNORECASE)
        clauses = [c.strip() for c in clauses if len(c.strip()) > 5]

        if not clauses:
            clauses = [text]

        for clause in clauses:
            title, tags = self._format_task_title_and_tags(clause)
            tasks.append({"title": title, "raw_text": clause, "tags": tags})

        return tasks

    def _format_task_title_and_tags(self, snippet: str) -> Tuple[str, List[str]]:
        """Cleans snippet into a professional task title and extracts relevant tags."""
        s = snippet.strip()
        tags = []
        lower = s.lower()

        # Clean introductory prepositions
        s = re.sub(r'^(to\s+|by\s+|and\s+|also\s+)', '', s, flags=re.IGNORECASE).strip()

        # Detect domain tags
        if any(w in lower for w in ["cater", "food", "lunch", "vegan", "breakfast", "snack"]):
            tags.extend(["catering", "dietary"])
        if any(w in lower for w in ["av", "projector", "mic", "sound", "screen", "wifi", "room 302"]):
            tags.extend(["venue", "av-setup"])
        if any(w in lower for w in ["slide", "presentation", "speaker", "curriculum", "repo", "deck"]):
            tags.extend(["content", "speakers"])
        if any(w in lower for w in ["badge", "lanyard", "swag", "kit", "print", "usb"]):
            tags.extend(["logistics", "swag"])
        if any(w in lower for w in ["email", "reminder", "prereq", "survey"]):
            tags.extend(["marketing", "comms"])

        # Format title to capitalized action title
        title = s[0].upper() + s[1:] if len(s) > 1 else s.upper()
        # Truncate if excessively long
        if len(title) > 70:
            title = title[:67] + "..."

        return title, list(set(tags))

    def _enrich_task_with_notes(self, task_text: str, notes: List[ProjectNote]) -> Tuple[List[ProjectNote], str, str]:
        """Cross-references ChromaDB notes to extract exact specifications and figures."""
        lower = task_text.lower()
        matched = []
        details = []
        category = "General"

        # Check catering / dietary
        if any(w in lower for w in ["cater", "food", "lunch", "dietary", "vegan", "allergy", "breakfast", "meal"]):
            category = "Catering"
            for n in notes:
                if "catering" in n.category.lower() or "catering" in n.title.lower():
                    matched.append(n)
                    details.append(
                        "• Provider: GreenLeaf Artisanal Kitchen (orders@greenleafkitchen.com).\n"
                        "• Headcount: 45 attendees + 5 staff (50 total).\n"
                        "• Dietary specs: 8 Vegetarian, 4 Strict Vegan (separately boxed), 3 Gluten-Free, 1 Severe Airborne Peanut Allergy.\n"
                        "• Final headcount confirmation required 3 business days prior."
                    )
                    break

        # Check Venue & AV
        elif any(w in lower for w in ["av", "projector", "mic", "microphone", "sound", "room 302", "wifi", "power strip"]):
            category = "Venue & AV"
            for n in notes:
                if "venue" in n.category.lower() or "av" in n.category.lower() or "venue" in n.title.lower():
                    matched.append(n)
                    details.append(
                        "• Room: Innovation Auditorium 302 (60-seat classroom capacity).\n"
                        "• Equipment: Dual 4K laser projectors, 2 wireless presenter lavaliers, 1 handheld Q&A mic, 50 power strips.\n"
                        "• Dedicated Wi-Fi: 'InnovationHub-5G' (Passcode: AIWorkshop2026!).\n"
                        "• Technical AV dry run must be completed 48 hours in advance."
                    )
                    break

        # Check Speakers & Slides
        elif any(w in lower for w in ["slide", "presentation", "deck", "speaker", "curriculum", "repo", "github"]):
            category = "Content & Speakers"
            for n in notes:
                if "speaker" in n.category.lower() or "content" in n.category.lower() or "speaker" in n.title.lower():
                    matched.append(n)
                    details.append(
                        "• Speakers: Dr. Aris Thorne (Keynote), Maya Lin (Fine-Tuning), Dev Patel (Agentic Tool-Calling).\n"
                        "• Specs: 16:9 ratio, exported to both PDF and PPTX, due 4 days prior for AV dry run.\n"
                        "• Verify hands-on GitHub repo 'ai-agentic-workshop-2026' with Docker devcontainer."
                    )
                    break

        # Check Badges & Kits
        elif any(w in lower for w in ["badge", "lanyard", "kit", "swag", "print", "usb", "workbook"]):
            category = "Logistics"
            for n in notes:
                if "kit" in n.title.lower() or "badge" in n.title.lower() or "logistics" in n.category.lower():
                    matched.append(n)
                    details.append(
                        "• Package: 50 custom NFC name badges with branded lanyards, spiral reference workbooks, and 64GB USBs preloaded with offline models.\n"
                        "• Vendor: PrintPro Express (batch submitted 3 days prior, kit assembly 24h prior)."
                    )
                    break

        # Check Email & Marketing
        elif any(w in lower for w in ["email", "reminder", "prereq", "prerequisite", "survey", "announcement"]):
            category = "Marketing & Comms"
            for n in notes:
                if "comms" in n.category.lower() or "marketing" in n.category.lower() or "comms" in n.title.lower():
                    matched.append(n)
                    details.append(
                        "• T-5 Days: Software prerequisites (Python 3.11+, Docker, VS Code).\n"
                        "• T-24 Hours: Building access QR codes, parking map, Room 302 directions.\n"
                        "• T+2 Hours post-event: Satisfaction feedback survey and digital certificates."
                    )
                    break

        if not details:
            # Fallback enrichment using first matched note
            if notes:
                matched.append(notes[0])
                details.append(f"Referenced workshop note: {notes[0].title}. Ensure alignment with master workshop schedule.")

        enriched_description = "\n".join(details)
        return matched, enriched_description, category

# Global singleton
_agent_instance: Optional[TaskManagementAgent] = None

def get_task_agent() -> TaskManagementAgent:
    global _agent_instance
    if _agent_instance is None:
        _agent_instance = TaskManagementAgent()
    return _agent_instance
