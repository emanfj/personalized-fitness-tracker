import os
import json
import re
import requests
from datetime import datetime
from typing import Any, List, Optional

from pydantic import BaseModel, ValidationError
from pymongo import MongoClient

OLLAMA_API = os.getenv("OLLAMA_API", "http://127.0.0.1:11434/api/generate")
MODEL = os.getenv("OLLAMA_MODEL", "llama3.2:latest")
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
DB_NAME = "fitness_tracker"

class Exercise(BaseModel):
    name: str
    sets: int
    reps: Optional[int] = None
    duration_min: Optional[float] = None
    rest_sec: Optional[int] = None

class DayPlan(BaseModel):
    day: int
    type: str
    exercises: List[Exercise]
    total_time: int

def log_plan(user_id: Any, plan_type: str, prompt: str, response: str, valid: bool, error: Optional[str] = None):
    client = MongoClient(MONGO_URI)
    db = client[DB_NAME]
    db.plans.insert_one({
        "user_id": user_id,
        "type": plan_type,
        "time": datetime.utcnow(),
        "prompt": prompt,
        "response": response,
        "valid": valid,
        "error": error,
    })

def build_workout_prompt(ctx: dict) -> str:
    notes = []
    soreness = ctx.get("recent_soreness")
    if isinstance(soreness, (int, float)) and soreness >= 3:
        notes.append("add more rest days")
    if ctx.get("favorite_activity"):
        notes.append(f"include {ctx['favorite_activity']}")
    header = (
        f"User: age={ctx['age']}, weight={ctx['weight_kg']}, "
        f"goal={ctx['goal']}, time/day={ctx['time_available']}min, "
        f"calories={ctx.get('calorie_target')}\n"
    )
    body = "\n".join(notes)
    schema = (
        "Return only valid JSON (no markdown or extra text). "
        "Use numeric types: 'day' as int (1=Monday…7=Sunday), 'reps' as int, 'duration_min' as float, 'rest_sec' as int. "
        "Output a list of 7 items, each with: day, type, exercises (list of {name, sets, reps, duration_min, rest_sec}), total_time."
    )
    return header + body + "\n" + schema


def build_nutrition_prompt(ctx: dict) -> str:
    header = (
        f"User: age={ctx['age']}, weight={ctx['weight_kg']}, "
        f"goal={ctx['goal']}, calories={ctx.get('calorie_target')}\n"
    )
    schema = (
        "Return only valid JSON (no markdown or extra text). "
        "Output an object with day1-day3, each containing food listed for each meal: breakfast, lunch, dinner. Snacks can be optionally generated." \
        "Do not leave any meals empty, and ensure each meal has at least one item. "
        "Each item should have: name, calories, protein, carbs, fat."
    )
    return header + schema

def call_llm(prompt: str) -> str:
    payload = {"model": MODEL, "prompt": prompt, "stream": False}
    resp = requests.post(OLLAMA_API, json=payload)
    resp.raise_for_status()
    return resp.json().get("response", "")

def clean_json(raw: str) -> str:
    raw = raw.strip("`\n")
    m = re.search(r"(\{.*\}|\[.*\])", raw, re.S)
    return m.group(1) if m else raw

_DAY_MAP = {
    "monday":1, "tuesday":2, "wednesday":3,
    "thursday":4, "friday":5, "saturday":6, "sunday":7
}

def normalize_workout_data(data: List[dict]) -> List[dict]:
    normalized = []
    for day_item in data:
        # normalize day
        d = day_item.get('day')
        if isinstance(d, str):
            lower = d.strip().lower()
            if lower in _DAY_MAP:
                day_item['day'] = _DAY_MAP[lower]
            else:
                nums = re.search(r'\d+', d)
                day_item['day'] = int(nums.group()) if nums else 0
        # normalize exercises
        exs = []
        for ex in day_item.get('exercises', []):
            name = ex.get('name')
            sets = ex.get('sets')
            if isinstance(sets, str) and sets.isdigit():
                sets = int(sets)

            reps = ex.get('reps')
            if isinstance(reps, str):
                m = re.search(r'\d+', reps)
                reps = int(m.group()) if m else None

            duration = ex.get('duration_min') if ex.get('duration_min') is not None else ex.get('duration')
            if isinstance(duration, str):
                m = re.search(r'\d+(?:\.\d+)?', duration)
                duration = float(m.group()) if m else None

            rest = ex.get('rest_sec')
            if rest is None and 'rest' in ex:
                rs = ex.get('rest')
                if isinstance(rs, str):
                    m = re.search(r'\d+', rs)
                    rest = int(m.group()) if m else None
                else:
                    rest = rs

            exs.append({
                'name': name,
                'sets': sets,
                'reps': reps,
                'duration_min': duration,
                'rest_sec': rest
            })
        day_item['exercises'] = exs
        normalized.append(day_item)
    return normalized

def generate_plan(user_id: Any, ctx: dict, plan_type: str) -> Any:
    prompt = build_workout_prompt(ctx) if plan_type == 'workout' else build_nutrition_prompt(ctx)
    raw = call_llm(prompt)
    

    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        cleaned = clean_json(raw)
        data = json.loads(cleaned)

    if plan_type == 'workout':
        data = normalize_workout_data(data)

    try:
        if plan_type == 'workout':
            plans = [DayPlan(**item) for item in data]
        else:
            plans = data
        log_plan(user_id, plan_type, prompt, raw, True)
        return plans

    except ValidationError as err:
        log_plan(user_id, plan_type, prompt, raw, False, str(err))
        raise
