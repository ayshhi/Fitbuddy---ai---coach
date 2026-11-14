"""
app.py - the FitBuddy app you see in the browser (built with Streamlit).

Run it with:   streamlit run app.py
"""

from datetime import date, datetime, timedelta

import streamlit as st
from pypdf import PdfReader

import pandas as pd

import cards
import coach
import crossword
import diet
import exercise
import food
import games
import garden
import journey
import quicklog
import reminders
import samsung
import storage
import ui

st.set_page_config(page_title="FitBuddy - AI Health Coach", page_icon="🌿", layout="wide")
ui.inject_css()
ui.inject_card_css()
ui.inject_page_css()
ui.inject_spacing_css()
ui.inject_widget_css()
ui.auto_size()


def show_error(err: Exception) -> None:
    st.error(f"😕 {err}")


# ---------------- Sidebar navigation ----------------

ui.sidebar_brand()
PAGES = ["🌈 Home", "🏠 Today", "🔥 Exercise", "🥗 Food & diet", "💬 Chat with Tulsi", "🆘 Craving SOS", "🌡️ Symptoms",
         "🌸 My garden", "🎯 Wellness Bingo", "🧩 Crossword", "📊 Progress", "🩺 Health profile"]
page = st.sidebar.radio("Go to", PAGES, key="nav", label_visibility="collapsed")


def go_to_chat(message: str, **extra) -> None:
    """Button callback: open the chat and send a message there."""
    st.session_state.nav = "💬 Chat with Tulsi"
    st.session_state.pending = message
    st.session_state.update(extra)


def go_to(target: str) -> None:
    st.session_state.nav = target


def water_tulsi(day: str) -> None:
    storage.set_water(day, storage.water_today(day) + 1)
    st.session_state.watered = True
show_tulsi = st.sidebar.toggle("🌿 Tulsi on screen", value=True, key="show_tulsi")
st.sidebar.divider()
st.sidebar.caption(
    "FitBuddy gives general wellness support, not medical advice. "
    "Always talk to your doctor about medical questions."
)

profile = storage.load_profile()

# Tulsi the mascot, bouncing in the corner (click her and she smiles)
ui.mascot(profile.get("name", ""), show=show_tulsi and page != "🌈 Home", lift=page == "💬 Chat with Tulsi")

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


# ---------------- Page: Home (Tulsi under a rainbow) ----------------

if page == "🌈 Home":
    today_str = date.today().isoformat()
    checked = {d for d, r in _rows.items() if r.get("checked_in")}
    streak = journey._streak(checked, date.today())
    chips = [f"{_growth['emoji']} Tulsi is a {_growth['name'].lower()}",
             f"💧 {storage.water_today(today_str)} / 8 glasses today",
             "✅ Checked in today" if today_str in checked else "📝 Not checked in yet"]
    if streak >= 2:
        chips.append(f"🔥 {streak}-day best streak")
    chips.append(f"🎯 Bingo: {len(games.ticked())}/25 this week")
    daily_key, _, daily_cw = crossword.daily()
    if not crossword.state(daily_key, daily_cw)["over"]:
        chips.append("🧩 Today's crossword is waiting")
    st.markdown(ui.home_html(profile.get("name", ""), chips), unsafe_allow_html=True)
    _, mid, _ = st.columns([2, 1, 2])
    with mid.container(key="letsgo"):
        st.button("Let's start ✨", on_click=go_to, args=("🏠 Today",))


# ---------------- Page 1: Today's check-in ----------------

