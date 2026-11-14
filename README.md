# 🌿 FitBuddy: meet Tulsi, your kind, judgement-free AI health coach

FitBuddy helps people lose weight and build healthy habits at home, without judgement.
It's built for people with PCOS and anyone who has faced body-shaming.

I built it from my own experience: I went from 80 kg to 63 kg in a year using AI as my coach,
and my cycle became regular again.

## Features (so far)
- **Health profile**: conditions (e.g. PCOS), medications, cycle, diet, goals and limitations.
- **Medical report upload**: the AI summarises key findings from a PDF report, and you check them before saving.
- **📸 Food photo scanning** (with servings eaten and a check that calories match protein/carbs/fat): snap or upload a meal photo, and Gemini identifies the foods (including Kerala dishes) and estimates calories, protein, carbs, fat and fibre. You can edit the results before saving, and the total flows into your daily check-in.
- **📊 Samsung Health import + progress dashboard**: upload your Samsung Health export (CSV files or a .zip). Your steps, distance, walks, sleep and weight then fill in daily check-ins automatically and show as weekly or monthly charts.
- **Daily check-in**: sleep, steps, distance (from Samsung Health), calories, exercise, stress, energy and mood.
- **AI coach feedback**: an encouraging look at your day and week, plus a plan for tomorrow
  that adjusts to sleep and stress (cortisol-aware).
- **Chat with Tulsi 🌿**: a cheerful sprout character who texts like a friend, with WhatsApp-style bubbles, a message bar and saved chat history. One-tap buttons give a 7-day PCOS-friendly meal plan for busy workers, quick lunchbox ideas, a 5-day no-equipment home workout plan, a 10-minute workout, and help with motivation and sleep. Daily check-in feedback arrives as chat messages too.

- **🌸 Tulsi grows with you**: Tulsi grows in her pot from seed → sprout → young plant → leafy plant → bud → **full bloom when you reach your goal**. She grows from goal progress *and* effort (check-ins, walks, sleep, water, food scans, wins), and she **never shrinks or wilts**: bad days just pause growth.
- **🌙 Cycle-aware coaching**: log period start dates, and Tulsi tailors food and exercise tips to your cycle phase (period, follicular, ovulation, luteal). It handles irregular PCOS cycles too.
- **🎙️ Voice chat**: speak to Tulsi (transcribed with Gemini), and she can reply out loud (gTTS, Indian English).
- **🏅 18 gentle badges** that reward effort, not just weight, with a celebration when you earn one.
- **💜 Non-scale wins journal**: "my jeans fit again", "more energy"...
- **📬 Weekly report**, **🛒 grocery list from your meal plan**, and a **💧 water tracker**.

- **💧 Water Tulsi**: every glass you drink waters Tulsi, with a watering-can animation. After 8 glasses her leaves sparkle with dewdrops.
- **🎯 Wellness Bingo (weekly, with friends)**: everyone gets the same 5×5 card each week. The card shows big numbers; tap one and its real-life self-care task pops up (sunlight, a short walk, calling someone you love, an early night) with "I did it!". Some squares tick themselves from your data. Get a bingo and share it on WhatsApp.
- **🧩 Tulsi's Crosswords**: newspaper-style crosswords with 9–10 crossing words and easy clues. Play **today's crossword** (the same for everyone), **pick a theme** (Kerala food, fruits & veggies, exercise, mind & feelings, herbs & spices, body & PCOS, sleep & rest), or **type your own theme** and Tulsi writes the words and clues. Every puzzle is generated automatically, and I tested hundreds to make sure there are no clashing letters or stray words.
- **📤 Share card**: a downloadable progress image for WhatsApp or Instagram. You choose what's shown, and weight is hidden by default.
- **🌈 Home page**: Tulsi bouncing under an animated rainbow, with today's status and a "Let's start" button.
- **🆘 Craving SOS page**: log the craving, how strong it is and what's behind it, then breathe with Tulsi. You get instant Indian swap ideas (no AI needed), can talk it through with Tulsi, and see your patterns by time of day, trigger and cycle phase.
- **🌡️ Symptoms page**: log 7 PCOS symptoms, see a 30-day grid and averages by cycle phase. Patterns with sleep, stress, cycle phase and water are checked with a permutation test plus a correction for testing many things at once (Benjamini–Hochberg), so chance findings aren't shown as real.
- **🩺 Doctor report**: a one-page PDF summary of weight, cycle, sleep, activity and symptoms for appointments.
- **🌿 Tulsi mascot**: bounces in the corner, waves, and smiles with floating hearts when you click her.

- **🔥 Exercise: specific home workouts**: 6 ready-made workouts with exact sets and reps, like the **🔥 15-min fat-burn
  warm-up** (jumping jacks 2 × 45 sec, high knees, squat jumps 3 × 10, mountain climbers 3 × 30 sec, 3 min skipping rope…),
  lower-body strength, core & plank, HIIT, full-body beginner and a period-friendly gentle session. Every move shows how to do it
  and the **estimated calories for your weight** (MET × weight × time, including rests). Tick the moves you did, or log a single
  move like "Plank: 3 × 60 sec". Tulsi suggests the right workout for today from your cycle phase, sleep, stress and energy.
  A **sun gets brighter** as you approach your daily burn goal, with a weekly chart. Samsung Health walks are included automatically.
- **🥗 Food & diet: a real daily meal plan**: a calorie target worked out from your height, weight and age (Mifflin-St Jeor,
  a gentle 400 kcal deficit, never below 1,200) and a protein goal (1.2 g per kg). Then 4 specific, PCOS-friendly Kerala and
  Indian meals with portions, calories and protein, for vegetarian, eggs + veg or non-veg. **🔀 Swap** any meal and tap
  **✅ I ate this** to log it. Food photo scanning is on the same page.

### Built for real daily use
- **💬 Just tell Tulsi**: describe your day in your own words (typed or spoken), like *"slept 6 hours, walked 30 min, dosa for
  breakfast, bit stressed"*. Tulsi fills in your check-in, meals, water and symptoms. You confirm with one tap. Logging takes 10 seconds.
- **📋 Plans that close the loop**: Tulsi's 3 steps for tomorrow become a checklist. The next evening she celebrates what you
  did, never guilts you about what you didn't, and makes plans **smaller when you're struggling and bigger when you're
  flying**, based on your real follow-through.
- **⏰ Phone reminders**: download a calendar file, and your phone reminds you every day (plan, water, check-in, wind-down),
  even when the app is closed. No server needed.
- **⚖️ A calmer weight view**: a bold 7-day average line instead of daily jumps. When the scale goes up, FitBuddy explains
  likely temporary reasons from your own data (cycle phase, short sleep, stress, a bigger meal, a long workout).

## Responsible AI design
- Looks at the whole week. It never tells you to "burn off" food with exercise.
- Suggests gentle movement on low-sleep or high-stress days.
- Never suggests eating under 1200 kcal per day or extreme diets, and never advises on medication.
- Health data stays on your computer, and you're asked for consent before it's saved.

## Tech
Python · Streamlit · OpenRouter API (coach) · Google Gemini API (food vision) · pypdf · Pillow

If one AI model is busy or unavailable, the app automatically tries a backup model.

## Run it (Windows)
```
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
notepad .env          (paste your OpenRouter and Gemini keys, then save)
streamlit run app.py
```
