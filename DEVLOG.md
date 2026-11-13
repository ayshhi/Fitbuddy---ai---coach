# FitBuddy development log

This is how FitBuddy was built, step by step, including the problems I hit and how I solved them.
I built it individually, with **Claude** as my AI building partner for planning, code, design and debugging.

Most of the first version was built in one intensive day, **13 November 2026**, before my first commit.
This log records that day honestly. Later commits on GitHub show the improvements I make after testing.

---

## The idea

From November 2025 to November 2026 I went from **80 kg to 63 kg**. I have PCOS and had been on
medication since 2018. After the weight loss my cycle became regular, and I stopped the medication in February 2026.

I didn't use a gym: there wasn't a good one near me, and after past body-shaming it didn't feel safe.
What helped was using AI to ask about calories and gentle exercise, and having it stay positive when I
slipped up. I also tracked sleep, steps and distance on my Samsung phone.

**Goal:** an AI coach that does what helped me, but personalised, kind and PCOS-aware.

I first considered submitting an older project (a resume RAG app), but decided a project built from my own
experience would be more original and more meaningful.

---

## Step 1: Health profile, daily check-in and AI coach

- Built the app in **Python + Streamlit**, so I could focus on the experience and the AI.
- **Health profile:** conditions, medications, cycle, diet, allergies, goals, plus optional PDF medical
  report upload, which the AI summarises and I can edit before saving.
- **Daily check-in:** sleep, steps, distance, calories, exercise, stress, energy, mood and notes.
- **Coach system prompt** with rules I cared about:
  - always kind, never body-shaming
  - look at the whole week, and **never** say "burn it off" (no exercise as punishment)
  - cortisol-aware: poor sleep or high stress means gentle movement, not hard workouts
  - safety: not a doctor, no medication advice, never below 1200 kcal, suggest a doctor for symptoms
- **Privacy:** data saved only on my computer as JSON files, consent before saving, API keys in a
  private `.env` file kept out of GitHub with `.gitignore`.

**Problem:** I didn't know what API keys were. I learned how they work, created one on OpenRouter,
and learned to keep keys private (I replaced one after accidentally pasting it into a chat).

## Step 2: Choosing a free AI model

**Problem:** the first free model returned error 403. It was only allowed inside certain coding tools.

**Fix:** switched to a free model that works in apps (**ERNIE 5.5 Flash** via OpenRouter), and added a
**fallback list**: if one model fails, the app tries the next one automatically.

**Result:** the coach's first reply noticed my period had started from my notes, encouraged rest, and
suggested iron-rich food. That was exactly the tone I wanted.

## Step 3: Food photo scanning

- I can't afford paid AI, so I used **Google Gemini's free tier**, which can read images.
- The photo is resized, sent with instructions to identify each food (including Kerala dishes like
  matta rice, sambar and thoran), estimate portion, calories, protein, carbs, fat and fibre,
  and reply in a fixed JSON format.
- Results are **editable** before saving, because photo estimates are never perfect.
- The tip is always positive. Food is never called "bad" or "junk".
- Saved meals automatically fill in the day's calories in the check-in.

## Step 4: Samsung Health import and progress charts

- Exported my Samsung Health data (500+ files) and studied the real format: the first line is
  metadata, column names sometimes have long prefixes, times are stored in UTC with a separate offset,
  and distance is in metres.
- Wrote an importer that accepts the CSV files or the whole export as a zip, and picks out steps,
  walking sessions, sleep and weight.
- My data showed **595 walking sessions since 2023**, and **134 walks covering about 195 km in the past year**.
- **Learning:** phone step counts were low because the phone only counts steps while I carry it.
  Walking sessions show my real effort, so the dashboard focuses on them.
- I had no sleep or weight files, so I added **manual weight history entry**. My real journey line
  comes from weights I actually recorded. I used sample files only for testing, never in the demo.
- Added separate line charts for weight, walking, distance, steps, sleep and calories.

## Step 5: Redesign, with Tulsi and WhatsApp-style chat

I didn't like the first layout, and the coach's long paragraphs felt like reading a report.

