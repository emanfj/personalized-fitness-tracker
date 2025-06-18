# plan_generator.py

import json
import requests

OLLAMA_API = "http://localhost:11434/api/generate"

def call_llm(prompt: str, model: str = "phi3:mini") -> str:
    """
    Send `prompt` to your local Ollama LLM and return the raw string response.
    """
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": {"temperature": 0.7, "num_ctx": 1024}
    }
    resp = requests.post(OLLAMA_API, json=payload)
    resp.raise_for_status()
    return resp.json()["response"]

def build_workout_prompt(ctx: dict) -> str:
    """
    Craft a detailed prompt for generating a 7-day personalized workout plan.
    """
    return f"""
You are a world-class personal trainer. Design a **7-day workout program** tailored to the following user profile:

User Profile:
Age: {ctx['age']} years
Gender: {ctx.get('gender', 'unspecified')}
Height: {ctx['height_cm']} cm
Weight: {ctx['weight_kg']} kg
Fitness Level: {ctx['fitness_level']}
Primary Goal: {ctx['goal']} # e.g. "build muscle", "lose fat", "improve endurance"
Available Time per Day: {ctx['time_available']} minutes
Average Daily Steps (last 7 days): {ctx['recent_steps_avg']}
Requirements:
1. For each day (Day 1–7), list:
   - **Workout Type** (e.g. Upper Body, HIIT, Active Rest)
   - **Exercises**: name, sets × reps (or duration), rest between sets
   - **Estimated Total Time** in minutes
2. Vary intensity and muscle groups to allow recovery.
3. Include at least one active-recovery or mobility day.
4. Format your answer as **JSON**, with keys: `"day"`, `"type"`, `"exercises"`, `"total_time"`.
"""

def build_nutrition_prompt(ctx: dict) -> str:
    """
    Craft a detailed prompt for generating a 3-day personalized meal plan.
    """
    return f"""
You are a registered dietitian. Create a **3-day meal plan** (breakfast, lunch, dinner, optional snacks) for the same user:

User Profile:
Age: {ctx['age']} years
Gender: {ctx.get('gender', 'unspecified')}
Height: {ctx['height_cm']} cm
Weight: {ctx['weight_kg']} kg
Fitness Goal: {ctx['goal']}
Estimated Daily Caloric Needs: {ctx.get('calorie_target', 'calculate based on profile')}
Activity Level: {ctx['fitness_level']}, ~{ctx['recent_steps_avg']} steps/day

Requirements:
1. Provide meals with:
   - **Dish Name**  
   - **Portion Size**  
   - **Approximate Calories** and **Macros** (P/C/F)
2. Balance protein, carbs, fat to support the user’s goal.
3. Keep ingredients simple and accessible.
4. Output **strictly JSON** with top-level key `"day1"`, `"day2"`, `"day3"`, each containing keys `"breakfast"`, `"lunch"`, `"dinner"`, `"snacks"`.
"""

def generate_workout_plan(ctx: dict, model: str = "phi3:mini") -> dict:
    raw = call_llm(build_workout_prompt(ctx), model=model)
    return json.loads(raw)

def generate_nutrition_plan(ctx: dict, model: str = "phi3:mini") -> dict:
    raw = call_llm(build_nutrition_prompt(ctx), model=model)
    return json.loads(raw)
