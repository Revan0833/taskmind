import re
from datetime import datetime
from typing import Dict, Any, Optional

class PriorityClassifierTool:
    """Intelligent Priority Classifier for workshop tasks."""

    URGENT_KEYWORDS = [
        "urgent", "asap", "immediately", "blocker", "critical", "emergency",
        "right now", "crucial", "severe", "allergy", "airborne"
    ]

    HIGH_KEYWORDS = [
        "important", "high priority", "essential", "must", "vital", "required",
        "contract", "deadline", "caterer sign-off", "av test", "4k projector",
        "keynote", "dry run", "prerequisite"
    ]

    LOW_KEYWORDS = [
        "optional", "nice to have", "bonus", "if time permits", "low priority",
        "whenever", "secondary", "survey", "followup", "post-event"
    ]

    def classify(self, title: str, description: str = "", due_date_str: str = "", category: str = "") -> Dict[str, Any]:
        """
        Classifies task priority into Urgent, High, Medium, or Low.
        Considers keyword signals, deadline urgency, and operational impact.
        """
        combined = f"{title} {description} {category}".lower()
        score = 50  # baseline Medium
        reasons = []

        # 1. Keyword analysis
        urgent_matches = [w for w in self.URGENT_KEYWORDS if re.search(r'\b' + re.escape(w) + r'\b', combined)]
        if urgent_matches:
            score += 35
            reasons.append(f"Contains urgent keywords ({', '.join(urgent_matches)})")

        high_matches = [w for w in self.HIGH_KEYWORDS if re.search(r'\b' + re.escape(w) + r'\b', combined)]
        if high_matches:
            score += 20
            reasons.append(f"Contains high-priority indicators ({', '.join(high_matches)})")

        low_matches = [w for w in self.LOW_KEYWORDS if re.search(r'\b' + re.escape(w) + r'\b', combined)]
        if low_matches:
            score -= 30
            reasons.append(f"Contains low-priority indicators ({', '.join(low_matches)})")

        # 2. Domain & Category impact
        if any(w in combined for w in ["allergy", "peanut", "nut-free", "dietary"]):
            score += 25
            reasons.append("Safety critical: attendee dietary/allergy compliance")

        if any(w in combined for w in ["projector", "av equipment", "microphone", "sound system", "dry run"]):
            score += 15
            reasons.append("Technical infrastructure dependency for presentation")

        if any(w in combined for w in ["survey", "feedback", "certificate", "post-event"]):
            score -= 20
            reasons.append("Post-event deliverable (non-blocking for workshop day)")

        # 3. Deadline proximity analysis
        if due_date_str:
            try:
                # Try parsing ISO or YYYY-MM-DD
                date_part = due_date_str.split(" ")[0].split("T")[0]
                dt = datetime.strptime(date_part, "%Y-%m-%d")
                days_left = (dt.date() - datetime.now().date()).days

                if days_left <= 1:
                    score += 25
                    reasons.append(f"Imminent deadline ({days_left} day(s) left)")
                elif days_left <= 3:
                    score += 10
                    reasons.append(f"Tight deadline ({days_left} days left)")
            except Exception:
                pass

        # 4. Map score to Priority Level
        score = max(5, min(95, score))
        if score >= 75:
            priority = "Urgent"
        elif score >= 60:
            priority = "High"
        elif score >= 35:
            priority = "Medium"
        else:
            priority = "Low"

        primary_reason = "; ".join(reasons) if reasons else "Standard operational workshop task"

        return {
            "priority": priority,
            "score": score,
            "reason": primary_reason
        }

# Global singleton
_classifier_instance: Optional[PriorityClassifierTool] = None

def get_priority_classifier() -> PriorityClassifierTool:
    global _classifier_instance
    if _classifier_instance is None:
        _classifier_instance = PriorityClassifierTool()
    return _classifier_instance
