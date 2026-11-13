# 🌿 FitBuddy: meet Tulsi, your kind, judgement-free AI health coach

FitBuddy helps people lose weight and build healthy habits at home, without judgement.
It's built for people with PCOS and anyone who has faced body-shaming.

I built it from my own experience: I went from 80 kg to 63 kg in a year using AI as my coach,
and my cycle became regular again.

## Features (so far)
- **Health profile**: conditions (e.g. PCOS), medications, cycle, diet, goals and limitations.
- **Medical report upload**: the AI summarises key findings from a PDF report, and you check them before saving.
- **📸 Food photo scanning**: snap or upload a meal photo, and Gemini identifies the foods (including Kerala dishes) and estimates calories, protein, carbs, fat and fibre. You can edit the results before saving, and the total flows into your daily check-in.
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
