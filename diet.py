"""
diet.py - a specific, PCOS-friendly daily meal plan with real portions.

1. Your daily calorie target:
     BMR (Mifflin-St Jeor, for women) = 10 x weight(kg) + 6.25 x height(cm) - 5 x age - 161
     Daily needs ≈ BMR x 1.375 (lightly active)
     Target = daily needs - 400 kcal (a gentle deficit for steady loss), never below 1200 kcal.
   If your doctor or dietitian gave you a target, the one in your profile is used instead.
2. Protein goal: about 1.2 g per kg of body weight (protein keeps you full and protects muscle).
3. Each meal slot gets a share of the target (breakfast 25%, lunch 35%, snack 10%, dinner 30%), and the plan
   picks a meal close to that size from the lists below. Calories are approximate for the portions written.
"""

import random
from datetime import date

import journey
import storage

SPLIT = {"Breakfast": 0.25, "Lunch": 0.35, "Snack": 0.10, "Dinner": 0.30}
DIET_TYPES = ["🥦 Vegetarian", "🥚 Eggs + veg", "🐟 Non-veg (fish, chicken, eggs)"]

# (meal, kcal, protein g, needs: "veg" | "egg" | "meat")
MEALS = {
    "Breakfast": [
        ("2 ragi dosa + ½ cup sambar + 1 tbsp coconut chutney", 330, 10, "veg"),
        ("Puttu (½ cup) + kadala curry (¾ cup)", 380, 14, "veg"),
        ("2 moong dal chilla + mint chutney + ½ cup curd", 320, 18, "veg"),
        ("2 besan chilla with veggies + ½ cup curd", 330, 16, "veg"),
        ("Overnight oats: ½ cup oats, milk, 1 tsp chia, ½ apple", 330, 13, "veg"),
        ("Paneer bhurji (75 g) + 1 small whole wheat roti", 340, 18, "veg"),
        ("Sprouts chaat (1 cup) + 1 glass buttermilk", 250, 14, "veg"),
        ("Vegetable oats upma (1 cup) + 1 boiled egg", 320, 14, "egg"),
        ("2-egg omelette with onion, tomato & spinach + 1 whole wheat toast", 300, 17, "egg"),
        ("2 idli + ½ cup sambar + 1 boiled egg", 300, 14, "egg"),
        ("2 appam + egg curry (1 egg)", 380, 13, "egg"),
    ],
    "Lunch": [
        ("2 chapatis + dal (1 cup) + mixed veg sabzi (1 cup) + salad", 480, 18, "veg"),
        ("¾ cup foxtail millet rice + sambar (1 cup) + avial (¾ cup)", 470, 14, "veg"),
        ("2 chapatis + paneer curry (75 g) + salad", 500, 22, "veg"),
        ("Rajma (1 cup) + ½ cup rice + salad", 480, 18, "veg"),
        ("Curd rice (1 cup) with veggies + sprouts thoran (1 cup)", 450, 18, "veg"),
        ("½ cup matta rice + moru curry + cabbage thoran + cherupayar (½ cup)", 460, 16, "veg"),
        ("Egg curry (2 eggs) + 2 chapatis + salad", 500, 22, "egg"),
        ("½ cup matta rice + fish curry (1 piece) + cabbage thoran (1 cup) + ½ cup curd", 520, 30, "meat"),
        ("½ cup matta rice + chicken curry (100 g) + beans thoran + cucumber salad", 540, 32, "meat"),
    ],
    "Snack": [
        ("1 apple + 8 almonds", 150, 4, "veg"),
        ("Roasted chana (30 g)", 120, 6, "veg"),
        ("1 glass buttermilk + 15 g peanuts", 130, 6, "veg"),
        ("Roasted makhana (1 cup)", 100, 3, "veg"),
        ("1 guava + 4 walnut halves", 140, 4, "veg"),
        ("½ cup thick curd with 1 tsp seeds", 120, 8, "veg"),
        ("½ cup sprouts with lemon and onion", 100, 7, "veg"),
        ("1 boiled egg + cucumber slices", 90, 6, "egg"),
    ],
    "Dinner": [
        ("2 chapatis + palak dal (1 cup) + salad", 420, 18, "veg"),
        ("Vegetable soup (1 bowl) + paneer tikka (80 g)", 350, 20, "veg"),
        ("Moong dal khichdi (1 cup) + ½ cup curd + salad", 400, 16, "veg"),
        ("Kanji (1 cup) + cherupayar curry (¾ cup) + beans thoran", 380, 15, "veg"),
        ("Paneer & veggie stir-fry + ½ cup millet rice", 400, 20, "veg"),
        ("2-egg bhurji + 1 chapati + salad", 380, 18, "egg"),
        ("Pan-cooked fish (1 piece) + sautéed veggies (1 cup) + 1 chapati", 400, 30, "meat"),
        ("Chicken stew (100 g) + 1 appam", 420, 28, "meat"),
    ],
}
ALLOWED = {"🥦 Vegetarian": {"veg"}, "🥚 Eggs + veg": {"veg", "egg"},
           "🐟 Non-veg (fish, chicken, eggs)": {"veg", "egg", "meat"}}


def target(profile: dict) -> dict:
    """Daily calorie target and protein goal, with how they were worked out."""
    w = journey.weights(journey.all_days())
    weight = float(w[-1][1] if w else profile.get("current_weight_kg") or 0)
    height, age = float(profile.get("height_cm") or 0), int(profile.get("age") or 0)
    if profile.get("calorie_target"):
        kcal, how = int(profile["calorie_target"]), "the target in your health profile (from your doctor or dietitian)"
    elif weight and height and age:
        bmr = 10 * weight + 6.25 * height - 5 * age - 161
        needs = bmr * 1.375
        kcal = max(1200, int(round((needs - 400) / 50) * 50))
        how = f"your body uses about {needs:,.0f} kcal a day; a gentle 400 kcal deficit gives steady, healthy loss"
    else:
        kcal, how = 1500, "a general starting point. Add your height, weight and age in 🩺 Health profile for your own number"
    protein = round(1.2 * (weight or 60))
    return {"kcal": kcal, "protein": protein, "how": how, "weight": weight}


def plan(profile: dict, diet_type: str, day: date | None = None, swaps: dict | None = None) -> dict:
    """{slot: (meal, kcal, protein)} for the day. Same plan all day; tapping Swap moves a slot to the next option."""
    day = day or date.today()
    swaps = swaps or {}
    goal = target(profile)["kcal"]
    allowed = ALLOWED.get(diet_type, ALLOWED[DIET_TYPES[2]])
    out = {}
    for slot, share in SPLIT.items():
        options = [m for m in MEALS[slot] if m[3] in allowed]
        options.sort(key=lambda m: abs(m[1] - goal * share))
        close = options[:4] if len(options) >= 4 else options  # the meals closest to the right size
        random.Random(f"{day.isoformat()}-{slot}").shuffle(close)
        meal = close[swaps.get(slot, 0) % len(close)]
        out[slot] = meal[:3]
    return out


def eaten_today(day: str | None = None) -> dict:
    day = day or date.today().isoformat()
    meals = storage.load_meals(day)
    kcal = sum(int(m.get("calories", 0)) for m in meals)
    protein = sum(float(i.get("protein_g") or 0) for m in meals for i in m.get("items", []))
    return {"kcal": kcal, "protein": round(protein)}
