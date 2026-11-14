"""
coach.py - everything that talks to the AI.

We use OpenRouter, which gives one API to many AI models. The model name
lives in the .env file, so switching to Claude later is a one-line change.
"""

import os
import random

import requests
from dotenv import load_dotenv

load_dotenv()

API_URL = "https://openrouter.ai/api/v1/chat/completions"
DEFAULT_MODEL = "baidu/ernie-5.5-flash-preview:free"


class CoachError(Exception):
    """A friendly error we can show directly in the app."""


# ---------- The coach's personality and safety rules ----------
# This is the "system prompt": instructions the AI follows in every reply.

SYSTEM_PROMPT = """You are Tulsi 🌿, a cheerful little sprout and the user's personal health coach
inside the FitBuddy app. You're like a supportive best friend who knows a lot about health:
warm, playful, encouraging and never judgemental. Many users have faced body-shaming and feel
uncomfortable in gyms, so you make them feel safe, respected and capable.

HOW YOU WRITE (very important - you are chatting like on WhatsApp)
- Send 2 to 4 SHORT chat messages. Separate each message with a line containing only: ---
- Exception: for a meal plan, workout plan or list of ideas (even if the user asks in their own words,
  e.g. "give me a different diet plan"), send up to 9 messages, one per day or section.
- Each message is 1-2 short sentences, or a short list of up to 4 bullet points.
- Never write long paragraphs. Use the user's name sometimes and a few friendly emojis (not too many).
- Sound like a real friend texting, not a report. No headings.
- Example:
  Hey Aysha! 🌸 A 60-minute walk on day one of your period? That's honestly amazing.
  ---
  You slept 7 hours and stress was low, so your body's in a calm place today 💜
  ---
  Plan for tomorrow:
  - 20 min gentle walk or yoga 🧘‍♀️
  - Eggs or dal with lunch for protein
  - Same bedtime as tonight 😴

HOW YOU COACH
- Always be kind and positive. Never shame, guilt or criticise the user's body, food or effort.
- Celebrate small wins (steps walked, water drunk, a good night's sleep, simply checking in).
- Look at the whole WEEK, not one day. One high-calorie day is normal and not a failure.
- NEVER tell the user to "burn off" or "make up for" food with extra exercise. Exercise is for
  strength, energy and mood - never punishment.
- Suggest home-friendly, low-impact exercise (walking, yoga, stretching, bodyweight strength,
  dancing) unless the user asks for something else.

SLEEP, STRESS AND CORTISOL
- Poor sleep (under ~6 hours) or high stress (4-5 out of 5) raises cortisol, which can make
  weight loss harder, especially with PCOS. On those days recommend gentle movement
  (walking, yoga, stretching), rest and stress relief - NOT intense workouts.
- When sleep and energy are good, it is fine to suggest a slightly more active day.

PCOS AND HEALTH CONDITIONS
- Use the user's health profile to personalise advice (e.g. PCOS: steady meals with protein and
  fibre, strength training, consistent sleep, stress management).

SAFETY RULES (always follow)
- You are not a doctor. Never diagnose, and never advise starting, stopping or changing medication.
- If the user mentions worrying symptoms (pain, dizziness, missed periods, fainting, etc.),
  kindly suggest they speak to their doctor.
- Never suggest eating less than 1200 kcal per day, skipping meals, fasting for long periods or
  any extreme diet.
- If the user shows signs of an unhealthy relationship with food or exercise, respond with care
  and gently encourage talking to a doctor or someone they trust.
"""


def _env_list(name: str, default: str) -> list[str]:
    return [m.strip() for m in os.getenv(name, default).split(",") if m.strip()]


def _has_key(name: str) -> bool:
    key = os.getenv(name, "").strip()
    return bool(key) and not key.startswith("paste")


class _TryNext(Exception):
    """This model didn't work; move on to the next one."""