elif page == "🏠 Today":
    name = profile.get("name") or "there"
    st.markdown(ui.chat_window(
        [{"role": "assistant", "content": f"Hey {name}! 🌿 How was your day? Tell me below and "
          "I'll help you plan a lovely tomorrow 💜", "time": ui.now_time()}],
        ), unsafe_allow_html=True)
    st.write("")

    today_str = date.today().isoformat()
    glasses = storage.water_today(today_str)

    def run_feedback(day: str, summary_text: str, sleep_hours: float, stress: int) -> None:
        """Shows your check-in as a chat bubble, gets Tulsi's reply, and saves tomorrow's plan as a checklist."""
        if sleep_hours and sleep_hours < 6 or stress >= 4:
            st.warning("🧘 Low sleep or high stress can raise cortisol, which makes your body hold on "
                       "to weight. Tomorrow is a day for gentle movement and rest, not pushing hard.")
        me = {"role": "user", "content": summary_text, "time": ui.now_time()}
        box = st.empty()
        box.markdown(ui.chat_window([me], typing=True, pop_from=0), unsafe_allow_html=True)
        try:
            reply = coach.daily_feedback(profile, storage.recent_checkins(7), day)
            text, items = coach.extract_plan(reply)
            if items:
                tomorrow = (date.fromisoformat(day) + timedelta(days=1)).isoformat()
                storage.save_plan(tomorrow, day, items)
                st.session_state.plan_saved = True
            box.empty()
            st.session_state.feedback = [me] + ui.coach_bubbles(text)
            st.session_state.feedback_new = True
            storage.save_chat(storage.load_chat() + st.session_state.feedback)  # also appears in the chat
        except coach.CoachError as err:
            box.empty()
            show_error(err)

    # ----- Row 1: today's plan  |  just tell Tulsi -----
    plan_col, tell_col = st.columns([2, 3])
    with plan_col.container(border=True, key="ck_plan"):
        plan = storage.load_plans().get(today_str)
        tomorrow_str = (date.today() + timedelta(days=1)).isoformat()
        next_plan = storage.load_plans().get(tomorrow_str)
        ui.card_header("📋", "Today's plan from Tulsi",
                       "Tick them off as you go" if plan else "3 tiny steps: movement, food and rest", tint="#EDE2FB")
        if plan:
            for i, item in enumerate(plan["items"]):
                st.checkbox(item["text"], value=item.get("done", False), key=f"plan_{today_str}_{i}",
                            on_change=lambda d=today_str, i=i: storage.set_plan_item(d, i, st.session_state[f"plan_{d}_{i}"]))
            done = sum(1 for i in plan["items"] if i.get("done"))
            if done == len(plan["items"]):
                st.markdown(ui.card("🎉 All done!", "Tulsi is so proud of you. Rest well tonight 💜"), unsafe_allow_html=True)
            else:
                st.caption(f"{done} of {len(plan['items'])} done. Small steps count. 🌱")
        else:
            st.caption("No plan for today yet. Tulsi can make one now, or you'll get tomorrow's after tonight's check-in.")
            if st.button("✨ Make today's plan", type="primary", key="make_plan"):
                with st.spinner("Tulsi is planning your day..."):
                    try:
                        storage.save_plan(today_str, today_str, coach.plan_for_today(profile, storage.recent_checkins(7)))
                        st.rerun()
                    except coach.CoachError as err:
                        show_error(err)
        if next_plan:
            st.markdown(ui.card("🌙 Tomorrow's plan is ready",
                                "<br>".join(f"• {ui.html.escape(i['text'])}" for i in next_plan["items"])
                                + "<br><span style='font-size:.85rem'>You can tick these off tomorrow.</span>"),
                        unsafe_allow_html=True)
        ft = journey.follow_through(7)
        if ft["total"]:
            st.caption(f"This week: {ft['done']} of {ft['total']} plan steps done ({ft['rate']:.0%}). "
                       "Tulsi makes plans easier or harder to match what works for you.")

    with tell_col.container(border=True, key="ck_tell"):
        ui.card_header("💬", "Just tell Tulsi", "Describe your day in your own words, and she'll fill in your check-in",
                       tint="#FCE8F3")
        with st.form("quick_log", border=False):
            said = st.text_area("Your day", label_visibility="collapsed", height=120,
                                placeholder="e.g. Slept about 6 hours. Walked 30 min after work. Dosa and chai for breakfast, "
                                            "rice with sambar for lunch. 5 glasses of water. A bit stressed and tired, bloated.")
            go = st.form_submit_button("✨ Fill in my check-in", type="primary")
        audio = st.audio_input("🎙️ Or say it out loud") if hasattr(st, "audio_input") else None
        spoken = None
        if audio is not None and st.session_state.get("last_day_audio") != hash(audio.getvalue()):
            st.session_state.last_day_audio = hash(audio.getvalue())
            with st.spinner("Listening..."):
                try:
                    spoken = coach.transcribe(audio.getvalue(), audio.type or "audio/wav")
                except coach.CoachError as err:
                    show_error(err)
        words = spoken or (said.strip() if go else "")
        if words:
            with st.spinner("Tulsi is reading about your day..."):
                try:
                    st.session_state.quick = {"day": today_str, "parsed": coach.parse_day(words), "words": words}
                except coach.CoachError as err:
                    show_error(err)

    # ----- Confirm what Tulsi understood -----
    quick = st.session_state.get("quick")
    if quick:
        with st.container(border=True, key="ck_confirm"):
            ui.card_header("✅", "Here's what I understood", f"“{ui.html.escape(quick['words'][:160])}”", tint="#E7F4EC")
            chips = quicklog.understood(quick["parsed"])
            if chips:
                st.markdown('<div class="chips" style="gap:.5rem">' + "".join(
                    f'<span class="chip" style="font-size:.95rem !important;padding:.35rem .8rem">{ui.html.escape(c)}</span>'
                    for c in chips) + "</div>", unsafe_allow_html=True)
                st.caption("Anything you didn't mention stays as it was (Samsung data, earlier entries).")
                b1, b2, _ = st.columns([2, 2, 3])
                if b1.button("✅ Looks right, save it", type="primary", key="quick_save"):
                    entry = quicklog.save(quick["day"], quick["parsed"])
                    del st.session_state.quick
                    st.success("Saved to your check-in! 🎉")
                    run_feedback(quick["day"], quicklog.summary(quick["day"], entry),
                                 float(entry.get("sleep_hours") or 0), int(entry.get("stress") or 2))
                if b2.button("✏️ Not quite, discard", key="quick_discard"):
                    del st.session_state.quick
                    st.rerun()
            else:
                st.info("I couldn't find anything to log in that. Try mentioning sleep, food, exercise, water or how you feel.")
                if st.button("OK", key="quick_ok"):
                    del st.session_state.quick
                    st.rerun()

    if st.session_state.get("feedback"):
        pop = 1 if st.session_state.pop("feedback_new", False) else None
        st.markdown(ui.chat_window(st.session_state.feedback, pop_from=pop), unsafe_allow_html=True)
        if st.session_state.pop("plan_saved", False) or pop:
            st.caption("📋 Tulsi's 3 steps are saved as tomorrow's checklist.")
        st.caption("💬 Want to talk more? Continue in **Chat with Tulsi**.")

    # ----- Row 2: Tulsi, cycle and water -----
    left, right = st.columns([1, 2])
    glasses = storage.water_today(today_str)
    with left:
        st.markdown(garden.tulsi_img(_growth["stage"], "10rem", fresh=glasses >= 8,
                                     watering=st.session_state.pop("watered", False)), unsafe_allow_html=True)
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
        fresh_note = " Tulsi's leaves are sparkling! ✨" if glasses >= 8 else " Each glass you drink waters Tulsi too."
        st.markdown(ui.card(f"💧 Water today: {glasses} / 8 glasses",
                            f"<span class='water'>{'💧' * min(glasses, 8)}{'🤍' * max(0, 8 - glasses)}</span><br>{fresh_note}"),
                    unsafe_allow_html=True)
        w1, w2, _ = st.columns([2, 1, 3])
        w1.button("💧 I drank a glass: water Tulsi", key="water_add", on_click=water_tulsi, args=(today_str,))
        if w2.button("➖", key="water_remove", help="Remove a glass"):
            storage.set_water(today_str, glasses - 1)
            st.rerun()

        q1, q2 = st.columns(2)
        q1.button("🆘 Having a craving?", key="to_crave", on_click=go_to, args=("🆘 Craving SOS",))
        q2.button("🌡️ Log PCOS symptoms", key="to_sym", on_click=go_to, args=("🌡️ Symptoms",))


    if not profile:
        st.info("Tip: fill in your **🩺 Health profile** first so your coach can personalise advice.")

    # ----- The detailed check-in, for when you want to fill things in by hand -----
    with st.expander("📝 Detailed check-in: fill in everything by hand", expanded=False):
        day = st.date_input("Date", value=date.today(), max_value=date.today()).isoformat()
        existing = storage.load_checkins().get(day, {})
        sh = storage.load_samsung().get(day, {})  # imported Samsung Health data for this day

        def prefill(key, sh_key, default):
            """Use the saved check-in value, else the Samsung value, else a default."""
            return existing.get(key, sh.get(sh_key, default))

        with st.form("checkin", border=False):
            top_left, top_right = st.columns(2)
            with top_left.container(border=True, key="ck_sleep"):
                ui.card_header("😴", "Sleep & activity",
                               "✅ Filled in from Samsung Health" if sh else "Copy these from Samsung Health, or import on 📊 Progress",
                               tint="#E5F2FD")
                sleep_hours = st.number_input("Sleep (hours)", 0.0, 16.0, float(prefill("sleep_hours", "sleep_hours", 7.0)), 0.5)
                c1, c2 = st.columns(2)
                steps = c1.number_input("Steps", 0, 100000, int(prefill("steps", "steps", 0)), 500)
                distance_km = c2.number_input("Distance (km)", 0.0, 100.0, float(prefill("distance_km", "distance_km", 0.0)), 0.5)

            with top_right.container(border=True, key="ck_food"):
                scanned = storage.day_calories(day)
                ui.card_header("🍽️", "Food & exercise",
                               f"📸 {scanned} kcal from your food scans" if scanned else "Scan or log meals on 🥗 Food & diet to fill this in",
                               tint="#FEF0E1")
                calories = st.number_input(
                    "Calories eaten today (approx.)", 0, 10000, scanned or int(existing.get("calories", 0)), 50,
                    help="Filled in automatically from 📸 Food scan. You can also type an estimate.",
                )
                c4, c5 = st.columns([3, 2])
                default_ex = f"Walk ({sh['workout_km']} km)" if sh.get("workout_min") else ""
                exercise = c4.text_input("Exercise done", existing.get("exercise", default_ex), placeholder="e.g. walk, yoga")
                exercise_minutes = c5.number_input("Minutes", 0, 600, int(prefill("exercise_minutes", "workout_min", 0)), 5)

            with st.container(border=True, key="ck_feel"):
                ui.card_header("💭", "How you feel", "There are no wrong answers here", tint="#FCE8F3")
                c6, c7 = st.columns(2)
                stress = c6.slider("Stress  ·  1 = calm, 5 = very stressed", 1, 5, int(existing.get("stress", 2)))
                energy = c7.slider("Energy  ·  1 = exhausted, 5 = great", 1, 5, int(existing.get("energy", 3)))
                moods = ["😊 Good", "🙂 Okay", "😐 Meh", "😔 Low", "😣 Frustrated"]
                mood = st.radio("Mood", moods, index=moods.index(existing["mood"]) if existing.get("mood") in moods else 1, horizontal=True)
                c8, c9 = st.columns([3, 1])
                notes = c8.text_area("Anything else? (cravings, period, how you're feeling...)", existing.get("notes", ""), height=110)
                with c9:
                    weight_kg = st.number_input(
                        "Weight (kg, optional)", 0.0, 300.0, float(prefill("weight_kg", "weight_kg", 0.0)), 0.1,
                        help="Optional. Once a week is plenty. Daily weight goes up and down with water, periods and salt.",
                    )
                    period_started = st.checkbox("🩸 My period started today", value=day in storage.load_periods())

            submitted = st.form_submit_button("Save & get my coach's feedback ✨", type="primary")

        if submitted:
            if period_started:
                storage.add_period(day)
            entry = {
                "sleep_hours": sleep_hours, "steps": steps, "distance_km": distance_km,
                "calories": calories, "exercise": exercise, "exercise_minutes": exercise_minutes,
                "stress": stress, "energy": energy, "mood": mood, "notes": notes,
                "foods": storage.day_foods(day), "weight_kg": weight_kg or None,
            }
            storage.save_checkin(day, entry)
            st.success("Check-in saved! 🎉")
            run_feedback(day, quicklog.summary(day, entry), sleep_hours, stress)
            st.rerun()

    # ----- This week -----
    week = storage.recent_checkins(7)
    if week:
        ui.section("📅 Your week")
        avg = lambda k: sum(float(c.get(k, 0) or 0) for c in week.values()) / len(week)
        ft = journey.follow_through(7)
        st.markdown(ui.tiles([
            ("😴 AVG SLEEP", f"{avg('sleep_hours'):.1f} h", "per night"),
            ("👟 AVG STEPS", f"{avg('steps'):,.0f}", "per day"),
            ("✅ CHECK-INS", f"{len(week)} / 7", "days this week"),
            ("📋 PLAN STEPS", f"{ft['done']} / {ft['total']}" if ft["total"] else "–", "done this week"),
        ]), unsafe_allow_html=True)

    # ----- Reminders on your phone -----
    with st.expander("⏰ Daily reminders on your phone"):
        st.caption("Pick your reminders, download the file, and your phone's calendar will remind you every day, "
                   "even when FitBuddy is closed.")
        chosen = []
        cols = st.columns(3)
        for i, (key, title, hhmm, desc) in enumerate(reminders.DEFAULTS):
            with cols[i % 3]:
                on = st.checkbox(title, value=True, key=f"rem_{key}")
                t = st.time_input("Time", value=datetime.strptime(hhmm, "%H:%M").time(), key=f"remt_{key}",
                                  label_visibility="collapsed", step=900)
                if on:
                    chosen.append((title, t.strftime("%H:%M"), desc))
        st.download_button("📅 Download my reminders", reminders.build_ics(chosen), file_name="fitbuddy_reminders.ics",
                           mime="text/calendar", type="primary", disabled=not chosen)
        st.markdown("**On your phone:** send this file to yourself (WhatsApp or email), tap it, and choose "
                    "**Calendar → Add / Import**.  \n**On Google Calendar (laptop):** Settings → Import & export → Import.")

