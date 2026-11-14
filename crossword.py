"""
crossword.py - newspaper-style crosswords about health, food and feeling good.

How a puzzle is built (automatically, so there's a fresh one every time):
  1. Pick a theme's words (or all themes for "Today's crossword").
  2. Place the longest word across the middle.
  3. For each next word, try every spot where it could cross a letter already on the grid, and keep the
     spot with the most crossings. A spot is only allowed if the new word doesn't touch other words side by
     side (that would create nonsense words), and the grid stays a reasonable size.
  4. Number the starts of the words in reading order, like a newspaper.
The random choices use a "seed" (for example today's date), so the same seed always gives the same puzzle.
That's how everyone gets the same daily crossword without any server.
"""

import random
import re
from datetime import date

import storage

THEMES = {
    "🍛 Kerala food": {
        "PUTTU": "Steamed rice cylinder, a Kerala breakfast", "APPAM": "Lacy Kerala pancake with a soft centre",
        "AVIAL": "Mixed vegetables with coconut and curd", "THORAN": "Stir-fried veg with grated coconut",
        "SAMBAR": "Lentil and vegetable stew", "RASAM": "Tangy, peppery South Indian soup",
        "IDIYAPPAM": "String hoppers made of rice noodles", "PAYASAM": "Sweet milky dessert served at Onam",
        "UPMA": "Savoury semolina breakfast", "DOSA": "Thin, crispy South Indian crepe", "IDLI": "Soft steamed rice cake",
        "KADALA": "Black chickpea curry served with puttu", "OLAN": "Mild ash gourd curry with coconut milk",
        "ERISSERY": "Pumpkin and bean curry with roasted coconut", "KANJI": "Comforting rice porridge",
        "MORU": "Spiced buttermilk", "CHUTNEY": "Coconut dip served with dosa", "PAPPADAM": "Crispy thin disc eaten with rice",
        "PAROTTA": "Flaky layered flatbread",
    },
    "🍎 Fruits & veggies": {
        "MANGO": "King of fruits in summer", "GUAVA": "Green fruit packed with vitamin C",
        "LEMON": "Squeeze this into water for zing", "APPLE": "One a day keeps the doctor away, they say",
        "BANANA": "Yellow fruit full of potassium", "PAPAYA": "Orange fruit that's good for digestion",
        "ORANGE": "Citrus fruit that shares its name with a colour", "GRAPES": "Small fruits that grow in bunches",
        "SPINACH": "Palak, a leafy green", "CARROT": "Orange root, crunchy and sweet", "BEETROOT": "Deep red root vegetable",
        "CABBAGE": "Round leafy veg, used in thoran", "PUMPKIN": "Big orange vegetable used in erissery",
        "TOMATO": "Red fruit used in rasam", "ONION": "Makes you cry when you chop it", "OKRA": "Ladies' finger",
        "BRINJAL": "Purple vegetable, also called eggplant", "CUCUMBER": "Cool green salad vegetable",
        "COCONUT": "Kerala's favourite tree fruit", "JACKFRUIT": "Huge spiky fruit, Kerala's state fruit",
    },
    "🏃‍♀️ Exercise": {
        "WALK": "A gentle 15-minute one after meals helps", "YOGA": "Practice with poses like Tree and Child's pose",
        "DANCE": "Move to music: fun cardio!", "PLANK": "Hold your body straight like a board",
        "SQUAT": "Bend your knees as if sitting on a chair", "LUNGE": "Step forward and bend both knees",
        "JOG": "Run slowly", "SWIM": "Exercise in a pool", "HIKE": "A long walk up a hill",
        "STRETCH": "Reach your arms up high and ___", "SKIPPING": "Jumping over a rope",
        "PILATES": "Core-strengthening mat workout", "ZUMBA": "Dance workout to Latin music",
        "BURPEE": "Squat, jump back, jump up: a tough move!", "CRUNCH": "Tummy exercise lying on your back",
        "STEPS": "A pedometer counts these", "AEROBICS": "Cardio workout often done to music",
        "BADMINTON": "Racket sport with a shuttlecock", "CYCLING": "Riding a bicycle",
    },
    "🧘 Mind & feelings": {
        "SMILE": "Curved line on a happy face", "RELAX": "Unwind and let go", "CALM": "Peaceful, not stressed",
        "HAPPY": "Joyful", "PEACE": "Calm and quiet", "MOOD": "How you feel", "JOURNAL": "A notebook for your thoughts",
        "GRATEFUL": "Thankful", "BREATHE": "Slowly in... and out", "LAUGH": "What you do at a good joke",
        "HOPE": "Believing good things can happen", "KIND": "Gentle and caring", "BRAVE": "Courageous",
        "PROUD": "How you feel about your small wins", "TRUST": "Believe in someone", "FOCUS": "Pay full attention",
        "MUSIC": "Songs and melodies", "FRIEND": "Someone you call when you need a laugh",
        "NATURE": "Trees, flowers and fresh air",
    },
    "🌿 Herbs & spices": {
        "TULSI": "Holy basil, and our coach's name", "CUMIN": "Jeera", "GINGER": "Root that goes in chai",
        "TURMERIC": "Golden spice, haldi", "CINNAMON": "Sweet bark spice, dalchini", "CARDAMOM": "Green pods, elaichi",
        "PEPPER": "Black spice Kerala is famous for", "GARLIC": "Strong-smelling bulb, lahsun", "CLOVES": "Small nail-shaped spice",
        "FENUGREEK": "Methi", "MINT": "Pudina, fresh and cool", "BASIL": "Herb used in pesto", "MUSTARD": "Tiny seeds that pop in hot oil",
        "AJWAIN": "Carom seeds", "SAFFRON": "Precious red threads, kesar", "FENNEL": "Saunf, chewed after meals",
        "CORIANDER": "Dhania leaves and seeds",
    },
    "🩺 Body & PCOS": {
        "HEART": "It pumps blood around your body", "BRAIN": "Your thinking organ",
        "CYCLE": "Menstrual ___, which you can track in FitBuddy", "OVARY": "Where eggs are stored",
        "INSULIN": "Hormone that helps your body use sugar", "HORMONE": "Chemical messenger in your body",
        "PERIOD": "Monthly bleed", "FIBRE": "Found in veggies, it helps digestion", "PROTEIN": "Builds muscle: eggs, dal, paneer",
        "IRON": "Mineral in spinach and dates that helps your blood", "VITAMIN": "D is one you get from sunlight",
        "SUGAR": "Too much of this spikes your energy, then crashes it", "WATER": "Drink 8 glasses of this a day",
        "MUSCLE": "Strength training builds this", "SKIN": "Your body's largest organ", "HAIR": "Grows on your head",
        "DOCTOR": "See one for regular check-ups", "THYROID": "Gland in your neck that controls energy",
    },
    "😴 Sleep & rest": {
        "SLEEP": "Aim for 7 to 9 hours of this", "NAP": "A short daytime sleep", "REST": "Take a break and ___",
        "DREAM": "Story your mind tells while you sleep", "PILLOW": "Soft thing under your head",
        "BLANKET": "Keeps you warm in bed", "BEDTIME": "When you go to sleep", "MOON": "Shines in the night sky",
        "NIGHT": "Time after sunset", "YAWN": "Sign that you're sleepy", "SNOOZE": "Button for five more minutes",
        "ALARM": "It wakes you up", "QUIET": "Without noise", "DARK": "A sleep-friendly room is cool and ___",
        "LULLABY": "Song sung to help a baby sleep", "MELATONIN": "Sleep hormone your body makes in the dark",
        "CORTISOL": "Stress hormone that poor sleep can raise",
    },
}
ALL_WORDS = {w: c for theme in THEMES.values() for w, c in theme.items()}
LAUNCH = date(2026, 11, 1)