def _openrouter(model: str, messages: list[dict], max_tokens: int, temperature: float) -> str:
    headers = {
        "Authorization": f"Bearer {os.getenv('OPENROUTER_API_KEY', '').strip()}",
        "Content-Type": "application/json",
        "X-Title": "FitBuddy AI Coach",
    }
    payload = {"model": model, "messages": messages, "max_tokens": max_tokens, "temperature": temperature}
    response = requests.post(API_URL, headers=headers, json=payload, timeout=90)
    if response.status_code == 401:
        raise _TryNext("Your OpenRouter key was rejected. Check OPENROUTER_API_KEY in your .env file.")
    if response.status_code == 402:
        raise _TryNext(f"{model} needs credits.")
    if response.status_code == 429:
        raise _TryNext(f"{model} is busy right now.")
    if response.status_code != 200:
        raise _TryNext(f"{model} returned an error ({response.status_code}).")
    try:
        data = response.json()
        if "error" in data:
            raise _TryNext(f"{model}: {data['error'].get('message', 'error')}")
        content = data["choices"][0]["message"].get("content") or ""
        if isinstance(content, list):  # some models send a list of text parts
            content = "".join(part.get("text", "") for part in content if isinstance(part, dict))
    except (KeyError, IndexError, ValueError, TypeError, AttributeError):
        raise _TryNext(f"{model} sent back an unexpected reply.")
    if not content.strip():
        raise _TryNext(f"{model} sent back an empty reply.")
    return content.strip()


def _gemini(model: str, messages: list[dict], max_tokens: int, temperature: float) -> str:
    """Gemini uses a different message format: system text goes in systemInstruction,
    and the assistant's role is called "model"."""
    system = "\n\n".join(m["content"] for m in messages if m["role"] == "system")
    contents = []
    for m in messages:
        if m["role"] == "system":
            continue
        role = "model" if m["role"] == "assistant" else "user"
        if contents and contents[-1]["role"] == role:  # merge back-to-back messages from the same side
            contents[-1]["parts"][0]["text"] += "\n\n" + m["content"]
        else:
            contents.append({"role": role, "parts": [{"text": m["content"]}]})
    if not contents or contents[0]["role"] != "user":
        contents.insert(0, {"role": "user", "parts": [{"text": "Hi Tulsi!"}]})

    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    body = {
        "systemInstruction": {"parts": [{"text": system}]},
        "contents": contents,
        "generationConfig": {"maxOutputTokens": max_tokens, "temperature": temperature},
    }
    headers = {"x-goog-api-key": os.getenv("GEMINI_API_KEY", "").strip(), "Content-Type": "application/json"}
    response = requests.post(url, headers=headers, json=body, timeout=90)
    if response.status_code == 429:
        raise _TryNext("The free Gemini limit was reached. Wait a minute and try again.")
    if response.status_code != 200:
        raise _TryNext(f"{model} returned an error ({response.status_code}).")
    try:
        parts = response.json()["candidates"][0]["content"]["parts"]
        text = "".join(p.get("text", "") for p in parts if not p.get("thought"))
    except (KeyError, IndexError, ValueError, TypeError):
        raise _TryNext(f"{model} sent back an unexpected reply.")
    if not text.strip():
        raise _TryNext(f"{model} sent back an empty reply.")
    return text.strip()


def call_ai(messages: list[dict], max_tokens: int = 1200, temperature: float = 0.7) -> str:
    """Send messages to the AI and return its text reply.
    Tries each OpenRouter model, then each Gemini model, until one works."""
    attempts = []
    if _has_key("OPENROUTER_API_KEY"):
        attempts += [(_openrouter, m) for m in _env_list("OPENROUTER_MODEL", DEFAULT_MODEL)]
    if _has_key("GEMINI_API_KEY"):
        attempts += [(_gemini, m) for m in _env_list("GEMINI_MODEL", "gemini-3.1-flash-lite,gemini-3.5-flash")]
    if not attempts:
        raise CoachError("No API key found. Open the .env file, paste your key(s), then restart the app.")

    last_error = ""
    for provider, model in attempts:
        try:
            return provider(model, messages, max_tokens, temperature)
        except _TryNext as err:
            last_error = str(err)
        except requests.RequestException:
            last_error = "Couldn't reach the AI. Check your internet connection."
    raise CoachError(f"Tulsi couldn't reply right now ({last_error}). Please try again in a minute.")


# ---------- Turning the user's data into context for the AI ----------

def profile_to_text(profile: dict) -> str:
    if not profile:
        return "The user has not filled in a health profile yet."
    lines = ["USER HEALTH PROFILE"]
    labels = {
        "name": "Name",
        "age": "Age",
        "height_cm": "Height (cm)",
        "current_weight_kg": "Current weight (kg)",
        "goal_weight_kg": "Goal weight (kg)",
        "calorie_target": "Daily calorie target (kcal)",
        "conditions": "Health conditions",
        "medications": "Medications",
        "cycle": "Menstrual cycle",
        "diet": "Diet / food preferences",
        "allergies": "Allergies",
        "limitations": "Injuries / exercise limitations",
        "goals": "Personal goals",
        "notes": "Other notes",
        "report_summary": "Summary of uploaded medical reports",
    }
    for key, label in labels.items():
        value = profile.get(key)
        if value not in (None, "", [], 0):
            if isinstance(value, list):
                value = ", ".join(value)
            lines.append(f"- {label}: {value}")
    return "\n".join(lines)


