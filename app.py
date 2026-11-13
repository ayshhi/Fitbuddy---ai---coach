"""
app.py - the FitBuddy app you see in the browser (built with Streamlit).

Run it with:   streamlit run app.py
"""

from datetime import date

import streamlit as st
from pypdf import PdfReader

import pandas as pd

import coach
import food
import garden
import journey
import samsung
import storage
import ui

st.set_page_config(page_title="FitBuddy - AI Health Coach", page_icon="🌿", layout="centered")
ui.inject_css()
ui.inject_card_css()
ui.inject_page_css()


def show_error(err: Exception) -> None:
    st.error(f"😕 {err}")


# ---------------- Sidebar navigation ----------------

ui.sidebar_brand()
page = st.sidebar.radio(
    "Go to", ["🏠 Today", "💬 Chat with Tulsi", "🌸 My garden", "📸 Food scan", "📊 Progress", "🩺 Health profile"],
    label_visibility="collapsed",
)
st.sidebar.divider()
st.sidebar.caption(
    "FitBuddy gives general wellness support, not medical advice. "
    "Always talk to your doctor about medical questions."
)

profile = storage.load_profile()

# Tulsi in the sidebar, and a celebration whenever a new badge is earned
_rows = journey.all_days()
_growth = journey.growth(profile, _rows)
st.sidebar.markdown(garden.tulsi_img(_growth["stage"], "7rem"), unsafe_allow_html=True)
st.sidebar.caption(f"{_growth['emoji']} Tulsi is a **{_growth['name'].lower()}**")
_earned = [b for b in journey.badges(profile, _rows) if b["earned"]]
_first_time = storage.load_seen_badges() is None
_seen = set(storage.load_seen_badges() or [])
_new = [b for b in _earned if b["name"] not in _seen]
if _new or _first_time:
    if not _first_time:  # the very first time, quietly record existing badges instead of celebrating
        st.balloons()
        for b in _new:
            st.toast(f"New badge: {b['emoji']} {b['name']}!", icon="🏅")
    storage.save_seen_badges([b["name"] for b in _earned])


# ---------------- Page 1: Today's check-in ----------------