# ---------------- Page: Food scan ----------------

elif page == "🆘 Craving SOS":
    left, right = st.columns([3, 2])
    with left:
        with st.form("craving"):
            kind = st.radio("What are you craving?", list(journey.SWAPS), horizontal=True)
            strength = st.slider("How strong is it? (1 = a little, 5 = very strong)", 1, 5, 3)
            trigger = st.radio("What might be behind it?", journey.TRIGGERS, horizontal=True, index=len(journey.TRIGGERS) - 1)
            note = st.text_input("Anything else? (optional)", placeholder="e.g. long day at work, it's 10 pm")
            if st.form_submit_button("Log it and help me 💜", type="primary"):
                storage.add_craving({"when": datetime.now().strftime("%Y-%m-%dT%H:%M"), "kind": kind,
                                     "strength": strength, "trigger": trigger, "note": note, "outcome": None})
                st.session_state.last_craving = (kind, f"{trigger}, strength {strength}/5. {note}".strip())
    with right:
        st.markdown(ui.BREATHE_HTML, unsafe_allow_html=True)

    if st.session_state.get("last_craving"):
        kind, details = st.session_state.last_craving
        ui.section("Try one of these instead", "Quick swaps that need no shopping trip. Pick whatever feels doable.")
        swap_cards = "".join(f'<div class="food"><div class="n">{ui.html.escape(x)}</div></div>' for x in journey.SWAPS[kind])
        st.markdown(f'<div class="foods">{swap_cards}</div>', unsafe_allow_html=True)
        st.button("💬 Talk it through with Tulsi", type="primary", on_click=go_to_chat,
                  args=(f"🆘 Craving SOS: {kind}",), kwargs={"craving": (kind, details)})

    cravings = storage.load_cravings()
    open_ones = [i for i, c in enumerate(cravings) if not c.get("outcome")]
    if open_ones:
        i = open_ones[-1]
        c = cravings[i]
        ui.section("How did it go?", f"Your {c['kind'].split(' ', 1)[1].lower()} craving from "
                   f"{datetime.fromisoformat(c['when']).strftime('%d %b, %I:%M %p')}. Every answer is a good answer.")
        cols = st.columns(3)
        for col, (key, label) in zip(cols, journey.OUTCOMES.items()):
            if col.button(label, key=f"out_{key}"):
                storage.set_craving_outcome(i, key)
                st.toast({"mindful": "Enjoying food mindfully is a win 💜", "swap": "Nice swap! 🥗",
                          "passed": "You rode the wave 🌊"}[key])
                st.rerun()

    pat = journey.craving_patterns()
    if pat and pat["total"] >= 3:
        ui.section("Your craving patterns", "Knowing when cravings come makes them easier to plan for.")
        outcomes = pat["outcomes"]
        handled = sum(outcomes.values())
        st.markdown(ui.tiles([
            ("🍬 CRAVINGS LOGGED", str(pat["total"]), "so far"),
            ("🕐 MOST OFTEN", pat["times"].most_common(1)[0][0], "time of day"),
            ("🔎 TOP TRIGGER", pat["triggers"].most_common(1)[0][0], "what's often behind it"),
            ("🌊 PASSED OR SWAPPED", f"{(outcomes['passed'] + outcomes['swap']) / handled:.0%}" if handled else "–",
             "of cravings you followed up"),
        ]), unsafe_allow_html=True)
        a, b = st.columns(2)
        with a:
            st.markdown("**By time of day**")
            st.markdown(ui.bars_html(dict(pat["times"])), unsafe_allow_html=True)
        with b:
            st.markdown("**By trigger**")
            st.markdown(ui.bars_html(dict(pat["triggers"])), unsafe_allow_html=True)
        phases = {k: v for k, v in pat["phases"].items() if k != "Unknown"}
        if phases:
            st.markdown("**By cycle phase**")
            st.markdown(ui.bars_html(phases), unsafe_allow_html=True)
            st.caption("Many people with PCOS crave more in the luteal phase (the week or so before a period). "
                       "If that's you too, it's your hormones, not a lack of willpower.")
    elif pat:
        st.caption(f"You've logged {pat['total']} craving(s). After 3, Tulsi starts showing your patterns here.")