def checkins_to_text(checkins: dict) -> str:
    if not checkins:
        return "No daily check-ins recorded this week yet."
    lines = ["DAILY CHECK-INS (last 7 days, oldest first)"]
    for day, c in checkins.items():
        lines.append(
            f"- {day}: sleep {c.get('sleep_hours')}h, steps {c.get('steps')}, "
            f"distance {c.get('distance_km')} km, calories eaten {c.get('calories') or 'not logged'}, "
            f"exercise: {c.get('exercise') or 'none'} ({c.get('exercise_minutes', 0)} min), "
            f"stress {c.get('stress')}/5, energy {c.get('energy')}/5, mood: {c.get('mood')}, "
            f"foods eaten: {c.get('foods') or 'not logged'}, notes: {c.get('notes') or '-'}"
        )
    return "\n".join(lines)


def samsung_to_text(daily: dict) -> str:
    if not daily:
        return ""
    lines = ["ACTIVITY FROM SAMSUNG HEALTH (last 14 days)"]
    for day, d in daily.items():
        parts = [f"{int(d['steps'])} steps" if "steps" in d else "",
                 f"{d['distance_km']} km" if "distance_km" in d else "",
                 f"walks {d['workout_min']} min" if "workout_min" in d else "",
                 f"sleep {d['sleep_hours']}h" if "sleep_hours" in d else "",
                 f"weight {d['weight_kg']} kg" if "weight_kg" in d else ""]
        lines.append(f"- {day}: " + ", ".join(p for p in parts if p))
    return "\n".join(lines)


def journey_to_text(profile: dict) -> str:
    """Cycle phase, water, wins, badges and Tulsi's growth, so the coach can mention them."""
    from datetime import date, timedelta
    import journey
    import storage
    rows = journey.all_days()
    lines = ["TODAY'S EXTRA CONTEXT"]
    cyc = journey.cycle_info()
    if cyc:
        lines.append(f"- Menstrual cycle: day {cyc['day']} ({cyc['phase']} phase), average cycle "
                     f"{cyc['length']} days{' (irregular)' if cyc['irregular'] else ''}. "
                     "Tailor food and exercise advice to this phase.")
    lines.append(f"- Water today: {storage.water_today(date.today().isoformat())} of 8 glasses")
    g = journey.growth(profile, rows)
    goal = g["goal"]
    if goal["pct"] is not None:
        lines.append(f"- Weight journey: started {goal['start']} kg, now {goal['current']} kg, goal "
                     f"{goal['goal']} kg ({goal['pct']:.0f}% of the way, {goal['lost']} kg lost).")
    lines.append(f"- Tulsi (you, the plant) has grown to stage: {g['name']} {g['emoji']}.")
    earned = [b["name"] for b in journey.badges(profile, rows) if b["earned"]]
    if earned:
        lines.append(f"- Badges earned: {', '.join(earned)}")
    recent_sym = {d: v for d, v in journey.symptom_days().items()
                  if d >= (date.today() - timedelta(days=7)).isoformat()}
    if recent_sym:
        worst = {}
        for v in recent_sym.values():
            for k, lvl in v.items():
                worst[k] = max(worst.get(k, 0), int(lvl))
        listed = [f"{journey.SYMPTOMS[k]} ({journey.LEVELS[l].lower()})" for k, l in worst.items() if l > 0 and k in journey.SYMPTOMS]
        if listed:
            lines.append("- PCOS symptoms logged this week: " + ", ".join(listed))
    for insight in journey.symptom_insights()[:3]:
        lines.append(f"- Pattern noticed: {insight}")
    week_ago = (date.today() - timedelta(days=7)).isoformat()
    cravings = [c for c in storage.load_cravings() if c["when"][:10] >= week_ago]
    if cravings:
        lines.append(f"- Cravings logged this week: {len(cravings)} "
                     f"(mostly {max(set(c['kind'] for c in cravings), key=[c['kind'] for c in cravings].count)}; "
                     f"triggers: {', '.join(sorted(set(c.get('trigger', '') for c in cravings)))})")
    try:
        import exercise
        today_ex = exercise.day_total(date.today().isoformat())
        goal = int(profile.get("burn_goal") or exercise.DEFAULT_GOAL)
        lines.append(f"- Exercise today: {today_ex['minutes']} min, about {today_ex['kcal']} kcal burned (daily goal {goal} kcal).")
    except Exception:
        pass
    try:
        import games
        lines.append(f"- Wellness Bingo this week: {len(games.ticked())}/25 squares, {games.bingo_lines(games.ticked())} bingo(s).")
    except Exception:
        pass
    wins = storage.load_wins()[-5:]
    if wins:
        lines.append("- Recent non-scale wins: " + "; ".join(f"{w['emoji']} {w['text']}" for w in wins))
    return "\n".join(lines)