if page == "🏠 Today":
    name = profile.get("name") or "there"
    ui.hero("👋", f"Hi {name}!", date.today().strftime("%A, %d %B") + " · Let's check in on today")
    st.markdown(ui.chat_window(
        [{"role": "assistant", "content": f"Hey {name}! 🌿 How was your day? Tell me below and "
          "I'll help you plan a lovely tomorrow 💜", "time": ui.now_time()}],
        ), unsafe_allow_html=True)
    st.write("")

    today_str = date.today().isoformat()
    left, right = st.columns([1, 2])
    with left:
        st.markdown(garden.tulsi_img(_growth["stage"], "9rem"), unsafe_allow_html=True)
        st.markdown(f"<div style='text-align:center'><b>{_growth['emoji']} {_growth['name']}</b></div>",
                    unsafe_allow_html=True)
    with right:
        cyc = journey.cycle_info()
        if cyc:
            note = " Your cycle looks irregular, so this is a rough guess." if cyc["irregular"] else ""
            st.markdown(ui.card(f"{cyc['emoji']} Cycle day {cyc['day']} · {cyc['phase']} phase",
                                cyc["tip"] + note), unsafe_allow_html=True)
        else:
            st.markdown(ui.card("🌙 Cycle-aware tips", "Tick <b>My period started today</b> in your check-in "
                                "(or add dates in 🩺 Health profile) and Tulsi will tailor advice to your cycle."),
                        unsafe_allow_html=True)
        glasses = storage.water_today(today_str)
        st.markdown(ui.card(f"💧 Water today: {glasses} / 8 glasses",
                            f"<span class='water'>{'💧' * min(glasses, 8)}{'🤍' * max(0, 8 - glasses)}</span>"),
                    unsafe_allow_html=True)
        w1, w2, _ = st.columns([1, 1, 2])
        if w1.button("➕ Glass", key="water_add"):
            storage.set_water(today_str, glasses + 1)
            st.rerun()
        if w2.button("➖", key="water_remove"):
            storage.set_water(today_str, glasses - 1)
            st.rerun()

    if not profile:
        st.info("Tip: fill in your **🩺 Health profile** first so your coach can personalise advice.")

    day = st.date_input("Date", value=date.today(), max_value=date.today()).isoformat()
    existing = storage.load_checkins().get(day, {})
    sh = storage.load_samsung().get(day, {})  # imported Samsung Health data for this day

    def prefill(key, sh_key, default):
        """Use the saved check-in value, else the Samsung value, else a default."""
        return existing.get(key, sh.get(sh_key, default))

    with st.form("checkin"):
        st.subheader("😴 Sleep & activity")
        st.caption("✅ Filled in from Samsung Health" if sh else
                   "Copy these from Samsung Health, or import your data on 📊 Progress.")
        c1, c2, c3 = st.columns(3)
        sleep_hours = c1.number_input("Sleep (hours)", 0.0, 16.0, float(prefill("sleep_hours", "sleep_hours", 7.0)), 0.5)
        steps = c2.number_input("Steps", 0, 100000, int(prefill("steps", "steps", 0)), 500)
        distance_km = c3.number_input("Distance (km)", 0.0, 100.0, float(prefill("distance_km", "distance_km", 0.0)), 0.1)

        st.subheader("🍽️ Food & exercise")
        scanned = storage.day_calories(day)
        if scanned:
            st.caption(f"📸 From your food scans: **{scanned} kcal** ({storage.day_foods(day)})")
        calories = st.number_input(
            "Calories eaten today (approx.)", 0, 10000, scanned or int(existing.get("calories", 0)), 50,
            help="Filled in automatically from 📸 Food scan. You can also type an estimate.",
        )
        c4, c5 = st.columns([2, 1])
        default_ex = f"Walk ({sh['workout_km']} km)" if sh.get("workout_min") else ""
        exercise = c4.text_input("Exercise done", existing.get("exercise", default_ex), placeholder="e.g. 30 min walk, yoga")
        exercise_minutes = c5.number_input("Minutes", 0, 600, int(prefill("exercise_minutes", "workout_min", 0)), 5)
        weight_kg = st.number_input(
            "Weight (kg, optional)", 0.0, 300.0, float(prefill("weight_kg", "weight_kg", 0.0)), 0.1,
            help="Optional. Once a week is plenty. Daily weight goes up and down with water, periods and salt.",
        )

        st.subheader("💭 How you feel")
        c6, c7 = st.columns(2)
        stress = c6.slider("Stress (1 = calm, 5 = very stressed)", 1, 5, int(existing.get("stress", 2)))
        energy = c7.slider("Energy (1 = exhausted, 5 = great)", 1, 5, int(existing.get("energy", 3)))
        moods = ["😊 Good", "🙂 Okay", "😐 Meh", "😔 Low", "😣 Frustrated"]
        mood = st.radio("Mood", moods, index=moods.index(existing["mood"]) if existing.get("mood") in moods else 1, horizontal=True)
        notes = st.text_area("Anything else? (cravings, period, how you're feeling...)", existing.get("notes", ""))
        period_started = st.checkbox("🩸 My period started today", value=day in storage.load_periods())

        submitted = st.form_submit_button("Save & get my coach's feedback ✨", type="primary")

    if submitted:
        if period_started:
            storage.add_period(day)
        storage.save_checkin(day, {
            "sleep_hours": sleep_hours, "steps": steps, "distance_km": distance_km,
            "calories": calories, "exercise": exercise, "exercise_minutes": exercise_minutes,
            "stress": stress, "energy": energy, "mood": mood, "notes": notes,
            "foods": storage.day_foods(day), "weight_kg": weight_kg or None,
        })
        st.success("Check-in saved! 🎉")

        # Gentle, rule-based heads-up shown before the AI reply
        if sleep_hours < 6 or stress >= 4:
            st.warning(
                "🧘 Low sleep or high stress can raise cortisol, which makes your body hold on "
                "to weight. Tomorrow is a day for gentle movement and rest, not pushing hard."
            )

        summary = (f"📋 My check-in for {day}\n"
                   f"😴 {sleep_hours:g}h sleep · 👟 {steps:,} steps · 📍 {distance_km:g} km\n"
                   f"🍽️ {calories or '–'} kcal · 🏃‍♀️ {exercise or 'no exercise'}"
                   f"{f' ({exercise_minutes} min)' if exercise_minutes else ''}\n"
                   f"Stress {stress}/5 · Energy {energy}/5 · {mood}"
                   f"{chr(10) + '📝 ' + notes if notes else ''}")
        me = {"role": "user", "content": summary, "time": ui.now_time()}
        box = st.empty()
        box.markdown(ui.chat_window([me], typing=True, pop_from=0), unsafe_allow_html=True)
        try:
            feedback = coach.daily_feedback(profile, storage.recent_checkins(7), day)
            box.empty()  # replaced by the full conversation below
            st.session_state.feedback = [me] + ui.coach_bubbles(feedback)
            st.session_state.feedback_new = True
            storage.save_chat(storage.load_chat() + st.session_state.feedback)  # also appears in the chat
        except coach.CoachError as err:
            box.empty()
            show_error(err)

    if st.session_state.get("feedback"):
        pop = 1 if st.session_state.pop("feedback_new", False) else None
        st.markdown(ui.chat_window(st.session_state.feedback, pop_from=pop), unsafe_allow_html=True)
        st.caption("💬 Want to talk more? Continue in **Chat with Tulsi**.")

    # This week's summary
    week = storage.recent_checkins(7)
    if week:
        st.divider()
        st.subheader("📅 Your week")
        avg = lambda k: sum(float(c.get(k, 0) or 0) for c in week.values()) / len(week)
        m1, m2, m3 = st.columns(3)
        m1.metric("Avg sleep", f"{avg('sleep_hours'):.1f} h")
        m2.metric("Avg steps", f"{avg('steps'):,.0f}")
        m3.metric("Days checked in", f"{len(week)} / 7")