elif page == "🌡️ Symptoms":
    day = st.date_input("Date", value=date.today(), max_value=date.today(), key="sym_day").isoformat()
    old = storage.load_symptoms().get(day, {})
    with st.form("symptoms"):
        st.markdown("**How strong was each symptom today?**")
        levels = {}
        keys = list(journey.SYMPTOMS.items())
        for row in (keys[:4], keys[4:]):
            cols = st.columns(4)
            for col, (key, label) in zip(cols, row):
                levels[key] = journey.LEVELS.index(col.select_slider(
                    label, journey.LEVELS, value=journey.LEVELS[int(old.get(key, 0))], key=f"s_{key}"))
        note = st.text_input("Notes (optional)", old.get("note", ""), placeholder="e.g. new spots on chin, bloated after dinner")
        if st.form_submit_button("Save today's symptoms", type="primary"):
            storage.save_symptoms(day, {**levels, "note": note})
            st.toast("Saved. Thank you for listening to your body 💜")
            st.rerun()

    sym = journey.symptom_days()
    if sym:
        ui.section("Last 30 days", "Darker = stronger · dotted = not logged · hover a square for details")
        days30 = [(date.today() - timedelta(days=i)).isoformat() for i in range(29, -1, -1)]
        grid = [[(float(sym[d].get(k, 0)) if d in sym else None) for d in days30] for k in journey.SYMPTOMS]
        st.markdown(f'<div class="soft-panel">{ui.heat_grid_svg(list(journey.SYMPTOMS.values()), [d[8:] + "/" + d[5:7] for d in days30], grid, col_every=5)}</div>',
                    unsafe_allow_html=True)

        by_phase = journey.symptoms_by_phase()
        if by_phase:
            ui.section("By cycle phase", "Average level in each phase of your cycle, from the period dates you've logged")
            phases = list(by_phase)
            grid = [[by_phase[ph][k] for ph in phases] for k in journey.SYMPTOMS]
            labels = [f"{ph}|{by_phase[ph]['_days']} days" for ph in phases]
            c1, _ = st.columns([2, 1])
            c1.markdown(f'<div class="soft-panel">{ui.heat_grid_svg(list(journey.SYMPTOMS.values()), labels, grid, cell=58, label_w=110)}</div>',
                        unsafe_allow_html=True)

        ui.section("Patterns Tulsi found", "Only shown when there's enough data and it's unlikely to be luck")
        patterns = journey.symptom_patterns()
        if patterns:
            for pt in patterns:
                st.markdown(ui.card(f"{'🔎' if pt['strength'] == 'Strong pattern' else '🌱'} {pt['strength']}",
                                    f"{ui.html.escape(pt['text'])}<br><span style='font-size:.85rem'>{ui.html.escape(pt['evidence'])}</span>"),
                            unsafe_allow_html=True)
        else:
            st.caption(f"You've logged symptoms on {len(sym)} day(s). Patterns need at least 3 days on each side of a "
                       "comparison (e.g. 3 low-sleep days and 3 good-sleep days), so keep logging. About 2-3 weeks is ideal.")

        b1, b2 = st.columns(2)
        b1.button("💬 Ask Tulsi about my symptoms", type="primary", on_click=go_to_chat, args=("🌡️ Explain my symptoms",))
        b2.download_button("🩺 Download a summary for my doctor (PDF)", cards.doctor_report(profile),
                           file_name=f"health_summary_{date.today().isoformat()}.pdf", mime="application/pdf",
                           key="doc_report_sym")
    else:
        st.caption("No symptoms logged yet. Start today, and in a couple of weeks Tulsi can show you what affects them.")


elif page == "🎯 Wellness Bingo":
    week = games.week_key()
    card = games.bingo_card()
    done = games.ticked()
    auto = games.auto_done()
    lines = games.bingo_lines(done)
    days_left = 6 - date.today().weekday()

    seen = st.session_state.get("bingo_seen", {}).get(week)
    if seen is not None and lines > seen:
        st.balloons()
        st.toast("🎉 BINGO! Tulsi is doing a happy dance!" if lines == 1 else f"🎉 {lines} bingos! Amazing!")
    st.session_state.setdefault("bingo_seen", {})[week] = lines

    st.caption("Same card for you and your friends this week. Tap a number to see its task.")
    st.markdown(ui.tiles([
        ("🟪 SQUARES", f"{len(done)} / 25", "done this week"),
        ("🎯 BINGOS", str(lines), "rows, columns or diagonals"),
        ("📅 DAYS LEFT", str(days_left) if days_left else "Last day!", "new card on Monday"),
    ]), unsafe_allow_html=True)

    def square_body(i: int) -> None:
        """What you see when you tap a number."""
        tid, emoji, text, auto_key = card[i]
        st.markdown(f'<div style="text-align:center;font-size:4rem;line-height:1.2">{emoji}</div>'
                    f'<div style="text-align:center;font-size:1.4rem;font-weight:800;color:#2A2140;margin:.4rem 0 1rem">'
                    f'{ui.html.escape(text)}</div>', unsafe_allow_html=True)
        if tid == "free":
            st.success("This one is always free. Always true. 💜")
        elif auto_key and auto_key in auto:
            st.success("Already done! Your data shows it ✨")
        elif i in done:
            st.success("You did this one! 🎉")
            if st.button("↩️ Oops, not done yet", key=f"undo_{i}"):
                storage.toggle_bingo(week, i)
                st.rerun()
        else:
            if auto_key:
                st.caption("✨ This one will also tick itself when your data shows it.")
            if st.button("✅ I did it!", type="primary", key=f"do_{i}"):
                storage.toggle_bingo(week, i)
                st.rerun()

    dialog = getattr(st, "dialog", None) or getattr(st, "experimental_dialog", None)
    show_square = dialog("Bingo square")(square_body) if dialog else None

    css = ['.st-key-bingo_grid [data-testid="stHorizontalBlock"] { flex-wrap: nowrap !important; gap: .9rem !important; }',
           '.st-key-bingo_grid [data-testid="stColumn"], .st-key-bingo_grid [data-testid="column"] { flex: 1 1 0 !important; min-width: 0 !important; }',
           '.st-key-bingo_grid [data-testid="stVerticalBlock"] { gap: .9rem !important; }',
           '.st-key-bingo_grid .stButton, .st-key-bingo_grid [class*="st-key-sq_"] { width: 100% !important; }',
           '.st-key-bingo_grid { max-width: 34rem; margin: 0 auto; }',
           '.stApp .st-key-bingo_grid button { width: 100% !important; height: 5.6rem !important; border-radius: 18px !important; '
           'background: #FFFFFF !important; border: 2px solid #E6DDF3 !important; box-shadow: 0 6px 18px rgba(78,42,132,.07) !important; }',
           '.stApp .st-key-bingo_grid button p { font-size: 1.6rem !important; font-weight: 800 !important; color: #4E2A84 !important; }',
           '.stApp .st-key-bingo_grid button:hover { border-color: #C38BEA !important; transform: translateY(-3px) scale(1.02); }']
    for i in done:
        css.append(f'.stApp .st-key-sq_{i} button {{ background: linear-gradient(135deg, #7B3FBF, #A66BE0) !important; '
                   f'border-color: transparent !important; }} .stApp .st-key-sq_{i} button p {{ color: #FFFFFF !important; }}')
    st.markdown("<style>" + "".join(css) + "</style>", unsafe_allow_html=True)

    grid = st.container(key="bingo_grid")
    for r in range(5):
        cols = grid.columns(5)
        for c in range(5):
            i = r * 5 + c
            label = "💜" if card[i][0] == "free" else (f"✓ {i + 1}" if i in done else str(i + 1))
            if cols[c].button(label, key=f"sq_{i}"):
                if show_square:
                    show_square(i)
                else:
                    st.session_state.bingo_open = i
    if not show_square and st.session_state.get("bingo_open") is not None:
        with st.container(border=True):
            square_body(st.session_state.bingo_open)

    if done - {12}:
        st.markdown("**Done this week:** " + " · ".join(f"{card[i][1]} {card[i][2]}" for i in sorted(done) if i != 12))

    ui.section("Share with friends", "Your friends see the same card this week. Send your progress and invite them!")
    share = games.bingo_share(profile.get("name", ""), done)
    s1, s2 = st.columns([3, 2])
    s1.code(share, language=None)
    with s2:
        st.link_button("📲 Share on WhatsApp", games.whatsapp(share), type="primary")
        st.caption("Tip: make a WhatsApp group with friends and share every Sunday. Nobody loses, everyone gets healthier. 🌿")