def build_context(profile: dict, checkins: dict) -> str:
    import storage  # imported here to keep this file easy to read on its own
    samsung = samsung_to_text(storage.recent_samsung(14))
    try:
        extra = journey_to_text(profile)
    except Exception:  # never let extra context break the chat
        extra = ""
    return "\n\n".join(p for p in [profile_to_text(profile), checkins_to_text(checkins), samsung, extra] if p)


# ---------- The three things the coach can do ----------

def plan_context(day: str) -> str:
    """What Tulsi needs to close the loop: how today's plan went, and how much of her plans usually happen."""
    import journey
    import storage
    lines = []
    plan = storage.load_plans().get(day)
    if plan:
        ticks = ", ".join(f"{'DONE' if i['done'] else 'not done'}: {i['text']}" for i in plan["items"])
        lines.append(f"The plan you gave me for {day}: {ticks}.")
    ft = journey.follow_through(7)
    if ft["rate"] is not None:
        lines.append(f"My plan follow-through over the last 7 days: {ft['done']} of {ft['total']} items ({ft['rate']:.0%}).")
        if ft["rate"] < 0.5:
            lines.append("That's under half, so make tomorrow's plan SMALLER and easier (tiny wins build habits).")
        elif ft["rate"] > 0.8:
            lines.append("That's great, so tomorrow's plan can be slightly more ambitious.")
    reasons = journey.scale_reasons(journey.all_days())
    if reasons and reasons["reasons"]:
        lines.append(f"My weight went up {reasons['up_by']} kg since the last weigh-in. Likely temporary reasons from my data: "
                     + " ".join(r.split(" ", 1)[1] for r in reasons["reasons"][:3])
                     + " Reassure me kindly and point me to the 7-day trend.")
    return "\n".join(lines)


def daily_feedback(profile: dict, checkins: dict, today: str) -> str:
    """Encouraging feedback on today, plus a 3-item plan for tomorrow.
    The reply ends with a machine-readable line "PLAN: a | b | c", which the app turns into a checklist."""
    loop = plan_context(today)
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "system", "content": build_context(profile, checkins) + ("\n\nPLAN FOLLOW-UP\n" + loop if loop else "")},
        {
            "role": "user",
            "content": (
                f"I just finished my check-in for {today}. Text me back like a friend on WhatsApp, "
                "in 3-4 short messages separated by ---:\n"
                "1. If there was a plan for today, start by celebrating what I DID from it (be specific). Never guilt "
                "me about what I didn't do. Otherwise, celebrate something specific about my day.\n"
                "2. How my sleep, stress and cycle might be affecting me (one or two sentences).\n"
                "3. A tiny plan for tomorrow as exactly 3 short bullets (movement, food, sleep), "
                "adjusted to my energy, sleep, stress and how well I follow plans.\n"
                "Optionally a 4th message: a short encouraging line.\n"
                "Then, on the very last line, write PLAN: followed by the same 3 actions, very short, separated by ' | ' "
                "(for example: PLAN: 20-min walk after lunch | Add dal to dinner | Phone away by 10:30 pm). "
                "The app reads this line to make my checklist."
            ),
        },
    ]
    return call_ai(messages)