# ---------------- Page: Food scan ----------------

elif page == "📸 Food scan":
    ui.hero("📸", "Food scan", "Snap your meal and Tulsi will estimate what's on your plate. No judgement, just info 💜")

    c1, c2 = st.columns([1, 2])
    day = c1.date_input("Date", value=date.today(), max_value=date.today()).isoformat()
    meal_name = c2.radio("Meal", ["Breakfast", "Lunch", "Snack", "Dinner"], horizontal=True)

    left, right = st.columns([3, 2])
    with left:
        source = st.radio("Photo", ["📁 Upload a photo", "📷 Use camera"], horizontal=True, label_visibility="collapsed")
        photo = (st.file_uploader("Upload a meal photo", type=["jpg", "jpeg", "png", "webp"])
                 if source.startswith("📁") else st.camera_input("Take a photo of your meal"))
        note = st.text_input("Add a note for better accuracy (optional)",
                             placeholder="e.g. 2 chapatis, half cup dal, cooked in 1 tsp oil")
        if photo and st.button("🔍 Scan my meal", type="primary"):
            with st.spinner("Tulsi is looking at your food..."):
                try:
                    st.session_state.scan = food.scan_meal(photo.getvalue(), note)
                except food.CoachError as err:
                    show_error(err)
    with right:
        if photo:
            st.image(photo)
        else:
            st.markdown(ui.card("🍛 Your meal photo will appear here",
                                "Tip: take the photo from above in good light, with the whole plate visible."),
                        unsafe_allow_html=True)

    scan = st.session_state.get("scan")
    if scan:
        if not scan["items"]:
            st.warning(scan["tip"] or "I couldn't find any food in this photo.")
        else:
            st.markdown('<div class="section-label">What Tulsi found</div>', unsafe_allow_html=True)
            summary = st.empty()   # filled in below, so it shows your corrections
            cards = st.empty()
            with st.expander("✏️ Something wrong? Fix the food, portion or calories here"):
                edited = st.data_editor(
                    scan["items"], num_rows="dynamic", key="scan_editor",
                    column_config={
                        "name": "Food", "portion": "Portion", "calories": "Calories",
                        "protein_g": "Protein (g)", "carbs_g": "Carbs (g)",
                        "fat_g": "Fat (g)", "fibre_g": "Fibre (g)",
                    },
                )
            total = sum(int(float(i.get("calories") or 0)) for i in edited)
            sums = {k: sum(float(i.get(k) or 0) for i in edited) for k in ("protein_g", "carbs_g", "fibre_g")}
            summary.markdown(ui.tiles([
                ("🔥 CALORIES", f"{total}", "kcal (estimate)"),
                ("💪 PROTEIN", f"{sums['protein_g']:.0f} g", "keeps you full"),
                ("🌾 CARBS", f"{sums['carbs_g']:.0f} g", "energy"),
                ("🥦 FIBRE", f"{sums['fibre_g']:.0f} g", "great for PCOS"),
            ]), unsafe_allow_html=True)
            cards.markdown(ui.food_cards(edited), unsafe_allow_html=True)
            if scan.get("tip"):
                st.markdown(f'<div class="tip">💡 <b>Tulsi\'s tip:</b> {ui.html.escape(scan["tip"])}</div>',
                            unsafe_allow_html=True)
            st.caption(f"Estimates from a photo (confidence: {scan['confidence']}). They're a guide, not exact numbers.")
            if st.button(f"✅ Save to {meal_name}", type="primary"):
                storage.add_meal(day, {"meal": meal_name, "items": edited, "calories": total})
                del st.session_state.scan
                st.toast(f"Saved to {meal_name}! 🌱")
                st.rerun()

    # The day's meals
    meals = storage.load_meals(day)
    st.markdown(f'<div class="section-label">Meals on {date.fromisoformat(day).strftime("%d %b")}</div>',
                unsafe_allow_html=True)
    if not meals:
        st.caption("No meals saved for this day yet. Scan your first one above! 📸")
    else:
        total_day = storage.day_calories(day)
        target = int(profile.get("calorie_target") or 0)
        st.markdown(ui.tiles([("🍽️ TODAY'S TOTAL", f"{total_day} kcal",
                               f"of your {target} kcal target" if target else f"{len(meals)} meal(s) logged")]),
                    unsafe_allow_html=True)
        if target:
            st.markdown(ui.growbar(total_day / target * 100), unsafe_allow_html=True)
        for i, m in enumerate(meals):
            c1, c2 = st.columns([8, 1])
            c1.markdown(ui.meal_row(m), unsafe_allow_html=True)
            if c2.button("✕", key=f"del{i}", help="Remove this meal"):
                storage.delete_meal(day, i)
                st.rerun()
        st.caption("One day never defines your progress. Tulsi looks at the whole week. 💜")