elif page == "🧩 Crossword":
    st.markdown("""<style>
    .st-key-cw_mode label p, .st-key-cw_theme label p, .st-key-cw_custom_pick label p { font-size:1.15rem !important; font-weight:700 !important; }
    .st-key-cw_mode [role="radiogroup"] > label, .st-key-cw_theme [role="radiogroup"] > label,
    .st-key-cw_custom_pick [role="radiogroup"] > label { padding:.7rem 1.3rem !important; }
    [class*="st-key-cwbox"] label p { font-size:1.12rem !important; font-weight:600 !important; line-height:1.4 !important; }
    [class*="st-key-cwbox"] input { font-size:1.3rem !important; letter-spacing:.25em; text-transform:uppercase; height:3rem; }
    .st-key-cw_own label p { font-size:1.15rem !important; font-weight:700 !important; }
    .st-key-cw_own input { font-size:1.2rem !important; height:3.2rem; }
    </style>""", unsafe_allow_html=True)
    mode = st.radio("Mode", ["📅 Today's crossword", "🗂️ Pick a theme", "✍️ My own theme"], horizontal=True,
                    label_visibility="collapsed", key="cw_mode")
    puzzle = None
    rounds = st.session_state.setdefault("cw_rounds", {})
    if mode.startswith("📅"):
        puzzle = crossword.daily()
        st.caption("Everyone gets this same puzzle today, so you can compare with friends. A new one every day.")
    elif mode.startswith("🗂️"):
        theme = st.radio("Theme", list(crossword.THEMES), horizontal=True, key="cw_theme")
        puzzle = crossword.themed(theme, rounds.get(theme, 0))
        if st.button("🔀 Give me a different puzzle", key="cw_new_theme"):
            rounds[theme] = rounds.get(theme, 0) + 1
            st.rerun()
    else:
        with st.container(key="cw_own"), st.form("own_theme", border=False):
            c1, c2 = st.columns([3, 1], vertical_alignment="bottom")
            typed = c1.text_input("Type any theme", placeholder="e.g. Onam festival, monsoon foods, Bollywood dance, my favourite things")
            go = c2.form_submit_button("✨ Make my crossword", type="primary")
        if go and typed.strip():
            with st.spinner("Tulsi is writing words and clues for you..."):
                try:
                    clues = crossword.clean_word_list(coach.theme_words(typed.strip()))
                    if len(clues) < 6:
                        st.warning("Tulsi couldn't find enough words for that theme. Try something a bit broader.")
                    else:
                        storage.save_custom_theme(crossword.slug(typed), typed.strip(), clues)
                        st.session_state.cw_custom = crossword.slug(typed)
                except coach.CoachError as err:
                    show_error(err)
        saved = storage.load_custom_themes()
        if saved:
            names = list(saved)
            current = st.session_state.get("cw_custom") if st.session_state.get("cw_custom") in saved else names[-1]
            pick = st.radio("Your themes", names, index=names.index(current), horizontal=True,
                            format_func=lambda k: saved[k]["theme"].title(), key="cw_custom_pick")
            puzzle = crossword.custom(saved[pick]["theme"], saved[pick]["clues"], rounds.get(pick, 0))
            if st.button("🔀 Give me a different puzzle", key="cw_new_custom"):
                rounds[pick] = rounds.get(pick, 0) + 1
                st.rerun()

    if puzzle:
        key, title, cw = puzzle
        state = crossword.state(key, cw)
        size = "3.4rem" if state["cols"] <= 10 else "2.9rem"
        st.markdown(f"""<style>
        .cw-grid {{ display:flex; flex-direction:column; gap:.3rem; align-items:center; padding: .6rem 0 .8rem; }}
        .cw-row {{ display:flex; gap:.3rem; }}
        .cw-cell {{ position:relative; width:{size}; height:{size}; border-radius:10px; background:#FFFFFF; border:2px solid #D9C8F2;
                   display:flex; align-items:center; justify-content:center; font-size:1.4rem; font-weight:800; color:#4E2A84; }}
        .cw-empty {{ background:transparent; border-color:transparent; }}
        .cw-filled {{ background:#EEF8F2; border-color:#A8DDBE; color:#1E6B45; animation: cw-pop .35s ease both; }}
        .cw-num {{ position:absolute; top:.1rem; left:.25rem; font-size:.62rem; font-weight:700; color:#9A90AE; }}
        @keyframes cw-pop {{ from {{ transform: scale(.8); }} to {{ transform: none; }} }}
        </style>""", unsafe_allow_html=True)

        grid_col, clue_col = st.columns([5, 4])
        with grid_col:
            st.markdown(f'<div class="soft-panel"><div style="font-weight:800;font-size:1.15rem;color:#4E2A84;text-align:center">'
                        f'{ui.html.escape(title)}</div>{crossword.grid_html(state)}</div>', unsafe_allow_html=True)
            st.markdown(ui.growbar(len(state["solved"]) / len(state["entries"]) * 100), unsafe_allow_html=True)
            st.caption(f"{len(state['solved'])} of {len(state['entries'])} words solved · solved words fill in letters "
                       "that help with the words crossing them")

        with clue_col:
            if state["over"]:
                if st.session_state.pop("cw_just_done", False):
                    st.balloons()
                st.markdown(ui.card("🎉 Crossword solved!", f"{len(state['entries'])} words, {state['hints']} hint(s). Brilliant!"),
                            unsafe_allow_html=True)
                share = crossword.share_text(state, title)
                st.code(share, language=None)
                st.link_button("📲 Share on WhatsApp", games.whatsapp(share), type="primary")
                st.caption("Want another? Pick a theme or type your own above. 🌿")
            else:
                with st.container(key=f"cwbox_{key}"), st.form(f"cw_form_{key}", border=False):
                    answers = {}
                    for direction in ("Across", "Down"):
                        st.markdown(f"**{direction}**")
                        for e in [x for x in state["entries"] if x["dir"] == direction]:
                            if e["id"] in state["solved"]:
                                st.markdown(f"✅ **{e['num']}** · {e['clue']}: **{e['word']}**")
                            else:
                                answers[e["id"]] = st.text_input(f"{e['num']} · {e['clue']} ({len(e['word'])})",
                                                                 key=f"cw_{key}_{e['id']}", max_chars=len(e["word"]))
                    checked = st.form_submit_button("✔️ Check my answers", type="primary")
                if checked:
                    result = crossword.check(key, cw, answers)
                    wrong = [e for e in state["entries"] if result.get(e["id"]) is False]
                    if crossword.state(key, cw)["over"]:
                        st.session_state.cw_just_done = True
                    st.session_state.cw_feedback = (
                        "Not quite: " + ", ".join(f"{e['num']} {e['dir']}" for e in wrong) + ". Try again or reveal a letter 💜"
                        if wrong else ("All correct so far! 🎉" if result else "Type an answer first 🙂"))
                    st.rerun()
                if st.session_state.get("cw_feedback"):
                    st.info(st.session_state.pop("cw_feedback"))
                open_entries = [e for e in state["entries"] if e["id"] not in state["solved"]]
                r1, r2 = st.columns([3, 2], vertical_alignment="bottom")
                stuck = r1.selectbox("Stuck on one?", open_entries, key=f"cw_stuck_{key}",
                                     format_func=lambda e: f"{e['num']} {e['dir']}: {e['clue'][:40]}")
                if r2.button("💡 Reveal a letter", key=f"cw_reveal_{key}"):
                    crossword.reveal(key, stuck["id"])
                    st.rerun()


