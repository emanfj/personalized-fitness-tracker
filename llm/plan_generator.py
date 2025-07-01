#!/usr/bin/env python3
"""
plan_generator.py — generate personalized workout and nutrition plans
using local Ollama llama3.2:3b model.
"""

import os
import json
import requests

# ─── Configuration ─────────────────────────────────────────────────────────────
OLLAMA_API = os.getenv("OLLAMA_API", "http://127.0.0.1:11435/api/generate")
DEFAULT_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2:3b")

# ─── Core LLM Caller ────────────────────────────────────────────────────────────
def call_llm(prompt: str, model: str = DEFAULT_MODEL) -> str:
    """
    Send `prompt` to your local Ollama LLM and return the raw string response.
    """
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": 0.7,
            "num_ctx": 2048
        }
    }
    resp = requests.post(OLLAMA_API, json=payload)
    resp.raise_for_status()
    return resp.json()["response"]

# ─── Prompt Builders ───────────────────────────────────────────────────────────
def build_workout_prompt(ctx: dict) -> str:
    """
    Craft a detailed prompt for generating a 7-day personalized workout plan.
    """
    return f"""
You are a world-class personal trainer. Design a **7-day workout program** tailored to the following user profile:

User Profile:
- Age: {ctx['age']} years
- Gender: {ctx.get('gender', 'unspecified')}
- Height: {ctx['height_cm']} cm
- Weight: {ctx['weight_kg']} kg
- Fitness Level: {ctx['fitness_level']}
- Primary Goal: {ctx['goal']!r}
- Available Time per Day: {ctx['time_available']} minutes
- Average Daily Steps (last 7 days): {ctx['recent_steps_avg']}

Requirements:
1. For each day (Day 1–7), list:
    - **Workout Type** (e.g. Upper Body, HIIT, Active Rest)
    - **Exercises**: name, sets × reps (or duration), rest between sets
    - **Estimated Total Time** in minutes
2. Vary intensity and muscle groups to allow recovery.
3. Include at least one active-recovery or mobility day.

Respond **only** with JSON, using this schema:

```json
[
  {{
    "day": 1,
    "type": "Upper Body",
    "exercises": [
      {{ "name": "Push-ups", "sets": 3, "reps": 12, "rest_sec": 60 }},
      // ...
    ],
    "total_time": 30
  }},
  // ...
]
```
""".strip()

def build_nutrition_prompt(ctx: dict) -> str:
    """
    Craft a detailed prompt for generating a 3-day personalized meal plan.
    """
    return f"""
You are a registered dietitian. Create a 3-day meal plan (breakfast, lunch, dinner, optional snacks) for the following user:

User Profile:
Age: {ctx['age']} years
Gender: {ctx.get('gender', 'unspecified')}
Height: {ctx['height_cm']} cm
Weight: {ctx['weight_kg']} kg
Fitness Goal: {ctx['goal']!r}
Estimated Daily Caloric Needs: {ctx.get('calorie_target', 'calculate based on profile')}
Activity Level: {ctx['fitness_level']}, ~{ctx['recent_steps_avg']} steps/day

Requirements:
Provide meals with:
Dish Name
Portion Size
Approximate Calories and Macros (P/C/F)
Balance macronutrients to support the user’s goal.
Keep ingredients simple and accessible.

Respond only with JSON, using this schema:
```json
{{
    "day1": {{ "breakfast": {{}}, "lunch": {{}}, "dinner": {{}}, "snacks": [] }},
    "day2": {{}},
    "day3": {{}}
}}
```
""".strip()

def generate_workout_plan(ctx: dict, model: str = DEFAULT_MODEL) -> list:
    """
    Generate and parse a 7-day workout plan.
    """
    raw = call_llm(build_workout_prompt(ctx), model=model)
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        raise ValueError(f"Failed to parse workout JSON:\n{raw}")

def generate_nutrition_plan(ctx: dict, model: str = DEFAULT_MODEL) -> dict:
    """
    Generate and parse a 3-day meal plan.
    """
    raw = call_llm(build_nutrition_prompt(ctx), model=model)
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        raise ValueError(f"Failed to parse nutrition JSON:\n{raw}")

if __name__ == "__main__":
    example_ctx = {
        "age": 30,
        "gender": "Female",
        "height_cm": 165,
        "weight_kg": 60,
        "fitness_level": "intermediate",
        "goal": "build muscle",
        "time_available": 45,
        "recent_steps_avg": 7000,
        "calorie_target": 2200,
    }
    workout_plan = generate_workout_plan(example_ctx)
    meal_plan = generate_nutrition_plan(example_ctx)

    print(json.dumps({
        "workout_plan": workout_plan,
        "meal_plan": meal_plan
    }, indent=2))