def theme_words(theme: str) -> list[dict]:
    """Words and easy clues for a crossword on any theme the user types."""
    import json
    prompt = (f'Make a fun newspaper-style crossword on the theme: "{theme}".\n'
              "Give 16 single words (letters only, no spaces or hyphens), 3 to 10 letters each.\n"
              "WORDS: use words SPECIFIC to this theme (famous names, titles, places, dishes, songs, things only fans "
              "would know), not plain dictionary words. For Bollywood, think SHOLAY, DEVDAS, KAJOL, RAHMAN, LAGAAN, "
              "not ACTRESS or COMEDY. A person who loves this theme should know most of them.\n"
              "CLUES: make them interesting, like a quiz or newspaper crossword: a real fact, a famous line, a "
              "fill-in-the-blank, or playful wordplay. Never a bland dictionary definition. Example clues: "
              "'Gabbar Singh's 1975 classic', 'Kerala's festival of the harvest and the pookalam', "
              "'Mozart of Madras who won two Oscars'. Each clue under 12 words, and it must not contain the answer.\n"
              "Keep it kind and family-friendly. Only use facts you are sure are correct.\n"
              'Reply with ONLY JSON: {"words": [{"word": "SHOLAY", "clue": "Gabbar Singh\'s 1975 classic"}]}')
    raw = call_ai([{"role": "user", "content": prompt}], max_tokens=1200, temperature=0.7)
    start, end = raw.find("{"), raw.rfind("}")
    try:
        return json.loads(raw[start:end + 1]).get("words", [])
    except ValueError:
        raise CoachError("Tulsi couldn't make words for that theme. Try a different one.")


def plan_for_today(profile: dict, checkins: dict, when: str = "today") -> list[str]:
    """Three tiny steps for today or tomorrow: movement, food, rest (in that order)."""
    from datetime import date
    loop = plan_context(date.today().isoformat())
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "system", "content": build_context(profile, checkins) + ("\n\nPLAN FOLLOW-UP\n" + loop if loop else "")},
        {"role": "user", "content": (
            f"Make me a tiny plan for {when.upper()}: exactly 3 short, specific, realistic actions IN THIS ORDER: 1) movement "
            "(name real moves with sets/reps or minutes, e.g. 3 × 12 squats, 15-min warm-up), 2) food (a specific meal or swap "
            "with a portion), 3) sleep or rest, adjusted to my recent sleep, stress, cycle phase and how well I follow plans. "
            "Reply with ONLY one line in this format: PLAN: action one | action two | action three")},
    ]
    _, items = extract_plan(call_ai(messages, max_tokens=200, temperature=0.6))
    if not items:
        raise CoachError("Tulsi couldn't make a plan just now. Please try again in a minute.")
    return items


def extract_plan(reply: str) -> tuple[str, list[str]]:
    """Splits Tulsi's reply into (text to show, plan items).
    Handles "PLAN: a | b | c" on one line, "PLAN:" followed by bullet lines, and falls back to her bullets."""
    import re
    bullet = re.compile(r"^\s*(?:[-•*]|\d+[.)])\s+(.*)")
    items, kept, collecting = [], [], False
    for line in reply.strip().splitlines():
        m = re.match(r"\s*\**PLAN\**\s*:\s*(.*)", line, flags=re.I)
        if m and not items:
            rest = m.group(1).strip()
            if rest:
                items = [x.strip(" .*-") for x in rest.split("|") if x.strip(" .*-")]
            else:
                collecting = True  # the steps are on the next lines
            continue
        if collecting:
            b = bullet.match(line)
            if b:
                items.append(b.group(1).strip(" .*"))
                continue
            if line.strip():
                collecting = False
        kept.append(line)
    text = "\n".join(kept).strip()
    if not items:  # the model forgot the PLAN line: use the first bullets instead
        items = [bullet.match(l).group(1).strip() for l in kept if bullet.match(l)][:3]
    return text, items[:3]


# ---------- "Just tell Tulsi": turn your own words into a check-in ----------

QUICK_LOG_PROMPT = """You turn a person's description of their day into data for a health app.
Only fill in what they actually said or clearly implied. Use null for anything not mentioned. Never guess sleep,
steps, weight or symptoms.

Reply with ONLY valid JSON in exactly this format:
{
  "sleep_hours": number or null,
  "steps": integer or null,
  "distance_km": number or null,
  "exercise": "short description" or null,
  "exercise_minutes": integer or null,
  "foods": [{"name": "Masala dosa", "meal": "Breakfast|Lunch|Snack|Dinner", "calories": 250}],
  "water_glasses": integer or null,
  "stress": 1-5 or null,
  "energy": 1-5 or null,
  "mood": one of ["😊 Good", "🙂 Okay", "😐 Meh", "😔 Low", "😣 Frustrated"] or null,
  "weight_kg": number or null,
  "period_started": true or false,
  "symptoms": {"acne": 0-3, "hair_fall": 0-3, "bloating": 0-3, "cramps": 0-3, "cravings": 0-3, "fatigue": 0-3, "low_mood": 0-3},
  "notes": "anything else worth remembering, one short sentence" or null
}
Rules:
- foods: estimate calories for a typical Indian home portion of what they named (e.g. 2 chapatis = 2 items or one item
  "2 chapatis"). If the meal isn't said, guess from the time words (morning = Breakfast, etc.), else Snack.
- symptoms: include ONLY symptoms they mentioned (0 none, 1 mild, 2 moderate, 3 strong). Empty object if none.
- stress/energy: map words like "very stressed" = 5, "a bit stressed" = 3, "exhausted" = 1, "full of energy" = 5.
- "tired" alone means energy 2. A walk of "half an hour" = 30 minutes.
"""


