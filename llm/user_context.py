# llm/user_context.py

from datetime import datetime, timezone, timedelta
from pymongo import MongoClient

# connect once at import time
client = MongoClient("mongodb://localhost:27017")
db     = client.fitness_tracker

def build_context(user_id: str) -> dict | None:
    """
    Fetch user profile + recent activity from Mongo, build the context dict
    that your prompt functions expect. Return None if user not found.
    """
    user = db.users.find_one({"user_id": user_id})
    if not user:
        return None

    # 1) compute age
    dob       = datetime.fromisoformat(user["date_of_birth"])
    today     = datetime.now(timezone.utc)
    age       = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))

    # 2) basic profile
    height_cm      = user.get("height_cm")
    weight_kg      = user.get("weight_kg_start")  # or current weight if you store that
    gender         = user.get("gender", "unspecified")
    fitness_level  = user.get("fitness_level", "moderate")
    goal           = user.get("goal", "maintain weight")
    time_available = user.get("time_available_minutes", 30)

    # 3) average daily steps over last 7 days
    seven_days_ago = today - timedelta(days=7)
    pipeline = [
        {"$match": {
            "user_id": user_id,
            "event_ts": {"$gte": seven_days_ago.isoformat()}
        }},
        {"$group": {
            "_id": None,
            "total_steps": {"$sum": "$step_increment"}
        }}
    ]
    agg = list(db.fitness_events.aggregate(pipeline))
    total_steps = agg[0]["total_steps"] if agg else 0
    recent_steps_avg = total_steps / 7

    # 4) optional calorie target (if you’ve stored one)
    calorie_target = user.get("calorie_target")

    return {
        "age": int(age),
        "gender": gender,
        "height_cm": height_cm,
        "weight_kg": weight_kg,
        "fitness_level": fitness_level,
        "goal": goal,
        "time_available": time_available,
        "recent_steps_avg": int(recent_steps_avg),
        "calorie_target": calorie_target,
    }