def puzzle_number(day: date | None = None) -> int:
    return ((day or date.today()) - LAUNCH).days + 1


# ---------------------------------------------------------------- building the grid

def _can_place(grid: dict, dirs: dict, word: str, r: int, c: int, d: str) -> int:
    """How many letters this word would share with the grid, or -1 if it can't go here."""
    dr, dc = (0, 1) if d == "A" else (1, 0)
    if (r - dr, c - dc) in grid or (r + dr * len(word), c + dc * len(word)) in grid:
        return -1  # touching another word at either end
    crossings = 0
    for k, ch in enumerate(word):
        cell = (r + dr * k, c + dc * k)
        if cell in grid:
            if grid[cell] != ch or d in dirs[cell]:
                return -1
            crossings += 1
        else:
            side1, side2 = ((cell[0] - 1, cell[1]), (cell[0] + 1, cell[1])) if d == "A" else \
                           ((cell[0], cell[1] - 1), (cell[0], cell[1] + 1))
            if side1 in grid or side2 in grid:
                return -1  # would sit right next to another word
    return crossings


def _place(grid, dirs, word, r, c, d):
    dr, dc = (0, 1) if d == "A" else (1, 0)
    for k, ch in enumerate(word):
        cell = (r + dr * k, c + dc * k)
        grid[cell] = ch
        dirs.setdefault(cell, set()).add(d)