def parse_day(text: str) -> dict:
    """Ask the AI to turn free text into check-in fields. Returns a cleaned dict."""
    import json
    raw = call_ai([{"role": "system", "content": QUICK_LOG_PROMPT}, {"role": "user", "content": text}],
                  max_tokens=900, temperature=0.1)
    raw = raw.strip().strip("`")
    start, end = raw.find("{"), raw.rfind("}")
    if start < 0 or end < 0:
        raise CoachError("Tulsi couldn't understand that. Try saying it a little differently.")
    try:
        data = json.loads(raw[start:end + 1])
    except ValueError:
        raise CoachError("Tulsi couldn't understand that. Try saying it a little differently.")

    def num(key, kind=float, lo=0, hi=10 ** 6):
        try:
            v = kind(data.get(key))
            return v if lo <= v <= hi else None
        except (TypeError, ValueError):
            return None

    moods = ["😊 Good", "🙂 Okay", "😐 Meh", "😔 Low", "😣 Frustrated"]
    foods = []
    for f in data.get("foods") or []:
        if isinstance(f, dict) and f.get("name"):
            meal = f.get("meal") if f.get("meal") in ("Breakfast", "Lunch", "Snack", "Dinner") else "Snack"
            try:
                kcal = max(0, min(3000, int(float(f.get("calories") or 0))))
            except (TypeError, ValueError):
                kcal = 0
            foods.append({"name": str(f["name"])[:60], "meal": meal, "calories": kcal})
    symptoms = {}
    for k, v in (data.get("symptoms") or {}).items():
        try:
            if k in ("acne", "hair_fall", "bloating", "cramps", "cravings", "fatigue", "low_mood"):
                symptoms[k] = max(0, min(3, int(v)))
        except (TypeError, ValueError):
            pass
    return {
        "sleep_hours": num("sleep_hours", float, 0, 16), "steps": num("steps", int, 0, 100000),
        "distance_km": num("distance_km", float, 0, 100), "exercise": (data.get("exercise") or None),
        "exercise_minutes": num("exercise_minutes", int, 0, 600), "foods": foods,
        "water_glasses": num("water_glasses", int, 0, 30), "stress": num("stress", int, 1, 5),
        "energy": num("energy", int, 1, 5), "mood": data.get("mood") if data.get("mood") in moods else None,
        "weight_kg": num("weight_kg", float, 25, 300), "period_started": bool(data.get("period_started")),
        "symptoms": symptoms, "notes": (data.get("notes") or None),
    }


# ---------- Ready-made requests behind the quick-action buttons ----------
# The button text is shown in the chat; the detailed request below is what Tulsi actually receives.

PLAN_RULES = (" For this request you may send up to 9 messages (still separated by ---), "
              "one message per day or section, each with short bullet points. "
              "Use my health profile (conditions, diet preferences, allergies, calorie target).")

