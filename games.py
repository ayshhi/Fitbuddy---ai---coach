"""
games.py - Wellness Bingo, a weekly game designed to feel good without being addictive.

Everyone gets the SAME 5x5 card each week, so friends can play together.
   Squares are small real-life self-care tasks. Some tick themselves from your data (water, sleep, movement).
   Finish a row, column or diagonal for a bingo. A new card arrives every Monday.

(The crosswords live in crossword.py.)
"""

import random
from datetime import date, timedelta
from urllib.parse import quote

import journey
import storage

# ---------------------------------------------------------------- Wellness Bingo

# (id, emoji, text, auto-check key or None)
BINGO_TASKS = [
    ("water8", "💧", "8 glasses of water in a day", "water8"),
    ("walk15", "🚶‍♀️", "A 15-min walk", "move15"),
    ("sleep7", "😴", "7+ hours of sleep", "sleep7"),
    ("checkin3", "🗓️", "Check in 3 days this week", "checkin3"),
    ("scan", "📸", "Scan a meal", "scan"),
    ("plan3", "📋", "Finish all 3 steps of a Tulsi plan", "plan3"),
    ("sun", "☀️", "10 minutes of morning sunlight", None),
    ("call", "📞", "Call someone you love", None),
    ("stretch", "🧘‍♀️", "Stretch for 5 min before bed", None),
    ("protein", "🥚", "A protein breakfast (eggs, paneer, dal, sprouts)", None),
    ("veg", "🥦", "Half your plate veggies at one meal", None),
    ("nophone", "📵", "No phone for the first 30 min of the day", None),
    ("dance", "💃", "Dance to 2 songs", None),
    ("journal", "📝", "Write 3 things you're grateful for", None),
    ("tea", "🍵", "Swap one sugary drink for herbal tea", None),
    ("nature", "🌳", "10 minutes outside in nature", None),
    ("breathe", "🌬️", "5 slow deep breaths when stressed", None),
    ("early", "🌙", "In bed 30 min earlier than usual", None),
    ("laugh", "😂", "Watch something that makes you laugh", None),
    ("compliment", "💌", "Give someone a compliment", None),
    ("seeds", "🌻", "Add seeds or nuts to a meal", None),
    ("stairs", "🪜", "Take the stairs once", None),
    ("cook", "🍳", "Cook a simple home meal", None),
    ("music", "🎧", "Listen to calming music for 10 min", None),
    ("posture", "🧍‍♀️", "Stand up and stretch every hour at work", None),
    ("fruit", "🍎", "Eat a whole fruit instead of a sweet", None),
    ("selfcare", "🛁", "10 minutes of pure 'me time'", None),
    ("mindful", "🍽️", "Eat one meal slowly, no screens", None),
    ("tidy", "🧺", "Tidy one small space", None),
    ("win", "💜", "Log a non-scale win in My garden", "win"),
]
FREE = ("free", "💜", "Be kind to yourself (free!)", None)


def week_start(day: date | None = None) -> date:
    day = day or date.today()
    return day - timedelta(days=day.weekday())  # Monday


def week_key(day: date | None = None) -> str:
    y, w, _ = (day or date.today()).isocalendar()
    return f"{y}-W{w:02d}"


def bingo_card(day: date | None = None) -> list[tuple]:
    """24 tasks + a free centre square. Shuffled with the week as the seed, so everyone gets the same card."""
    tasks = BINGO_TASKS[:]
    random.Random(week_key(day)).shuffle(tasks)
    card = tasks[:24]
    card.insert(12, FREE)
    return card


def auto_done(day: date | None = None) -> set[str]:
    """Squares your own data already proves this week."""
    start = week_start(day).isoformat()
    end = (week_start(day) + timedelta(days=6)).isoformat()
    rows = {d: r for d, r in journey.all_days().items() if start <= d <= end}
    done = set()
    if any(int(r.get("water", 0) or 0) >= 8 for r in rows.values()):
        done.add("water8")
    checkins = storage.load_checkins()
    if any(max(float(r.get("workout_min", 0) or 0), float(checkins.get(d, {}).get("exercise_minutes") or 0)) >= 15
           for d, r in rows.items()):
        done.add("move15")
    if any(float(r.get("sleep_hours", 0) or 0) >= 7 for r in rows.values()):
        done.add("sleep7")
    if sum(1 for r in rows.values() if r.get("checked_in")) >= 3:
        done.add("checkin3")
    meals = storage._read(storage.MEALS_FILE, {})
    if any(start <= d <= end and any(m.get("source") != "quick log" for m in v) for d, v in meals.items()):
        done.add("scan")
    if any(start <= d <= end and p["items"] and all(i.get("done") for i in p["items"]) for d, p in storage.load_plans().items()):
        done.add("plan3")
    if any(start <= w["date"] <= end for w in storage.load_wins()):
        done.add("win")
    return done


def ticked(day: date | None = None) -> set[int]:
    """Square positions (0-24) that are done: ticked by you, proven by your data, or the free centre."""
    card = bingo_card(day)
    manual = set(storage.load_bingo().get(week_key(day), []))
    auto = auto_done(day)
    return {i for i, t in enumerate(card) if i in manual or t[0] == "free" or (t[3] and t[3] in auto)}


LINES = [[r * 5 + c for c in range(5)] for r in range(5)] + [[r * 5 + c for r in range(5)] for c in range(5)] \
        + [[0, 6, 12, 18, 24], [4, 8, 12, 16, 20]]


def bingo_lines(done: set[int]) -> int:
    return sum(1 for line in LINES if all(i in done for i in line))


def bingo_share(name: str, done: set[int]) -> str:
    rows = ["".join("🟪" if r * 5 + c in done else "⬜" for c in range(5)) for r in range(5)]
    lines = bingo_lines(done)
    head = f"🎯 FitBuddy Wellness Bingo {week_key()}: {len(done)}/25 squares, {lines} bingo{'s' if lines != 1 else ''}!"
    return head + "\n" + "\n".join(rows) + f"\nPlaying with Tulsi 🌿 Want to join {name or 'me'} this week?"


def whatsapp(text: str) -> str:
    return "https://wa.me/?text=" + quote(text)