elif page == "🔥 Exercise":
    today_str = date.today().isoformat()
    goal = int(profile.get("burn_goal") or exercise.DEFAULT_GOAL)
    weight = exercise.body_weight(profile)
    total = exercise.day_total(today_str)
    progress = total["kcal"] / goal if goal else 0

    sun_col, info_col = st.columns([1, 2], vertical_alignment="center")
    with sun_col:
        st.markdown(f'<div style="max-width:16rem;margin:0 auto">{exercise.sun_svg(progress)}</div>', unsafe_allow_html=True)
    with info_col:
        msg = ("☀️ Goal reached! You're shining today!" if progress >= 1 else
               "🌤️ Your sun is waking up. Keep going!" if progress > 0 else "😴 Your sun is still sleepy. Any movement wakes it up!")
        st.markdown(f'<div style="font-size:2.6rem;font-weight:800;color:#2A2140;line-height:1.1">~{total["kcal"]} kcal burned</div>'
                    f'<div style="color:#786E8C;font-size:1.1rem">today · goal {goal} kcal · {total["minutes"]:.0f} min moved</div>'
                    f'<div style="margin:.4rem 0;font-weight:700;color:#4E2A84;font-size:1.15rem">{msg}</div>', unsafe_allow_html=True)
        st.markdown(ui.growbar(progress * 100), unsafe_allow_html=True)

    tab_workouts, tab_move, tab_week = st.tabs(["🏋️‍♀️ Workouts", "➕ Log a single move", "📅 My log"])

    with tab_workouts:
        pick_name, why = exercise.suggested_routine()
        names = list(exercise.ROUTINES)
        st.markdown(ui.card(f"✨ Tulsi suggests today: {pick_name}", ui.html.escape(why)), unsafe_allow_html=True)
        routine = st.radio("Workout", names, index=names.index(pick_name), horizontal=True, label_visibility="collapsed",
                           key="routine_pick")
        minutes_total, best_for, _ = exercise.ROUTINES[routine]
        rows = exercise.routine_breakdown(routine, weight)
        st.caption(f"⏱️ About {minutes_total} min with short rests · 🔥 ~{sum(r['kcal'] for r in rows)} kcal for you · best for: {best_for}")
        with st.form(f"routine_{routine}", border=False):
            ticks = []
            for i, r in enumerate(rows):
                c1, c2 = st.columns([1, 12], vertical_alignment="center")
                ticks.append(c1.checkbox("done", key=f"rt_{routine}_{i}", label_visibility="collapsed"))
                c2.markdown(f'<div class="meal" style="margin:0"><div class="i">{r["emoji"]}</div><div class="m">'
                            f'<b>{r["move"]}: {r["text"]}</b><div>{ui.html.escape(r["tip"])}</div></div>'
                            f'<div class="kc">~{r["kcal"]} kcal</div></div>', unsafe_allow_html=True)
            b1, b2 = st.columns(2)
            log_ticked = b1.form_submit_button("✅ Log the moves I ticked", type="primary")
            log_all = b2.form_submit_button("🏆 I did the whole workout!")
        if log_ticked or log_all:
            chosen = list(range(len(rows))) if log_all else [i for i, t in enumerate(ticks) if t]
            if chosen:
                burned = exercise.log_routine_moves(today_str, routine, chosen, profile)
                st.toast(f"Logged! ~{burned} kcal burned 🔥 Your sun is brighter! (See 📅 My log)")
                st.rerun()
            else:
                st.warning("Tick the moves you did first, or tap 'I did the whole workout'.")
        st.caption("💡 Planks and wall sits don't burn many calories, but they build the strength that helps you burn more every day.")

    with tab_move:
        move_names = [m[0] for m in exercise.MOVES]
        c1, c2, c3 = st.columns([3, 1, 2])
        mv = c1.selectbox("Move", move_names, format_func=lambda n: f"{exercise.MOVE[n][1]} {n}", key="mv_pick")
        unit = exercise.MOVE[mv][3]
        sets = c2.number_input("Sets", 1, 10, 3 if unit != "min" else 1, 1, key="mv_sets")
        label, default, step = {"reps": ("Reps per set", 12, 1), "sec": ("Seconds per set", 60, 5), "min": ("Minutes", 10, 1)}[unit]
        amount = c3.number_input(label, 1, 600, default, step, key=f"mv_amt_{unit}")
        st.caption(f"How to: {exercise.MOVE[mv][5]}")
        est = exercise.move_kcal(mv, sets, amount, weight)
        if st.button(f"➕ Log {exercise.amount_text(mv, sets, amount)} of {mv} (~{est} kcal)", type="primary", key="mv_add"):
            exercise.add_move(today_str, mv, sets, amount, profile)
            st.toast(f"Logged {mv}! ~{est} kcal 🔥")
            st.rerun()
        with st.expander("Did a walk, yoga class, Zumba or sport instead?"):
            names = [n for n, _, _ in exercise.EXERCISES]
            a1, a2 = st.columns([3, 2])
            pick = a1.selectbox("Activity", names, format_func=lambda n: f"{exercise.BY_NAME[n][0]} {n}", key="ex_pick")
            mins = a2.number_input("Minutes", 5, 300, 30, 5, key="ex_min")
            est2 = exercise.kcal(exercise.BY_NAME[pick][1], weight, mins)
            if st.button(f"➕ Add (~{est2} kcal)", key="ex_add"):
                exercise.add(today_str, pick, mins, profile)
                st.rerun()
        with st.expander("🎯 Change my daily burn goal"):
            new_goal = st.number_input("Calories to burn from exercise each day", 50, 1500, goal, 25)
            if new_goal != goal:
                profile["burn_goal"] = int(new_goal)
                storage.save_profile(profile)
                st.rerun()
        st.caption(f"Calories ≈ MET × your weight ({weight:g} kg) × time. METs are standard values for how hard a move is. "
                   "These are estimates: real burn varies with effort and fitness.")

    with tab_week:
        st.markdown("**Today**")
        entries = exercise.day_entries(today_str)
        if not entries:
            st.caption("Nothing yet today. Pick a workout, or log a single move. Even 5 minutes counts! 🌱")
        manual_index = 0
        for e in entries:
            r1, r2 = st.columns([12, 1], vertical_alignment="center")
            detail = e.get("detail") or f"{e['minutes']:.0f} min"
            r1.markdown(f'<div class="meal"><div class="i">{e["emoji"]}</div><div class="m"><b>{ui.html.escape(e["name"])}</b>'
                        f'<div>{ui.html.escape(detail)}{" · Samsung Health" if e["source"] == "samsung" else ""}</div></div>'
                        f'<div class="kc">~{e["kcal"]} kcal</div></div>', unsafe_allow_html=True)
            if e["source"] != "samsung":
                if r2.button("✕", key=f"exdel_{manual_index}", help="Remove"):
                    storage.delete_exercise(today_str, manual_index)
                    st.rerun()
                manual_index += 1
        st.markdown("**This week**")
        week = exercise.week_totals()
        top = max(k for _, _, k in week) or 1
        bars = "".join(
            f'<div style="display:flex;flex-direction:column;align-items:center;gap:.3rem;flex:1">'
            f'<div style="font-weight:700;color:#4E2A84;font-size:.9rem">{k or ""}</div>'
            f'<div style="width:70%;height:{max(4, k / top * 150):.0f}px;border-radius:12px 12px 4px 4px;'
            f'background:linear-gradient(180deg,#FFD23F,#FF9F1C)"></div>'
            f'<div style="color:#786E8C;font-size:.85rem">{date.fromisoformat(d).strftime("%a")}</div></div>'
            for d, m, k in week)
        st.markdown(f'<div class="soft-panel" style="display:flex;align-items:flex-end;gap:.4rem;height:14rem">{bars}</div>',
                    unsafe_allow_html=True)
        st.markdown(ui.tiles([
            ("🔥 THIS WEEK", f"~{sum(k for _, _, k in week):,} kcal", "burned from exercise"),
            ("⏱️ MINUTES", f"{sum(m for _, m, _ in week):.0f}", "of movement"),
            ("☀️ GOAL DAYS", f"{sum(1 for _, _, k in week if k >= goal)} / 7", "days your sun shone fully"),
        ]), unsafe_allow_html=True)


