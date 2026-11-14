"""
games.py - two small games designed to feel good without being addictive.

1. Wellness Bingo (weekly): everyone gets the SAME 5x5 card each week, so friends can play together.
   Squares are small real-life self-care tasks. Some tick themselves from your data (water, sleep, movement).
   Finish a row, column or diagonal for a bingo. A new card arrives every Monday.

2. Daily Puzzle (one a day): guess the 5-letter health word in 6 tries, like Wordle.
   Everyone gets the same word that day, so you can compare on WhatsApp. One puzzle a day, then it's done.
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


# ---------------------------------------------------------------- Daily Puzzle

# Five-letter words about health, food and feeling good, each with a gentle fact shown after the puzzle.
WORDS = {
    "WATER": "Even mild dehydration can feel like tiredness or hunger. A glass of water is a great first step.",
    "SLEEP": "Good sleep helps balance hunger hormones, which can make cravings easier to manage.",
    "TULSI": "Tulsi (holy basil) tea is a calming, caffeine-free drink many people enjoy in the evening.",
    "DANCE": "Dancing counts as exercise, and it's one of the most fun ways to move.",
    "SMILE": "Smiling and laughing can help you feel calmer, even on hard days.",
    "GUAVA": "Guava is rich in fibre and vitamin C, which makes it a great fruit snack.",
    "LEMON": "A squeeze of lemon makes plain water more refreshing to sip through the day.",
    "SEEDS": "Flax, chia and pumpkin seeds add fibre, healthy fats and a little protein to meals.",
    "BEANS": "Beans and lentils give protein and fibre, which help keep blood sugar steadier.",
    "SALAD": "Starting a meal with salad or veggies adds fibre and can help you feel full sooner.",
    "CURDS": "Curd (yoghurt) contains probiotics, which support a healthy gut.",
    "RASAM": "Rasam is light, warming and a lovely way to add spices like pepper and cumin.",
    "PUTTU": "Pairing puttu with kadala curry adds protein, which keeps you fuller for longer.",
    "APPAM": "Appam with a vegetable or egg stew makes a more balanced breakfast.",
    "CUMIN": "Cumin (jeera) adds warmth and flavour, and jeera water is a popular gentle drink.",
    "BASIL": "Fresh herbs like basil add flavour without extra salt or sugar.",
    "COCOA": "Dark chocolate with more cocoa usually has less sugar than milk chocolate.",
    "BRAIN": "Your brain loves sleep, water, movement and omega-3s from walnuts, seeds and fish.",
    "HEART": "Regular walking is one of the simplest things you can do for your heart.",
    "RELAX": "A few slow breaths, with a longer breath out than in, can help your body relax.",
    "PEACE": "A few quiet minutes a day without screens can lower stress.",
    "HAPPY": "Sunlight in the morning can lift your mood and help your sleep at night.",
    "LAUGH": "Laughing with friends is good for your mood and helps ease stress.",
    "STEPS": "Every step counts. Short walks after meals can help with blood sugar.",
    "WALKS": "A 10-minute walk after a meal is a small habit with big benefits.",
    "FOCUS": "Short movement breaks can help you focus better at work or study.",
    "BLOOM": "Progress is like a plant growing: slow, steady and real, even when you can't see it daily.",
    "LOTUS": "Lotus pose and other gentle yoga poses can help calm the mind.",
    "SUNNY": "Sunlight helps your body make vitamin D. Low vitamin D is common in PCOS, so ask your doctor to check yours.",
    "FRESH": "Fresh, home-cooked food usually has less hidden sugar and salt than packaged food.",
    "CYCLE": "Tracking your cycle helps you understand your energy, cravings and moods.",
    "FIBRE": "Fibre from vegetables, whole grains and dal helps keep blood sugar steadier.",
    "PLANT": "Filling half your plate with plants is an easy rule for balanced meals.",
    "PETAL": "Small wins add up, like petals making a flower.",
    "MANGO": "Mango is delicious in season. Pairing it with nuts or curd makes it a more filling snack.",
    "APPLE": "An apple with a few nuts is a quick, balanced snack.",
    "GRAPE": "Frozen grapes are a refreshing swap for sweets on a hot day.",
    "HONEY": "Honey is still sugar, so a drizzle goes a long way.",
    "SPICE": "Spices like turmeric, cinnamon and ginger add flavour to healthy cooking.",
    "YOGIC": "Yogic breathing (pranayama) is a calming practice you can do anywhere.",
    "SWEAT": "A little sweat from exercise is a sign your body is working. Drink water after!",
    "TRUST": "Trust the process. Health changes take weeks, not days.",
    "PROUD": "Be proud of the small steps. They're the ones that last.",
}
LAUNCH = date(2026, 11, 1)  # puzzle #1


def puzzle_number(day: date | None = None) -> int:
    return ((day or date.today()) - LAUNCH).days + 1


def word_of_the_day(day: date | None = None) -> str:
    """Same word for everyone on the same day (the day is the seed)."""
    words = sorted(WORDS)
    random.Random(f"tulsi-{(day or date.today()).isoformat()}").shuffle(words)
    return words[0]


def score_guess(guess: str, answer: str) -> list[str]:
    """Colours for each letter, like Wordle: 'g' right place, 'y' in the word elsewhere, 'x' not in the word.
    Repeated letters are handled properly (a letter is only marked as many times as it appears)."""
    result = ["x"] * 5
    remaining = {}
    for i, (g, a) in enumerate(zip(guess, answer)):
        if g == a:
            result[i] = "g"
        else:
            remaining[a] = remaining.get(a, 0) + 1
    for i, g in enumerate(guess):
        if result[i] == "x" and remaining.get(g, 0) > 0:
            result[i] = "y"
            remaining[g] -= 1
    return result


def puzzle_state(day: date | None = None) -> dict:
    day = day or date.today()
    data = storage.load_puzzles().get(day.isoformat(), {"guesses": []})
    answer = word_of_the_day(day)
    guesses = data["guesses"]
    won = bool(guesses) and guesses[-1] == answer
    return {"answer": answer, "guesses": guesses, "won": won, "over": won or len(guesses) >= 6,
            "number": puzzle_number(day)}


def puzzle_share(state: dict) -> str:
    emoji = {"g": "🟩", "y": "🟨", "x": "⬜"}
    rows = ["".join(emoji[c] for c in score_guess(g, state["answer"])) for g in state["guesses"]]
    tries = f"{len(state['guesses'])}/6" if state["won"] else "X/6"
    return f"🌿 Tulsi Word #{state['number']} {tries}\n" + "\n".join(rows) + "\nPlay today's word in FitBuddy!"


def whatsapp(text: str) -> str:
    return "https://wa.me/?text=" + quote(text)