QUICK_ACTIONS = {
    "🥗 Weekly meal plan": (
        "Make me a simple 7-day meal plan for a busy working person. One message per day with "
        "Breakfast, Lunch (lunchbox-friendly), Snack and Dinner, plus rough calories per meal. "
        "Use easy Indian / Kerala home-style food that takes 20 minutes or less, or can be prepped the "
        "night before. Make it PCOS-friendly: protein and fibre in every meal, more whole grains and "
        "vegetables, fewer refined carbs and sugar. Repeat some meals to make cooking easier. "
        "End with a short message of 3 batch-cooking tips for the weekend." + PLAN_RULES
    ),
    "🍱 Quick lunchbox ideas": (
        "Give me 6 quick lunchbox ideas I can make in 15 minutes before work, Indian / Kerala style and "
        "PCOS-friendly (protein + fibre). For each: the dish, a one-line how-to and rough calories." + PLAN_RULES
    ),
    "🏠 Home workout plan": (
        "Make me a 5-day weekly home workout plan with no equipment and no gym, low-impact and "
        "PCOS-friendly (mix of walking, bodyweight strength, yoga and stretching), 20-30 minutes a day. "
        "One message per day with a warm-up, 4-5 exercises with reps or time, and a cool-down. "
        "Adjust the intensity to my recent sleep, stress and energy, and keep it apartment-friendly "
        "(quiet, small space)." + PLAN_RULES
    ),
    "🔥 Today's workout": (
        "Give me a home workout for today with no equipment, adjusted to my cycle phase, sleep, stress and energy. "
        "List each exercise with time or reps and roughly how many calories the whole workout burns for my weight. "
        "Keep it achievable and kind." + PLAN_RULES
    ),
    "⏱️ 10-min home workout": (
        "Give me a 10-minute, no-equipment home workout I can do right now, adjusted to my energy and "
        "stress today. Short list of exercises with time for each, plus one motivating line."
    ),
    "😔 I'm feeling unmotivated": "I'm feeling unmotivated today. Can you help me?",
    "😴 Tips for better sleep": (
        "Give me practical tips to sleep better on workdays, keeping cortisol and PCOS in mind."
    ),
    "📬 My weekly report": (
        "Give me my weekly report for the last 7 days, like a friendly recap. Message 1: my wins this "
        "week (be specific: walks, km, sleep, check-ins, food scans, water, badges, non-scale wins). "
        "Message 2: one or two patterns you noticed (e.g. sleep vs energy, or cycle phase). "
        "Message 3: ONE small, realistic goal for next week. Message 4: a warm closing line." + PLAN_RULES
    ),
    "🛒 Grocery list": "",  # filled in by grocery_request() with the latest meal plan
    "🆘 Craving SOS": "",   # filled in by craving_request()
    "🌡️ Explain my symptoms": (
        "Look at the PCOS symptoms I've logged and any patterns noticed. In 3-4 short messages: what you notice "
        "(only from my data, don't invent patterns), 2 practical things to try this week, and when it would be "
        "worth talking to my doctor. Be gentle."
    ),
}

CRAVINGS = ["🍫 Something sweet", "🍟 Fried or salty", "🍚 Rice or carbs", "🥤 A cold drink", "😩 I'm just stressed or bored"]


def craving_request(kind: str = "", note: str = "") -> str:
    what = kind or "something"
    extra = f" Details: {note}." if note else ""
    return (f"Craving SOS! I'm craving {what} right now.{extra} Help me kindly in 3 short messages: "
            "1) a quick healthier swap I can make at home or buy nearby (Indian options), "
            "2) a 2-minute distraction I can do right now, "
            "3) a reminder that it's completely okay if I still eat it, and how to enjoy it mindfully. "
            "If the craving might be linked to my cycle phase, sleep or stress, mention it gently.")


def grocery_request(history: list[dict]) -> str:
    """Build the grocery-list request from the most recent meal plan in the chat."""
    plan_start = None
    for i in range(len(history) - 1, -1, -1):
        if history[i]["role"] == "user" and history[i]["content"] == "🥗 Weekly meal plan":
            plan_start = i
            break
    if plan_start is None:
        return ("I'd like a grocery list, but I haven't asked for a meal plan yet. Tell me to tap "
                "'🥗 Weekly meal plan' first, in a short friendly message.")
    plan = []
    for m in history[plan_start + 1:]:
        if m["role"] == "user":
            break
        plan.append(m["content"])
    return ("Turn this meal plan into a grocery list for the week, for one person. Group it into "
            "messages: 🥬 Vegetables & fruit, 🥚 Protein (dal, eggs, fish, paneer...), 🌾 Grains & millets, "
            "🥛 Dairy, 🧂 Pantry & spices. Give rough quantities. End with one money-saving tip."
            + PLAN_RULES + "\n\nMEAL PLAN:\n" + "\n".join(plan))


def transcribe(audio_bytes: bytes, mime: str = "audio/wav") -> str:
    """Turn a voice message into text using Gemini (free tier)."""
    import base64
    if not _has_key("GEMINI_API_KEY"):
        raise CoachError("Voice needs your Gemini key in the .env file.")
    body = {
        "contents": [{"parts": [
            {"text": "Transcribe this voice message exactly, in the language spoken. The speaker may use "
                     "Indian English or Malayalam words. Reply with ONLY the transcript."},
            {"inline_data": {"mime_type": mime, "data": base64.b64encode(audio_bytes).decode()}},
        ]}],
        "generationConfig": {"temperature": 0},
    }
    headers = {"x-goog-api-key": os.getenv("GEMINI_API_KEY", "").strip(), "Content-Type": "application/json"}
    last = "Couldn't understand the voice message."
    for model in _env_list("GEMINI_MODEL", "gemini-3.1-flash-lite,gemini-3.5-flash"):
        try:
            r = requests.post(f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
                              headers=headers, json=body, timeout=60)
            if r.status_code == 200:
                parts = r.json()["candidates"][0]["content"]["parts"]
                text = "".join(p.get("text", "") for p in parts if not p.get("thought")).strip()
                if text:
                    return text
            elif r.status_code == 429:
                last = "The free Gemini limit was reached. Wait a minute and try again."
        except (requests.RequestException, KeyError, IndexError, ValueError):
            continue
    raise CoachError(last)