elif page == "🥗 Food & diet":
    tab_plan, tab_scan = st.tabs(["📋 My meal plan", "📸 Scan a meal"])

    with tab_plan:
        t = diet.target(profile)
        dtype = profile.get("diet_type") if profile.get("diet_type") in diet.DIET_TYPES else diet.DIET_TYPES[2]
        new_type = st.radio("I eat", diet.DIET_TYPES, index=diet.DIET_TYPES.index(dtype), horizontal=True, key="diet_type")
        if new_type != dtype:
            profile["diet_type"] = new_type
            storage.save_profile(profile)
            st.rerun()
        swaps = st.session_state.setdefault("diet_swaps", {})
        today_plan = diet.plan(profile, new_type, swaps=swaps)
        eaten = diet.eaten_today()
        plan_kcal = sum(m[1] for m in today_plan.values())
        plan_protein = sum(m[2] for m in today_plan.values())

        st.markdown(ui.tiles([
            ("🎯 DAILY TARGET", f"{t['kcal']:,} kcal", "from food"),
            ("💪 PROTEIN GOAL", f"{t['protein']} g", "about 1.2 g per kg"),
            ("🍽️ EATEN TODAY", f"{eaten['kcal']:,} kcal", f"{max(0, t['kcal'] - eaten['kcal']):,} kcal left"),
        ]), unsafe_allow_html=True)
        st.markdown(ui.growbar(eaten["kcal"] / t["kcal"] * 100), unsafe_allow_html=True)
        st.caption(f"How it's worked out: {t['how']}. It never goes below 1,200 kcal. "
                   "If you feel very hungry, tired or dizzy, eat more and check with your doctor.")

        icons = {"Breakfast": "🌅", "Lunch": "☀️", "Snack": "🍎", "Dinner": "🌙"}
        logged = {m["meal"] for m in storage.load_meals(date.today().isoformat()) if m.get("source") == "diet plan"}
        cols = st.columns(4)
        for col, (slot, (meal, kcal, protein)) in zip(cols, today_plan.items()):
            with col.container(border=True):
                st.markdown(f'<div style="font-size:2rem">{icons[slot]}</div><div style="font-weight:800;color:#4E2A84">{slot}</div>'
                            f'<div style="font-weight:600;margin:.3rem 0;min-height:4.5rem">{ui.html.escape(meal)}</div>'
                            f'<div style="color:#786E8C">≈ {kcal} kcal · {protein} g protein</div>', unsafe_allow_html=True)
                if slot in logged:
                    st.success("Eaten ✅")
                else:
                    if st.button("✅ I ate this", key=f"ate_{slot}", type="primary"):
                        storage.add_meal(date.today().isoformat(), {
                            "meal": slot, "calories": kcal, "source": "diet plan",
                            "items": [{"name": meal, "portion": "as planned", "calories": kcal, "protein_g": protein,
                                       "carbs_g": 0, "fat_g": 0, "fibre_g": 0, "servings": 1}]})
                        st.toast(f"{slot} logged! 🌱")
                        st.rerun()
                    if st.button("🔀 Swap", key=f"swap_{slot}"):
                        swaps[slot] = swaps.get(slot, 0) + 1
                        st.rerun()
        st.caption(f"Today's plan: ≈ {plan_kcal:,} kcal and {plan_protein} g protein.")
        if plan_protein < t["protein"] - 10:
            st.markdown(ui.card("💪 Easy protein boosts",
                                f"This plan gives about {plan_protein} g protein; your goal is {t['protein']} g. Add one or two: "
                                "1 boiled egg (+6 g) · ½ cup thick curd (+5 g) · 50 g paneer (+9 g) · ½ cup sprouts (+7 g) · "
                                "1 glass milk (+8 g) · 30 g roasted chana (+6 g)"), unsafe_allow_html=True)
        st.markdown(ui.card("🍽️ The PCOS plate, for any meal",
                            "Half the plate vegetables · a quarter protein (dal, eggs, fish, paneer, chicken) · a quarter "
                            "slow carbs (matta rice, millets, chapati) · a spoon of healthy fat. Eat protein and veg first, carbs last."),
                    unsafe_allow_html=True)
        st.button("💬 Ask Tulsi for a full 7-day plan", on_click=go_to_chat, args=("🥗 Weekly meal plan",))

    with tab_scan:

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
                            "name": "Food", "portion": "Portion (in photo)", "calories": "Calories",
                            "protein_g": "Protein (g)", "carbs_g": "Carbs (g)",
                            "fat_g": "Fat (g)", "fibre_g": "Fibre (g)",
                            "servings": "Servings eaten (1 = as in photo)",
                        },
                    )
                # what you actually ate = photo estimate x servings, plus a check that the numbers add up
                eaten = []
                for item in edited:
                    row = food.scaled(item)
                    warn = food.macro_check(item)
                    if warn:
                        row["warn"] = warn
                    eaten.append(row)
                total = sum(int(float(i.get("calories") or 0)) for i in eaten)
                sums = {k: sum(float(i.get(k) or 0) for i in eaten) for k in ("protein_g", "carbs_g", "fibre_g")}
                summary.markdown(ui.tiles([
                    ("🔥 CALORIES", f"{total}", "kcal (estimate)"),
                    ("💪 PROTEIN", f"{sums['protein_g']:.0f} g", "keeps you full"),
                    ("🌾 CARBS", f"{sums['carbs_g']:.0f} g", "energy"),
                    ("🥦 FIBRE", f"{sums['fibre_g']:.0f} g", "great for PCOS"),
                ]), unsafe_allow_html=True)
                cards.markdown(ui.food_cards(eaten), unsafe_allow_html=True)
                if scan.get("tip"):
                    st.markdown(f'<div class="tip">💡 <b>Tulsi\'s tip:</b> {ui.html.escape(scan["tip"])}</div>',
                                unsafe_allow_html=True)
                st.caption(f"Estimates from a photo (confidence: {scan['confidence']}). They're a guide, not exact numbers.")
                if st.button(f"✅ Save to {meal_name}", type="primary"):
                    storage.add_meal(day, {"meal": meal_name, "items": [{k: v for k, v in i.items() if k != "warn"} for i in eaten],
                                           "calories": total})
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

        def chart(name, title, unit, how="mean", per_period=True, decimals=0, where=st, data=None, trend=None):
            data = col(name) if data is None else data
            if data.empty:
                return
            if per_period:
                data = getattr(data.resample(group), how)().dropna()
                sub = f"{'Total' if how == 'sum' else 'Average'} per {label} · hover a dot for details"
            else:
                sub = ("Bold line = your 7-day average (the number that matters) · faint dots = each weigh-in"
                       if trend else "Your whole journey · hover a dot for details")
            points = list(zip(data.index.to_pydatetime(), data.values))
            body = ui.line_chart_svg(points, unit, decimals, wide=where is st, trend=trend)
            if len(points) < 2:
                body += '<div class="st">Not enough data yet for a line. Keep logging! 🌱</div>'
            where.markdown(ui.chart_card(title, sub, body), unsafe_allow_html=True)

        trend = [(pd.Timestamp(d).to_pydatetime(), v) for d, v in journey.weight_trend(rows)]
        why = journey.scale_reasons(rows)
        if why:
            change = (f" Your 7-day average is {why['trend_now']:g} kg"
                      + (f" ({why['trend_change']:+g} kg vs a week ago)." if why["trend_change"] is not None else "."))
            st.markdown(ui.card(f"🤍 The scale went up {why['up_by']:g} kg. Here's what's likely going on",
                                "<br>".join(ui.html.escape(r) for r in why["reasons"]) + "<br><b>" + change + "</b>"),
                        unsafe_allow_html=True)
        chart("weight_kg", "⚖️ Weight", "kg", per_period=False, decimals=1, data=all_weights, trend=trend or None)
        # the other charts sit side by side in pairs; only the ones with data are shown, so there are no gaps
        specs = [("workout_min", "🚶‍♀️ Walking minutes", "min", "sum", 0),
                 ("workout_km", "📍 Distance walked", "km", "sum", 1),
                 ("steps", "👟 Daily steps", "steps", "mean", 0),
                 ("sleep_hours", "😴 Sleep", "h", "mean", 1),
                 ("calories", "🍽️ Calories eaten", "kcal", "mean", 0),
                 ("water", "💧 Water", "glasses", "mean", 1)]
        specs = [sp for sp in specs if not col(sp[0]).empty]
        for i in range(0, len(specs), 2):
            pair = specs[i:i + 2]
            cols = st.columns(2) if len(pair) == 2 else [st]
            for where, (name, title, unit, how, dec) in zip(cols, pair):
                chart(name, title, unit, how=how, decimals=dec, where=where)

        st.caption("Steps only count while your phone is with you, so walking sessions show your effort best. "
                   "Quieter weeks are part of the journey too. 💜")
        with st.expander("📋 See the data as a table"):
            st.dataframe(df.sort_index(ascending=False))

    st.download_button("🩺 Download a health summary for my doctor (PDF)", cards.doctor_report(profile),
                       file_name=f"health_summary_{date.today().isoformat()}.pdf", mime="application/pdf")

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
    g = _growth
    left, right = st.columns([1, 1])
    with left:
        g_glasses = storage.water_today(date.today().isoformat())
        st.markdown(garden.tulsi_img(g["stage"], "16rem", fresh=g_glasses >= 8,
                                     watering=st.session_state.pop("watered", False)), unsafe_allow_html=True)
        st.button(f"💧 Water Tulsi ({g_glasses}/8 glasses today)", key="garden_water",
                  on_click=water_tulsi, args=(date.today().isoformat(),))
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
    st.subheader("📤 Share my progress")
    st.caption("Make a pretty card to share on WhatsApp or Instagram. You choose what's on it.")
    s1, s2, s3 = st.columns([2, 2, 3])
    show_weight = s1.toggle("Show kg lost", value=False, help="Off by default. Your weight is your business.")
    show_win = s2.toggle("Show my latest win", value=True)
    card_png = cards.share_card(profile, show_weight=show_weight, show_win=show_win)
    with s3:
        st.download_button("⬇️ Download my share card", card_png, file_name="my_fitbuddy_progress.png",
                           mime="image/png", type="primary")
    with st.expander("👀 Preview my card"):
        st.image(card_png, width=360)

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
        c_plus, c_form, c_mic = st.columns([1, 12, 1], vertical_alignment="center", gap="small")

        with c_plus.popover("✨", help="Plans & ideas"):
            st.markdown("**Plans for you**")
            for label in ["🥗 Weekly meal plan", "🍱 Quick lunchbox ideas", "🛒 Grocery list", "🏠 Home workout plan"]:
                if st.button(label, key=f"qa_{label}"):
                    st.session_state.pending = label
            st.markdown("**Quick help**")
            for label in ["🆘 Craving SOS", "⏱️ 10-min home workout", "😔 I'm feeling unmotivated",
                          "😴 Tips for better sleep", "📬 My weekly report"]:
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
        elif prompt.startswith("🆘 Craving SOS"):
            kind, note = st.session_state.pop("craving", ("", ""))
            msg["ask"] = coach.craving_request(kind, note)
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

    st.download_button("🩺 Download a health summary for my doctor (PDF)", cards.doctor_report(profile),
                       file_name=f"health_summary_{date.today().isoformat()}.pdf", mime="application/pdf",
                       key="doc_report_profile")

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