# ---------------- Page: Progress (Samsung Health import + dashboard) ----------------

elif page == "📊 Progress":
    ui.hero("📊", "Your progress", "Every walk, every good night's sleep, every kilo. It all adds up 💜")

    rows = journey.all_days()  # Samsung + check-ins + weights + water, one row per day

    if not rows:
        st.info("Import your Samsung Health data or add your weight history below, or do a few "
                "check-ins, to see your progress here.")
    else:
        df = pd.DataFrame.from_dict(rows, orient="index")
        df.index = pd.to_datetime(df.index)
        df = df.sort_index()
        all_weights = pd.to_numeric(df["weight_kg"], errors="coerce").dropna() if "weight_kg" in df else pd.Series(dtype=float)

        period = st.radio("Show", ["Last 30 days", "Last 3 months", "Last year", "All time"], index=2,
                          horizontal=True, label_visibility="collapsed")
        days = {"Last 30 days": 30, "Last 3 months": 91, "Last year": 365, "All time": 100000}[period]
        df = df[df.index >= pd.Timestamp.today().normalize() - pd.Timedelta(days=days)]
        group = "W" if days <= 91 else "ME"  # weekly points for short periods, monthly for long ones
        label = "week" if group == "W" else "month"

        def col(name):
            return pd.to_numeric(df[name], errors="coerce").dropna() if name in df else pd.Series(dtype=float)

        # Headline tiles
        weight, sleep = all_weights, col("sleep_hours")  # weight always shows the whole journey
        items = [("🚶‍♀️ WALKS", f"{col('workouts').sum():.0f}", f"in the {period.lower()}"),
                 ("📍 DISTANCE", f"{col('workout_km').sum():.0f} km", "walked")]
        if len(weight) >= 2:
            items.append(("⚖️ JOURNEY", f"{weight.iloc[-1] - weight.iloc[0]:+.1f} kg",
                          f"{weight.iloc[0]:g} → {weight.iloc[-1]:g} kg since {weight.index[0].strftime('%b %Y')}"))
        if not sleep.empty:
            items.append(("😴 SLEEP", f"{sleep.mean():.1f} h", "average per night"))
        st.markdown(ui.tiles(items), unsafe_allow_html=True)

        def chart(name, title, unit, how="mean", per_period=True, decimals=0, where=st, data=None):
            data = col(name) if data is None else data
            if data.empty:
                return
            if per_period:
                data = getattr(data.resample(group), how)().dropna()
                sub = f"{'Total' if how == 'sum' else 'Average'} per {label} · hover a dot for details"
            else:
                sub = "Your whole journey · hover a dot for details"
            points = list(zip(data.index.to_pydatetime(), data.values))
            body = ui.line_chart_svg(points, unit, decimals, wide=where is st)
            if len(points) < 2:
                body += '<div class="st">Not enough data yet for a line. Keep logging! 🌱</div>'
            where.markdown(ui.chart_card(title, sub, body), unsafe_allow_html=True)

        chart("weight_kg", "⚖️ Weight", "kg", per_period=False, decimals=1, data=all_weights)
        a, b = st.columns(2)
        chart("workout_min", "🚶‍♀️ Walking minutes", "min", how="sum", where=a)
        chart("workout_km", "📍 Distance walked", "km", how="sum", decimals=1, where=b)
        a, b = st.columns(2)
        chart("steps", "👟 Daily steps", "steps", where=a)
        chart("sleep_hours", "😴 Sleep", "h", decimals=1, where=b)
        a, b = st.columns(2)
        chart("calories", "🍽️ Calories eaten", "kcal", where=a)
        chart("water", "💧 Water", "glasses", decimals=1, where=b)

        st.caption("Steps only count while your phone is with you, so walking sessions show your effort best. "
                   "Quieter weeks are part of the journey too. 💜")
        with st.expander("📋 See the data as a table"):
            st.dataframe(df.sort_index(ascending=False))

    # ----- Adding data -----
    st.markdown('<div class="section-label">Add your data</div>', unsafe_allow_html=True)
    with st.expander("📥 Import Samsung Health data", expanded=not storage.load_samsung()):
        st.markdown(
            "1. In Samsung Health: **⋮ → Settings → Download personal data**.\n"
            "2. On your phone, open **My Files → Downloads → Samsung Health** and copy the newest folder to your computer.\n"
            "3. Upload the **whole folder as a .zip** (right-click the folder → *Compress to ZIP file*), "
            "or just the CSV files with **step_daily_trend**, **exercise**, **sleep** and **weight** in their names."
        )
        uploads = st.file_uploader("Samsung Health files", type=["csv", "zip"], accept_multiple_files=True)
        if uploads and st.button("Import", type="primary"):
            with st.spinner("Reading your Samsung Health data..."):
                daily, imported, problems = samsung.import_export(uploads)
            if daily:
                storage.save_samsung(daily)
                st.success(f"Imported {', '.join(imported)} for {len(daily)} days! 🎉")
            for msg in problems:
                st.caption(f"ℹ️ {msg}")
        if storage.load_samsung() and st.button("🗑️ Remove imported Samsung data"):
            storage.clear_samsung()
            st.success("Imported Samsung data removed. Your check-ins and weight history are kept.")
            st.rerun()

    with st.expander("⚖️ Add your weight history"):
        st.caption("Add any weights you remember, e.g. your starting weight and a few points along the way. "
                   "Even 3–4 real points make a clear journey line.")
        with st.form("weight", clear_on_submit=True):
            c1, c2, c3 = st.columns([2, 2, 1])
            w_day = c1.date_input("Date", value=date.today(), max_value=date.today())
            w_kg = c2.number_input("Weight (kg)", 20.0, 300.0, 60.0, 0.1)
            c3.write("")
            if c3.form_submit_button("Add"):
                storage.add_weight(w_day.isoformat(), w_kg)
                st.rerun()
        for d, kg in storage.load_weights().items():
            c1, c2 = st.columns([4, 1])
            c1.write(f"{d}: **{kg} kg**")
            if c2.button("Remove", key=f"w{d}"):
                storage.delete_weight(d)
                st.rerun()