VARIETY = {
    "🥗 Weekly meal plan": ["millets like ragi, jowar and foxtail millet", "Kerala classics made lighter",
                           "high-protein vegetarian meals", "eggs and fish", "one-pot and pressure-cooker meals",
                           "minimal-cooking meals for very busy weeks", "North and South Indian mix"],
    "🍱 Quick lunchbox ideas": ["wraps and rolls", "rice-free lunches", "leftover makeovers",
                               "salad bowls with Indian flavours", "millet-based lunches"],
    "🏠 Home workout plan": ["yoga and mobility", "bodyweight strength", "dance cardio and fun moves",
                            "walking plus core", "mat pilates-style moves"],
    "⏱️ 10-min home workout": ["gentle stretching", "standing strength", "fun cardio", "core and posture"],
}


def chat_reply(profile: dict, checkins: dict, history: list[dict]) -> str:
    """Reply in an ongoing chat. Each history message is {"role", "content"} and, for quick-action
    buttons, an "ask" field holding the detailed request (used only for the newest message)."""
    recent = history[-10:]
    convo = []
    for i, m in enumerate(recent):
        text = m["content"]
        if i == len(recent) - 1 and m.get("ask"):
            text = m["ask"]
            if m["content"] in VARIETY:
                theme = random.choice(VARIETY[m["content"]])
                text += (f" Make it clearly different from anything you suggested earlier in this chat. "
                         f"This time, give it a theme of {theme}, as long as it fits my diet preferences.")
        elif m["role"] == "assistant" and len(text) > 400:
            text = text[:400] + " ..."  # long old plans are shortened so they don't crowd out the new reply
        convo.append({"role": m["role"], "content": text})

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "system", "content": build_context(profile, checkins)},
        *convo,
    ]
    return call_ai(messages, max_tokens=3500, temperature=0.85)


def summarise_report(report_text: str) -> str:
    """Turn a medical report into a short, plain-language summary for the profile."""
    messages = [
        {
            "role": "system",
            "content": (
                "You summarise medical reports for a personal health coach app. "
                "List only the key findings relevant to diet, exercise, weight, hormones, "
                "sleep and energy (e.g. blood sugar, insulin, thyroid, vitamin D, iron, "
                "hormone levels), with values and whether they are flagged high/low. "
                "Use at most 8 short bullet points. Do not diagnose or give medical advice."
            ),
        },
        {"role": "user", "content": report_text[:12000]},
    ]
    return call_ai(messages, max_tokens=500)


def craving_swaps(food: str) -> tuple[str, list, str]:
    """Specific swaps for a craving that isn't in FitBuddy's library. Returns (group, [(emoji, swap, why)], tip)."""
    import json
    prompt = (f'I\'m craving: "{food}". I have PCOS and I\'m in Kerala, India. Give 3 SPECIFIC healthier swaps for '
              "exactly this food (with portions, easy to make at home or buy nearby), each with a short reason why it "
              "satisfies the same craving. Also give one kind tip for enjoying the real thing mindfully if I still want it. "
              "Never shame. Reply with ONLY JSON: "
              '{"group": "sweet|salty|carbs|drink|other", "swaps": [{"emoji": "🍌", "swap": "...", "why": "..."}], "tip": "..."}')
    raw = call_ai([{"role": "user", "content": prompt}], max_tokens=600, temperature=0.6)
    start, end = raw.find("{"), raw.rfind("}")
    try:
        data = json.loads(raw[start:end + 1])
        swaps = [(s.get("emoji", "🌿"), s["swap"], s.get("why", "")) for s in data["swaps"][:3]]
    except (ValueError, KeyError, TypeError):
        raise CoachError("Tulsi couldn't think of swaps just now.")
    group = {"sweet": "🍫 Something sweet", "salty": "🍟 Fried or salty", "carbs": "🍚 Rice or carbs",
             "drink": "🥤 A cold drink"}.get(str(data.get("group", "")).lower(), "🍽️ Something else")
    return group, swaps, data.get("tip", "")
