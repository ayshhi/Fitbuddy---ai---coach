"""
reminders.py - makes a calendar file (.ics) with daily reminders.

Your phone's calendar app then reminds you every day, even when FitBuddy is closed.
No server and no notification permissions needed: it's a standard calendar format.
"""

import uuid
from datetime import date, datetime, time, timedelta, timezone

DEFAULTS = [
    # (key, title, time, description)
    ("morning", "🌿 Peek at today's plan from Tulsi", "08:00", "Open FitBuddy and look at your 3-step plan for today."),
    ("water1", "💧 Water Tulsi (and you!)", "10:30", "Drink a glass of water and tap 'I drank a glass' in FitBuddy."),
    ("water2", "💧 Water Tulsi (and you!)", "13:30", "Drink a glass of water and tap 'I drank a glass' in FitBuddy."),
    ("water3", "💧 Water Tulsi (and you!)", "16:30", "Drink a glass of water and tap 'I drank a glass' in FitBuddy."),
    ("checkin", "💜 Evening check-in with Tulsi", "21:00", "Tell Tulsi about your day in a sentence or two. She'll plan a kind tomorrow."),
    ("winddown", "😴 Wind-down time", "22:30", "Phone away, lights low. Good sleep keeps cortisol (and cravings) down."),
]


def _escape(text: str) -> str:
    return text.replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,").replace("\n", "\\n")


def build_ics(chosen: list[tuple[str, str, str]], start: date | None = None) -> bytes:
    """chosen: [(title, "HH:MM", description), ...]. Each becomes a daily repeating event with an alert.
    Times are 'floating' (no time zone), so they ring at that time wherever your phone is."""
    start = start or date.today()
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    lines = ["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//FitBuddy//Tulsi reminders//EN", "CALSCALE:GREGORIAN",
             "X-WR-CALNAME:FitBuddy with Tulsi"]
    for title, hhmm, description in chosen:
        h, m = (int(x) for x in hhmm.split(":"))
        begin_dt = datetime.combine(start, time(h, m))
        begin = begin_dt.strftime("%Y%m%dT%H%M%S")
        end = (begin_dt + timedelta(minutes=10)).strftime("%Y%m%dT%H%M%S")
        lines += ["BEGIN:VEVENT", f"UID:{uuid.uuid4()}@fitbuddy", f"DTSTAMP:{stamp}", f"DTSTART:{begin}", f"DTEND:{end}",
                  "RRULE:FREQ=DAILY", f"SUMMARY:{_escape(title)}", f"DESCRIPTION:{_escape(description)}",
                  "BEGIN:VALARM", "ACTION:DISPLAY", f"DESCRIPTION:{_escape(title)}", "TRIGGER:PT0M", "END:VALARM",
                  "END:VEVENT"]
    lines.append("END:VCALENDAR")
    return ("\r\n".join(lines) + "\r\n").encode("utf-8")
