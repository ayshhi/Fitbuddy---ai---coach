"""
games.py - two small games designed to feel good without being addictive.

1. Wellness Bingo (weekly): everyone gets the SAME 5x5 card each week, so friends can play together.
   Squares are small real-life self-care tasks. Some tick themselves from your data (water, sleep, movement).
   Finish a row, column or diagonal for a bingo. A new card arrives every Monday.

2. Daily Crossword (one a day): a small newspaper-style crossword with easy clues about health and Kerala food.
   Everyone gets the same puzzle that day, so you can compare on WhatsApp. One puzzle a day, then it's done.
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


# ---------------------------------------------------------------- Daily Crossword

# Easy, friendly clues about health, Kerala food and feeling good.
CLUES = {
    "WATER": "Drink 8 glasses of this a day", "SLEEP": "Aim for 7 to 9 hours of this every night",
    "WALK": "A gentle 15-minute one after meals helps", "YOGA": "Practice with poses like Tree and Child's pose",
    "DANCE": "Move to music: fun cardio!", "TULSI": "Holy basil, and our coach's name",
    "MANGO": "Kerala's favourite summer fruit", "GUAVA": "Green fruit packed with vitamin C",
    "LEMON": "Squeeze this into water for some zing", "APPLE": "One a day keeps the doctor away, they say",
    "BANANA": "Yellow fruit full of potassium", "DATES": "Sweet dried fruit to beat a sugar craving",
    "CURD": "Dahi, great with rice", "RAGI": "Finger millet, used in dosa and porridge",
    "OATS": "Breakfast grain cooked into porridge", "PUTTU": "Steamed rice cylinder, a Kerala breakfast",
    "APPAM": "Lacy Kerala pancake with a soft centre", "IDLI": "Soft steamed rice cake",
    "DOSA": "Thin, crispy South Indian crepe", "SAMBAR": "Lentil and vegetable stew",
    "RASAM": "Tangy, peppery South Indian soup", "AVIAL": "Kerala mixed vegetables with coconut and curd",
    "THORAN": "Kerala stir-fried veg with grated coconut", "SEEDS": "Flax, chia and pumpkin ___",
    "NUTS": "Almonds and walnuts, for example", "EGGS": "Protein-packed breakfast, boiled or scrambled",
    "PANEER": "Indian cottage cheese", "FISH": "Kerala curry star, rich in omega-3",
    "SPINACH": "Palak, a leafy green", "GINGER": "Root that goes in chai and soothes the tummy",
    "CUMIN": "Jeera", "SMILE": "Curved line on a happy face", "RELAX": "Unwind and let go",
    "BREATHE": "Slowly in... and out", "CALM": "Peaceful, not stressed", "HAPPY": "Joyful",
    "STRETCH": "Reach your arms up high and ___", "STEPS": "A pedometer counts these",
    "HEART": "It pumps blood around your body", "BRAIN": "Your thinking organ",
    "CYCLE": "Menstrual ___, which you can track in FitBuddy", "FIBRE": "Found in veggies, it helps digestion",
    "PROTEIN": "Builds muscle: found in eggs, dal and paneer", "SALAD": "A bowl of fresh raw veggies",
    "SOUP": "A warm bowl, like rasam", "TEA": "Chai or herbal ___", "REST": "Take a break and ___",
    "NAP": "A short daytime sleep", "JOG": "Run slowly", "SWIM": "Exercise in a pool",
    "HIKE": "A long walk up a hill", "PLANK": "Hold your body straight like a board",
    "SQUAT": "Bend your knees as if sitting on a chair", "MOOD": "How you feel",
    "JOURNAL": "A notebook for your thoughts", "HONEY": "Sweet golden syrup made by bees",
    "COCONUT": "Kerala's favourite tree fruit", "PAPAYA": "Orange fruit that's good for digestion",
    "PEACE": "Calm and quiet", "FRIEND": "Someone you call when you need a laugh",
    "MUSIC": "Songs and melodies", "NATURE": "Trees, flowers and fresh air", "GARDEN": "Where Tulsi grows",
    "BLOOM": "To flower", "LOTUS": "Yoga pose named after a flower", "SUNNY": "A bright, warm day",
    "HYDRATE": "Drink water to ___", "SPROUTS": "Germinated moong, great in chaat",
    "WELLNESS": "Feeling good in body and mind", "SUNLIGHT": "Morning ___ helps you sleep better at night",
}
SPINES = ["WATER", "SLEEP", "DANCE", "TULSI", "SMILE", "RELAX", "HAPPY", "BLOOM", "LOTUS", "PEACE", "HEART",
          "STEPS", "SALAD", "MANGO", "LEMON", "APPLE", "CYCLE", "BRAIN", "HONEY", "MUSIC", "PLANK", "SQUAT",
          "SPROUTS", "BREATHE", "PROTEIN", "STRETCH", "COCONUT", "JOURNAL", "SPINACH", "HYDRATE"]
LAUNCH = date(2026, 11, 1)  # puzzle #1


def puzzle_number(day: date | None = None) -> int:
    return ((day or date.today()) - LAUNCH).days + 1


def make_crossword(day: date | None = None) -> dict:
    """Builds today's crossword. One word goes DOWN, and words go ACROSS through its 1st, 3rd, 5th (and 7th) letters.
    Across words sit on every other row, so they never touch each other by accident.
    The date is the random seed, so everyone gets the same puzzle that day."""
    rng = random.Random(f"crossword-{(day or date.today()).isoformat()}")
    for _ in range(50):  # try spines until one gives at least 3 across words
        spine = rng.choice(SPINES)
        used, across = {spine}, []
        for row in range(0, len(spine), 2):
            letter = spine[row]
            options = [(w, i) for w in CLUES if w not in used for i, ch in enumerate(w) if ch == letter and 3 <= len(w) <= 8]
            if options:
                word, k = rng.choice(sorted(options))
                used.add(word)
                across.append({"word": word, "row": row, "offset": k})
        if len(across) >= 3:
            break
    spine_col = max(a["offset"] for a in across)
    for a in across:
        a["col"] = spine_col - a["offset"]
    width = max(max(a["col"] + len(a["word"]) for a in across), spine_col + 1)

    # number the start of each answer, in reading order (like a newspaper)
    starts = {(a["row"], a["col"]) for a in across} | {(0, spine_col)}
    numbers = {cell: n + 1 for n, cell in enumerate(sorted(starts))}
    entries = [{"id": f"A{a['row']}", "dir": "Across", "num": numbers[(a["row"], a["col"])], "word": a["word"],
                "row": a["row"], "col": a["col"], "clue": CLUES[a["word"]]} for a in across]
    entries.append({"id": "D", "dir": "Down", "num": numbers[(0, spine_col)], "word": spine, "row": 0, "col": spine_col,
                    "clue": CLUES[spine]})
    entries.sort(key=lambda e: (e["dir"] != "Across", e["num"]))
    return {"rows": len(spine), "cols": width, "entries": entries, "numbers": numbers, "number": puzzle_number(day)}


def cells_of(entry: dict) -> list[tuple[int, int]]:
    if entry["dir"] == "Across":
        return [(entry["row"], entry["col"] + i) for i in range(len(entry["word"]))]
    return [(entry["row"] + i, entry["col"]) for i in range(len(entry["word"]))]


def puzzle_state(day: date | None = None) -> dict:
    """Today's crossword plus your progress: solved answers, revealed letters, and how many checks."""
    day = day or date.today()
    cw = make_crossword(day)
    saved = storage.load_puzzles().get(day.isoformat(), {})
    solved = set(saved.get("solved", []))
    revealed = saved.get("revealed", {})
    letters = {}  # (row, col) -> letter shown in the grid
    for e in cw["entries"]:
        cells = cells_of(e)
        shown = len(e["word"]) if e["id"] in solved else int(revealed.get(e["id"], 0))
        for (r, c), ch in list(zip(cells, e["word"]))[:shown]:
            letters[(r, c)] = ch
    for e in cw["entries"]:  # a word is also solved if crossing words revealed all of its letters
        if all(cell in letters for cell in cells_of(e)):
            solved.add(e["id"])
    return {**cw, "solved": solved, "letters": letters, "checks": saved.get("checks", 0),
            "hints": sum(int(v) for v in revealed.values()), "over": len(solved) == len(cw["entries"])}