# ---------------- Page: My garden (Tulsi grows, badges, wins) ----------------

elif page == "🌸 My garden":
    ui.hero("🌸", "My garden", "Tulsi grows with every step you take, and she never shrinks 💜")
    g = _growth
    left, right = st.columns([1, 1])
    with left:
        st.markdown(garden.tulsi_img(g["stage"], "16rem"), unsafe_allow_html=True)
    with right:
        st.markdown(f"### {g['emoji']} {g['name']}")
        st.write(g["message"])
        st.markdown(ui.growbar(g["value"]), unsafe_allow_html=True)
        if g["next"]:
            st.caption(f"{g['value']:.0f}% grown · {g['to_next']:.0f}% more until **{g['next']}**")
        goal = g["goal"]
        if goal["pct"] is not None:
            st.markdown(ui.card(f"⚖️ {goal['start']:g} kg → {goal['current']:g} kg → goal {goal['goal']:g} kg",
                                f"{goal['lost']:g} kg lost · {goal['pct']:.0f}% of the way there"),
                        unsafe_allow_html=True)
        else:
            st.info("Add your **starting weight** and **goal weight** in 🩺 Health profile so Tulsi can grow "
                    "with your journey.")
        st.caption("Tulsi grows from your progress *and* your effort: check-ins, walks, good sleep, water, "
                   "food scans and wins. She never shrinks or wilts. Bad days just pause her growth. 💜")

    st.divider()
    earned = [b for b in journey.badges(profile, _rows) if b["earned"]]
    all_badges = journey.badges(profile, _rows)
    st.subheader(f"🏅 Badges ({len(earned)} / {len(all_badges)})")
    st.markdown(ui.badges_html(all_badges), unsafe_allow_html=True)

    st.divider()
    st.subheader("💜 My wins (not just the scale)")
    st.caption("Clothes fitting better, more energy, climbing stairs easily, a regular cycle... "
               "These matter as much as any number.")
    with st.form("win", clear_on_submit=True):
        c1, c2, c3 = st.columns([1, 4, 1])
        emoji = c1.selectbox("Emoji", ["💜", "👗", "⚡", "🪜", "😴", "🩸", "😊", "💪", "🌟"], label_visibility="collapsed")
        text = c2.text_input("Win", placeholder="e.g. My old jeans fit again!", label_visibility="collapsed")
        if c3.form_submit_button("Add") and text.strip():
            storage.add_win(date.today().isoformat(), text.strip(), emoji)
            st.rerun()
    wins = storage.load_wins()
    for i in range(len(wins) - 1, -1, -1):
        w = wins[i]
        c1, c2 = st.columns([6, 1])
        c1.markdown(f'<div class="win">{w["emoji"]} {ui.html.escape(w["text"])} <small>· {w["date"]}</small></div>',
                    unsafe_allow_html=True)
        if c2.button("✕", key=f"win{i}"):
            storage.delete_win(i)
            st.rerun()