def _build_once(words: list[str], rng: random.Random, target: int, max_size: int):
    grid, dirs, placed = {}, {}, []
    first, *rest = words
    _place(grid, dirs, first, 0, 0, "A")
    placed.append((first, 0, 0, "A"))
    for word in rest:
        if len(placed) >= target:
            break
        options = []
        for (r, c), letter in list(grid.items()):
            for i, ch in enumerate(word):
                if ch != letter:
                    continue
                for d in ("A", "D"):
                    sr, sc = (r, c - i) if d == "A" else (r - i, c)
                    score = _can_place(grid, dirs, word, sr, sc, d)
                    if score < 1:
                        continue
                    cells = list(grid) + [(sr + (k if d == "D" else 0), sc + (k if d == "A" else 0)) for k in range(len(word))]
                    height = max(x for x, _ in cells) - min(x for x, _ in cells) + 1
                    width = max(y for _, y in cells) - min(y for _, y in cells) + 1
                    if height > max_size or width > max_size:
                        continue
                    options.append((score, -(height * width), rng.random(), sr, sc, d))
        if options:
            _, _, _, sr, sc, d = max(options)
            _place(grid, dirs, word, sr, sc, d)
            placed.append((word, sr, sc, d))
    return grid, placed


def build(clues: dict, seed: str, target: int = 10, max_size: int = 13) -> dict:
    """Makes a crossword from {WORD: clue}. Tries several times and keeps the best (most words, then most compact)."""
    rng = random.Random(seed)
    best = None
    for _ in range(25):
        words = sorted(clues)
        rng.shuffle(words)
        words = sorted(words[:30], key=len, reverse=True)[:1] + words[:30]
        words = list(dict.fromkeys(words))  # the longest is first, no duplicates
        grid, placed = _build_once(words, rng, target, max_size)
        rows = {r for r, _ in grid}
        cols = {c for _, c in grid}
        quality = (len(placed), -(len(rows) * len(cols)))
        if best is None or quality > best[0]:
            best = (quality, grid, placed)
    _, grid, placed = best

    # shift everything so the grid starts at (0, 0)
    r0 = min(r for r, _ in grid)
    c0 = min(c for _, c in grid)
    placed = [(w, r - r0, c - c0, d) for w, r, c, d in placed]
    starts = sorted({(r, c) for _, r, c, _ in placed})
    numbers = {cell: n + 1 for n, cell in enumerate(starts)}
    entries = []
    for w, r, c, d in placed:
        num = numbers[(r, c)]
        entries.append({"id": f"{num}{d}", "num": num, "dir": "Across" if d == "A" else "Down", "word": w,
                        "row": r, "col": c, "clue": clues[w]})
    entries.sort(key=lambda e: (e["dir"] != "Across", e["num"]))
    return {"rows": max(r for r, _ in grid) - r0 + 1, "cols": max(c for _, c in grid) - c0 + 1,
            "entries": entries, "numbers": numbers}


def cells_of(entry: dict) -> list[tuple[int, int]]:
    if entry["dir"] == "Across":
        return [(entry["row"], entry["col"] + i) for i in range(len(entry["word"]))]
    return [(entry["row"] + i, entry["col"]) for i in range(len(entry["word"]))]


# ---------------------------------------------------------------- choosing a puzzle