def check_answers(answers: dict) -> dict:
    """answers: {entry id: typed word}. Saves the correct ones. Returns {entry id: True/False} for what was typed."""
    day = date.today().isoformat()
    cw = make_crossword()
    data = storage.load_puzzles()
    saved = data.setdefault(day, {})
    saved["checks"] = saved.get("checks", 0) + 1
    result = {}
    for e in cw["entries"]:
        typed = "".join(ch for ch in (answers.get(e["id"]) or "").upper() if ch.isalpha())
        if typed:
            result[e["id"]] = typed == e["word"]
            if result[e["id"]]:
                saved.setdefault("solved", [])
                if e["id"] not in saved["solved"]:
                    saved["solved"].append(e["id"])
    storage.save_puzzles(data)
    return result


def reveal_letter(entry_id: str) -> None:
    day = date.today().isoformat()
    data = storage.load_puzzles()
    saved = data.setdefault(day, {})
    saved.setdefault("revealed", {})
    saved["revealed"][entry_id] = int(saved["revealed"].get(entry_id, 0)) + 1
    storage.save_puzzles(data)


def crossword_html(state: dict) -> str:
    """The grid: white boxes with clue numbers, filled letters, and nothing where there's no box."""
    used = {cell for e in state["entries"] for cell in cells_of(e)}
    rows = []
    for r in range(state["rows"]):
        cells = []
        for c in range(state["cols"]):
            if (r, c) not in used:
                cells.append('<div class="cw-cell cw-empty"></div>')
                continue
            num = state["numbers"].get((r, c))
            letter = state["letters"].get((r, c), "")
            cells.append(f'<div class="cw-cell{" cw-filled" if letter else ""}">'
                         f'{f"<span class=cw-num>{num}</span>" if num else ""}{letter}</div>')
        rows.append(f'<div class="cw-row">{"".join(cells)}</div>')
    return f'<div class="cw-grid">{"".join(rows)}</div>'


def puzzle_share(state: dict) -> str:
    hints = f", {state['hints']} hint{'s' if state['hints'] != 1 else ''}" if state["hints"] else ", no hints"
    return (f"🌿 Tulsi Crossword #{state['number']} solved! ✅\n{len(state['entries'])} words, "
            f"{state['checks']} check{'s' if state['checks'] != 1 else ''}{hints}\nCan you solve today's in FitBuddy?")


def whatsapp(text: str) -> str:
    return "https://wa.me/?text=" + quote(text)