- Created **Tulsi 🌿**, a cheerful sprout character, drawn in SVG and named after the tulsi plant (healing and care).
- Rebuilt the chat to look like WhatsApp: header with "online / typing…", my bubbles on the right,
  hers on the left, timestamps, ticks and a typing animation.
- Changed the prompt so Tulsi replies in **2–4 short messages**, like a friend texting.
- Check-in feedback now arrives as chat bubbles too, and the chat history is saved.

## Step 6: Testing on my own screen, then fixing problems

- **Problem:** there was no box to type my own message. **Fix:** added a message bar with a Send button.
- **Problem:** on my high-resolution monitor everything was tiny and far apart.
  **Fix:** text and layout now scale with screen size.
- Switched to a **purple theme**.
- Added one-tap buttons: **weekly meal plan** (quick, PCOS-friendly Indian food for working people),
  **lunchbox ideas**, **home workout plan** (no equipment), **10-minute workout**, motivation and sleep tips.
- **Problem:** a long meal plan got cut off, and the next request failed with an empty reply.
  **Fixes:**
  - gave long plans more room for the reply
  - shortened old long messages before sending them, so new replies have space
  - added my free **Gemini key as a backup chat model**
  - made every new plan different by giving it a random theme (millets, Kerala classics, one-pot meals…)

## Step 7: Features to make it motivating and personal

- **Tulsi grows with you:** seed → sprout → young plant → leafy plant → bud → **full bloom at your goal**.
  Growth comes from goal progress plus effort (check-ins, walks, sleep, water, food scans, wins).
  The app saves her highest growth, so **she never shrinks or wilts**. Bad days just pause growth.
- **Cycle-aware coaching:** from logged period dates, the app works out cycle length and today's phase
  (period, follicular, ovulation, luteal), notices irregular cycles, and tells Tulsi to adapt her advice.
- **Voice chat:** record a message, Gemini transcribes it, and Tulsi can answer out loud (gTTS, Indian English accent).
- **18 badges** that reward effort, not just weight, with a celebration when a new one is earned.
- **Non-scale wins journal**, **weekly report**, **grocery list from the meal plan**, and a **water tracker**.

## Step 8: Making every page look good

- Purple gradient headers on every page.
- **Progress:** stat tiles, and redrawn charts with soft purple lines and hover details.
  The weight chart always shows the whole journey.
- **Food scan:** a food card for each item with coloured nutrient labels, Tulsi's tip, and a meal timeline.
- Tested every page with my real Samsung data before publishing.

## Step 9: Published on GitHub

- Checked `git status` before the first push, to make sure `.env` (keys), `data` (health data)
  and `venv` were not included.

## Step 10: More testing and more features (afternoon, 13 Nov)

- **Chat redesign:** I didn't like that the chat copied WhatsApp, so it now flows on the page with pop-in bubbles
  and a message bar that stays at the bottom. Fixed a bug where the typing bubble stayed stuck after a check-in.
- **Layout:** switched to a full-width layout and bigger text, because content only used the middle of my screen.
  Progress charts now only show when there's data, so there are no empty gaps.
- **Tulsi mascot:** she bounces in the corner, waves a leaf, and smiles with hearts when clicked.
- **Watering Tulsi:** each glass of water I log waters her (with an animation), and counts towards her growth.
- **Tulsi's Garden Path:** a snakes-and-ladders walking game without snakes, because sliding back is a punishment.
  Ladders unlock with healthy habits. Friends join with a "friend code" I share on WhatsApp, because a live
  online version would need a server and would put health data online.
- **Share card:** a progress image to share, with weight hidden by default.
- **Craving SOS, PCOS symptom tracker and doctor report PDF:** practical tools for living with PCOS.
  Symptom patterns are only reported when there are enough days on both sides to compare.

---

## What I learned

- How to design an AI's behaviour with a system prompt, and how much tone matters for health.
- How to give an AI context (profile, check-ins, cycle) on every request, since it doesn't remember.
- How to get structured JSON output from a vision model.
- How to make a demo reliable with free models: fallbacks, shorter history, friendly errors.
- How to handle real, messy data (Samsung's export format).
- Privacy basics: local storage, consent, and keeping secrets out of Git.