# ---------------- Page 2: Chat with Tulsi ----------------

elif page == "💬 Chat with Tulsi":
    chat = storage.load_chat()
    if not chat:
        name = profile.get("name") or "there"
        chat = [{"role": "assistant", "time": ui.now_time(),
                 "content": f"Hi {name}! I'm Tulsi 🌿, your little health buddy."},
                {"role": "assistant", "time": ui.now_time(),
                 "content": "No judgement here, ever 💜 Type anything below, or tap ✨ for a "
                            "meal plan or a home workout made just for you."}]

    st.markdown(ui.chat_header(), unsafe_allow_html=True)
    shown = 60  # show the most recent messages
    offset = max(0, len(chat) - shown)
    flow = st.empty()
    flow.markdown(ui.chat_window(chat[offset:]), unsafe_allow_html=True)

    # ----- The message bar: stays at the bottom of the screen -----
    with st.container(key="composer"):
        c_plus, c_form, c_mic = st.columns([1, 8, 1], vertical_alignment="center")

        with c_plus.popover("✨", help="Plans & ideas"):
            st.markdown("**Plans for you**")
            for label in ["🥗 Weekly meal plan", "🍱 Quick lunchbox ideas", "🛒 Grocery list", "🏠 Home workout plan"]:
                if st.button(label, key=f"qa_{label}"):
                    st.session_state.pending = label
            st.markdown("**Quick help**")
            for label in ["⏱️ 10-min home workout", "😔 I'm feeling unmotivated", "😴 Tips for better sleep",
                          "📬 My weekly report"]:
                if st.button(label, key=f"qb_{label}"):
                    st.session_state.pending = label

        with c_form.form("message", clear_on_submit=True, border=False):
            f1, f2 = st.columns([6, 1], vertical_alignment="center")
            typed = f1.text_input("Message", placeholder="Message Tulsi...", label_visibility="collapsed")
            sent = f2.form_submit_button("➤", type="primary")

        voice_prompt = None
        with c_mic.popover("🎙️", help="Talk to Tulsi"):
            speak = st.toggle("🔊 Tulsi speaks her replies", key="speak")
            audio = st.audio_input("Record a message") if hasattr(st, "audio_input") else None
            if audio is not None:
                audio_bytes = audio.getvalue()
                audio_id = hash(audio_bytes)
                if st.session_state.get("last_audio") != audio_id:  # only handle each recording once
                    st.session_state.last_audio = audio_id
                    with st.spinner("Listening..."):
                        try:
                            voice_prompt = "🎙️ " + coach.transcribe(audio_bytes, audio.type or "audio/wav")
                        except coach.CoachError as err:
                            show_error(err)

    prompt = (typed.strip() if sent and typed.strip() else None) or voice_prompt or st.session_state.pop("pending", None)
    if prompt:
        msg = {"role": "user", "content": prompt, "time": ui.now_time()}
        if prompt == "🛒 Grocery list":
            msg["ask"] = coach.grocery_request(chat)
        elif prompt in coach.QUICK_ACTIONS:
            msg["ask"] = coach.QUICK_ACTIONS[prompt]
        chat.append(msg)
        offset = max(0, len(chat) - shown)
        # your bubble pops up straight away, with Tulsi "typing"
        flow.markdown(ui.chat_window(chat[offset:], typing=True, pop_from=len(chat) - 1 - offset),
                      unsafe_allow_html=True)
        ui.scroll_to_bottom()
        try:
            reply = coach.chat_reply(profile, storage.recent_checkins(7), chat)
            first_new = len(chat)
            chat += ui.coach_bubbles(reply)
            storage.save_chat(chat)
            offset = max(0, len(chat) - shown)
            # Tulsi's replies pop in one after another
            flow.markdown(ui.chat_window(chat[offset:], pop_from=first_new - offset), unsafe_allow_html=True)
            if speak or voice_prompt:
                st.session_state.voice_reply = ui.speech(reply)
                if st.session_state.voice_reply is None:
                    st.caption("🔇 To hear Tulsi, run `pip install gtts` once and restart the app.")
        except coach.CoachError as err:
            chat.pop()
            flow.markdown(ui.chat_window(chat[max(0, len(chat) - shown):]), unsafe_allow_html=True)
            show_error(err)
    ui.scroll_to_bottom()

    if st.session_state.get("voice_reply"):
        st.audio(st.session_state.pop("voice_reply"), format="audio/mp3", autoplay=True)

    if storage.load_chat():
        with st.expander("⚙️ Chat options"):
            if st.button("🗑️ Clear chat"):
                storage.save_chat([])
                st.rerun()


