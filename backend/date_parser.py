import re
from datetime import datetime, timedelta
from typing import Optional, Tuple, Dict, Any
import dateparser

from backend.config import TARGET_WORKSHOP_DATE

class DateParserTool:
    """Intelligent Date & Deadline Parser for natural language task requests."""

    def __init__(self, target_workshop_date: Optional[datetime] = None):
        self.workshop_date = target_workshop_date or TARGET_WORKSHOP_DATE

    def parse(self, text: str, context_hint: str = "") -> Dict[str, Any]:
        """
        Extracts and resolves a deadline from natural language text.
        Supports:
        - Relative offsets from workshop: '3 days before event', '48h prior', 'T-5 days'
        - Calendar relative: 'next Monday', 'by Friday 5pm', 'tomorrow', 'in 3 days'
        - Explicit dates: 'October 28', '2026-11-04'
        - Contextual inference based on task topic
        """
        cleaned = text.strip()
        now = datetime.now()

        # 1. Check for workshop-relative patterns
        workshop_rel = self._match_workshop_relative(cleaned)
        if workshop_rel:
            return workshop_rel

        # 2. Check for explicit phrases like 'in X days', 'in X hours', 'by next X'
        extracted_phrase = self._extract_date_phrase(cleaned)
        target_str = extracted_phrase if extracted_phrase else cleaned

        # 3. Use dateparser with future preference
        parsed_dt = dateparser.parse(
            target_str,
            settings={
                "PREFER_DATES_FROM": "future",
                "RELATIVE_BASE": now,
                "RETURN_AS_TIMEZONE_AWARE": False
            }
        )

        if parsed_dt:
            # Ensure it's not set in the past unless explicitly intended
            if parsed_dt < now - timedelta(hours=1):
                # If dateparser picked past weekday, jump to next week
                parsed_dt += timedelta(days=7)

            return self._format_result(parsed_dt, source="natural_language_parser", phrase=target_str)

        # 4. Contextual fallback based on task category/keywords
        fallback_dt, reason = self._infer_contextual_deadline(cleaned, context_hint)
        return self._format_result(fallback_dt, source="contextual_inference", reason=reason)

    def _match_workshop_relative(self, text: str) -> Optional[Dict[str, Any]]:
        """Matches phrases like '3 days before workshop', '48 hours prior', 'T-2 days'."""
        text_lower = text.lower()

        # Pattern: T-X days / T-X hours
        t_minus = re.search(r't-(\d+)\s*(days?|d|hours?|h)', text_lower)
        if t_minus:
            num = int(t_minus.group(1))
            unit = t_minus.group(2)
            delta = timedelta(days=num) if "d" in unit else timedelta(hours=num)
            resolved = self.workshop_date - delta
            return self._format_result(
                resolved,
                source="workshop_milestone_offset",
                phrase=f"T-{num} {unit} relative to workshop"
            )

        # Pattern: X days before / prior to workshop / event
        days_before = re.search(r'(\d+)\s*days?\s*(?:before|prior to|ahead of)\s*(?:the\s*)?(?:workshop|event|conference|day)', text_lower)
        if days_before:
            days = int(days_before.group(1))
            resolved = self.workshop_date - timedelta(days=days)
            return self._format_result(
                resolved,
                source="workshop_milestone_offset",
                phrase=f"{days} days before workshop"
            )

        # Pattern: X hours before / prior
        hours_before = re.search(r'(\d+)\s*(?:hours?|hrs?|h)\s*(?:before|prior to|ahead of)', text_lower)
        if hours_before:
            hours = int(hours_before.group(1))
            resolved = self.workshop_date - timedelta(hours=hours)
            return self._format_result(
                resolved,
                source="workshop_milestone_offset",
                phrase=f"{hours} hours before workshop"
            )

        return None

    def _extract_date_phrase(self, text: str) -> Optional[str]:
        """Extracts candidate date snippet from sentences like 'book catering by next Wednesday'."""
        patterns = [
            r'(?:by|due|on|before|until|for)\s+([a-zA-Z0-9\s,\:\-\/]+?)(?:\.|$|,|\band\b)',
            r'(in\s+\d+\s+(?:days?|weeks?|hours?|business days?))',
            r'(tomorrow(?:\s+at\s+\d+(?::\d+)?\s*(?:am|pm)?)?)',
            r'(next\s+(?:monday|tuesday|wednesday|thursday|friday|saturday|sunday|week))',
            r'(\b\d{1,2}\s+(?:days?|weeks?)\s+from\s+now\b)'
        ]
        for pat in patterns:
            match = re.search(pat, text, re.IGNORECASE)
            if match:
                candidate = match.group(1).strip()
                # filter out non-date noise words
                if len(candidate) > 2 and not candidate.lower() in ["our", "the", "all", "each", "some"]:
                    return candidate
        return None

    def _infer_contextual_deadline(self, text: str, context_hint: str) -> Tuple[datetime, str]:
        """Infers reasonable default timeline based on workshop lead times."""
        combined = (text + " " + context_hint).lower()

        if any(w in combined for w in ["catering", "food", "lunch", "dietary", "caterer"]):
            # Catering contracts typically need confirmation 3 days before
            dt = self.workshop_date - timedelta(days=3)
            return dt.replace(hour=17, minute=0), "3 business days prior (caterer headcount deadline)"

        if any(w in combined for w in ["av", "projector", "mic", "microphone", "sound", "screen", "wifi"]):
            # AV tests need 48 hours before
            dt = self.workshop_date - timedelta(days=2)
            return dt.replace(hour=16, minute=0), "48 hours prior (technical dry run)"

        if any(w in combined for w in ["badge", "lanyard", "kit", "swag", "print"]):
            # Printing badges takes 3 days
            dt = self.workshop_date - timedelta(days=3)
            return dt.replace(hour=18, minute=0), "3 days prior (print batch delivery)"

        if any(w in combined for w in ["slide", "presentation", "deck", "speaker", "repo"]):
            # Slides collection 4 days before
            dt = self.workshop_date - timedelta(days=4)
            return dt.replace(hour=18, minute=0), "4 days prior (speaker review buffer)"

        if any(w in combined for w in ["email", "reminder", "prerequisite", "attendee"]):
            # Prereq email 5 days before
            dt = self.workshop_date - timedelta(days=5)
            return dt.replace(hour=10, minute=0), "5 days prior (attendee prep window)"

        # Generic default: 2 days from now or 2 days before event
        now = datetime.now()
        dt = min(now + timedelta(days=2), self.workshop_date - timedelta(days=1))
        return dt.replace(hour=17, minute=0), "Standard lead time"

    def _format_result(self, dt: datetime, source: str, phrase: str = "", reason: str = "") -> Dict[str, Any]:
        """Formats the datetime into clean structured representation."""
        now = datetime.now()
        diff_days = (dt.date() - now.date()).days
        
        if diff_days == 0:
            rel = "Today"
        elif diff_days == 1:
            rel = "Tomorrow"
        elif diff_days == -1:
            rel = "Yesterday"
        elif diff_days > 1:
            rel = f"In {diff_days} days"
        else:
            rel = f"{abs(diff_days)} days ago"

        days_to_workshop = (self.workshop_date.date() - dt.date()).days
        if days_to_workshop > 0:
            rel += f" (T-{days_to_workshop} days to workshop)"
        elif days_to_workshop == 0:
            rel += " (Workshop Day)"

        time_str = dt.strftime("%I:%M %p") if (dt.hour != 0 or dt.minute != 0) else ""
        date_str = dt.strftime("%b %d, %Y")
        formatted = f"{date_str} at {time_str}" if time_str else date_str

        return {
            "iso": dt.strftime("%Y-%m-%d %H:%M"),
            "date": dt.strftime("%Y-%m-%d"),
            "formatted": formatted,
            "relative": rel,
            "source": source,
            "matched_phrase": phrase,
            "reason": reason
        }

# Global singleton
_date_parser_instance: Optional[DateParserTool] = None

def get_date_parser() -> DateParserTool:
    global _date_parser_instance
    if _date_parser_instance is None:
        _date_parser_instance = DateParserTool()
    return _date_parser_instance