def daily(day: date | None = None) -> tuple[str, str, dict]:
    """(key, title, crossword): today's mixed-theme puzzle, the same for everyone."""
    day = day or date.today()
    return f"daily:{day.isoformat()}", f"Tulsi Crossword #{puzzle_number(day)}", build(ALL_WORDS, f"daily-{day.isoformat()}")


def themed(theme: str, round_no: int = 0) -> tuple[str, str, dict]:
    return (f"theme:{theme}:{round_no}", f"{theme} crossword",
            build(THEMES[theme], f"{theme}-{round_no}", target=9))


def slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:40]


def custom(theme: str, clues: dict, round_no: int = 0) -> tuple[str, str, dict]:
    return f"custom:{slug(theme)}:{round_no}", f"{theme.strip().title()} crossword", build(clues, f"{slug(theme)}-{round_no}", target=9)


def clean_word_list(items: list) -> dict:
    """Keeps only usable AI-made words: single words, letters only, 3-10 letters, each with a clue."""
    out = {}
    for item in items or []:
        if not isinstance(item, dict):
            continue
        raw = str(item.get("word", "")).strip()
        if not raw.isalpha():  # skip phrases like "two words" or "ice-cream" instead of squashing them together
            continue
        word = raw.upper()
        clue = str(item.get("clue", "")).strip()
        if 3 <= len(word) <= 10 and clue and word.lower() not in clue.lower():
            out[word] = clue[:90]
    return out


# ---------------------------------------------------------------- progress

def state(key: str, cw: dict) -> dict:
    saved = storage.load_puzzles().get(key, {})
    solved = set(saved.get("solved", []))
    revealed = saved.get("revealed", {})
    letters = {}
    for e in cw["entries"]:
        shown = len(e["word"]) if e["id"] in solved else int(revealed.get(e["id"], 0))
        for cell, ch in list(zip(cells_of(e), e["word"]))[:shown]:
            letters[cell] = ch
    for e in cw["entries"]:  # crossing words can complete a word too
        if all(cell in letters for cell in cells_of(e)):
            solved.add(e["id"])
    return {**cw, "key": key, "solved": solved, "letters": letters, "checks": saved.get("checks", 0),
            "hints": sum(int(v) for v in revealed.values()), "over": len(solved) == len(cw["entries"])}


def check(key: str, cw: dict, answers: dict) -> dict:
    data = storage.load_puzzles()
    saved = data.setdefault(key, {})
    saved["checks"] = saved.get("checks", 0) + 1
    result = {}
    for e in cw["entries"]:
        typed = re.sub(r"[^A-Z]", "", (answers.get(e["id"]) or "").upper())
        if typed:
            result[e["id"]] = typed == e["word"]
            if result[e["id"]] and e["id"] not in saved.setdefault("solved", []):
                saved["solved"].append(e["id"])
    storage.save_puzzles(data)
    return result


def reveal(key: str, entry_id: str) -> None:
    data = storage.load_puzzles()
    saved = data.setdefault(key, {})
    saved.setdefault("revealed", {})
    saved["revealed"][entry_id] = int(saved["revealed"].get(entry_id, 0)) + 1
    storage.save_puzzles(data)


def grid_html(st_: dict) -> str:
    used = {cell for e in st_["entries"] for cell in cells_of(e)}
    rows = []
    for r in range(st_["rows"]):
        cells = []
        for c in range(st_["cols"]):
            if (r, c) not in used:
                cells.append('<div class="cw-cell cw-empty"></div>')
                continue
            num = st_["numbers"].get((r, c))
            letter = st_["letters"].get((r, c), "")
            cells.append(f'<div class="cw-cell{" cw-filled" if letter else ""}">'
                         f'{f"<span class=cw-num>{num}</span>" if num else ""}{letter}</div>')
        rows.append(f'<div class="cw-row">{"".join(cells)}</div>')
    return f'<div class="cw-grid">{"".join(rows)}</div>'


def share_text(st_: dict, title: str) -> str:
    hints = f"{st_['hints']} hint{'s' if st_['hints'] != 1 else ''}" if st_["hints"] else "no hints"
    return f"🌿 {title} solved! ✅\n{len(st_['entries'])} words, {hints}\nCome solve one in FitBuddy!"