# ---------------- Page 3: Health profile ----------------

else:
    ui.hero("🩺", "Your health profile", "This helps Tulsi give advice that fits <i>your</i> body and health")

    with st.expander("🔒 How your health data is used", expanded=not profile):
        st.markdown(
            "- Your profile is saved **only on this computer** (in the `data` folder).\n"
            "- When you talk to the coach, your profile and this week's check-ins are sent to the "
            "AI so it can personalise advice. Nothing else is shared.\n"
            "- You can delete your profile at any time at the bottom of this page.\n"
            "- FitBuddy is not a doctor and will never advise on medication."
        )

    with st.form("profile"):
        st.subheader("About you")
        c1, c2 = st.columns(2)
        name = c1.text_input("Name", profile.get("name", ""))
        age = c2.number_input("Age", 0, 100, int(profile.get("age", 0)))
        c3, c4, c5, c6 = st.columns(4)
        height_cm = c3.number_input("Height (cm)", 0.0, 250.0, float(profile.get("height_cm", 0.0)), 0.5)
        start_weight_kg = c4.number_input("Starting weight (kg)", 0.0, 300.0, float(profile.get("start_weight_kg", 0.0)), 0.5,
                                          help="Your weight when you began your journey. Tulsi grows as you move from here to your goal.")
        current_weight_kg = c5.number_input("Current weight (kg)", 0.0, 300.0, float(profile.get("current_weight_kg", 0.0)), 0.5)
        goal_weight_kg = c6.number_input("Goal weight (kg)", 0.0, 300.0, float(profile.get("goal_weight_kg", 0.0)), 0.5)
        calorie_target = st.number_input(
            "Daily calorie target (optional)", 0, 5000, int(profile.get("calorie_target", 0)), 50,
            help="Ideally one suggested by your doctor or dietitian. Leave 0 if you don't have one.",
        )

        st.subheader("Health")
        condition_options = ["PCOS", "Thyroid issues", "Diabetes / pre-diabetes", "Insulin resistance",
                             "High blood pressure", "Anaemia", "None"]
        conditions = st.multiselect("Health conditions", condition_options,
                                    [c for c in profile.get("conditions", []) if c in condition_options])
        medications = st.text_input("Current medications (if any)", profile.get("medications", ""))
        cycle = st.text_input("Menstrual cycle", profile.get("cycle", ""),
                              placeholder="e.g. Regular since Feb 2026 after weight loss")
        limitations = st.text_input("Injuries or exercise limitations", profile.get("limitations", ""))

        st.subheader("Food & goals")
        diet = st.text_input("Diet / food preferences", profile.get("diet", ""),
                             placeholder="e.g. Vegetarian, Kerala home food, love rice")
        allergies = st.text_input("Allergies", profile.get("allergies", ""))
        goals = st.text_area("Your goals", profile.get("goals", ""),
                             placeholder="e.g. Lose weight steadily, manage PCOS, feel more energetic")
        notes = st.text_area("Anything else your coach should know?", profile.get("notes", ""),
                             placeholder="e.g. I prefer working out at home, stress affects my weight")

        consent = st.checkbox("I understand how my health data is used (see above).", value=bool(profile))
        save = st.form_submit_button("Save profile", type="primary")

    if save:
        if not consent:
            st.warning("Please tick the box to confirm you understand how your data is used.")
        else:
            profile.update({
                "name": name, "age": age, "height_cm": height_cm, "start_weight_kg": start_weight_kg,
                "current_weight_kg": current_weight_kg, "goal_weight_kg": goal_weight_kg,
                "calorie_target": calorie_target, "conditions": conditions,
                "medications": medications, "cycle": cycle, "limitations": limitations,
                "diet": diet, "allergies": allergies, "goals": goals, "notes": notes,
            })
            storage.save_profile(profile)
            st.success("Profile saved! Your coach will now use it. 🌱")

    # ----- Cycle tracking -----
    st.divider()
    st.subheader("🌙 My cycle")
    st.caption("Add the dates your recent periods started. Tulsi uses them to tailor food and exercise "
               "tips to your cycle phase. With PCOS, cycles can be irregular, so more dates mean better guesses.")
    c1, c2 = st.columns([3, 1])
    p_day = c1.date_input("Period start date", value=date.today(), max_value=date.today(), key="pday")
    c2.write("")
    if c2.button("Add date"):
        storage.add_period(p_day.isoformat())
        st.rerun()
    cyc = journey.cycle_info()
    if cyc:
        st.markdown(ui.card(f"{cyc['emoji']} Today: cycle day {cyc['day']} · {cyc['phase']} phase",
                            f"Average cycle: {cyc['length']} days · next period around {cyc['next_period']}"
                            f"{' · looks irregular' if cyc['irregular'] else ''}"), unsafe_allow_html=True)
    for d in reversed(storage.load_periods()):
        c1, c2 = st.columns([4, 1])
        c1.write(f"🩸 {d}")
        if c2.button("Remove", key=f"p{d}"):
            storage.delete_period(d)
            st.rerun()

    # ----- Medical report upload -----
    st.divider()
    st.subheader("📄 Medical reports (optional)")
    st.caption("Upload a blood test or hormone report (PDF). The AI pulls out the key findings, "
               "and you can check and edit them before saving.")

    uploaded = st.file_uploader("Upload a PDF report", type="pdf")
    if uploaded and st.button("Summarise report"):
        text = "\n".join(p.extract_text() or "" for p in PdfReader(uploaded).pages).strip()
        if not text:
            st.error("Couldn't read text from this PDF (it may be a scanned image).")
        else:
            with st.spinner("Reading your report..."):
                try:
                    st.session_state.report_draft = coach.summarise_report(text)
                except coach.CoachError as err:
                    show_error(err)

    if "report_draft" in st.session_state:
        edited = st.text_area("Check the summary, then save it", st.session_state.report_draft, height=200)
        if st.button("Save summary to my profile"):
            profile["report_summary"] = edited
            storage.save_profile(profile)
            del st.session_state.report_draft
            st.success("Report summary saved to your profile.")
            st.rerun()

    if profile.get("report_summary"):
        with st.expander("Saved report summary"):
            st.markdown(profile["report_summary"])

    # ----- Delete data -----
    if profile:
        st.divider()
        if st.button("🗑️ Delete my health profile"):
            storage.delete_profile()
            st.success("Your profile has been deleted.")
            st.rerun()
