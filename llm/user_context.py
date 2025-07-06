# llm/user_context.py

from datetime import datetime, timezone, timedelta
from motor.motor_asyncio import AsyncIOMotorClient

MONGO_URI = "mongodb://localhost:27017"
DB_NAME = "fitness_tracker"

# Helper for motor connection
_client = None
def get_db():
    global _client
    if _client is None:
        _client = AsyncIOMotorClient(MONGO_URI)
    return _client[DB_NAME]

async def build_context(user_id: str) -> dict | None:
    db = get_db()
    user = await db.users.find_one({"user_id": user_id})
    if not user:
        return None

    today = datetime.now(timezone.utc)
    dob = datetime.fromisoformat(user["date_of_birth"])
    age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))

    height_cm = user.get("height_cm")
    weight_kg = user.get("weight_kg_start")
    gender = user.get("gender", "unspecified")
    fitness_level = user.get("fitness_level", "moderate")
    goal = user.get("goal", "maintain weight")
    time_available = user.get("time_available_minutes", 30)
    calorie_target = user.get("calorie_target")

    # Steps in last 7 days
    seven_days_ago = today - timedelta(days=7)
    pipeline_steps = [
        {"$match": {"user_id": user_id, "event_ts": {"$gte": seven_days_ago.isoformat()}}},
        {"$group": {"_id": None, "total_steps": {"$sum": "$step_increment"}}}
    ]
    agg = [doc async for doc in db.fitness_events.aggregate(pipeline_steps)]
    total_steps = agg[0]["total_steps"] if agg else 0
    recent_steps_avg = total_steps / 7

    # Last feedback
    feedback = await db.feedback.find_one({"user_id": user_id}, sort=[("event_ts", -1)])
    mood = feedback.get("mood") if feedback else None
    exertion = feedback.get("perceived_exertion") if feedback else None
    soreness = feedback.get("soreness_level") if feedback else None

    # Favorite activity type in last 7 days
    pipeline_fav = [
        {"$match": {"user_id": user_id, "event_ts": {"$gte": seven_days_ago.isoformat()}}},
        {"$group": {"_id": "$activity_type", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
        {"$limit": 1}
    ]
    agg2 = [doc async for doc in db.fitness_events.aggregate(pipeline_fav)]
    favorite_activity = agg2[0]["_id"] if agg2 else None

    # Last 3 days nutrition logs for macro trend (optional)
    three_days_ago = today - timedelta(days=3)
    recent_nutrition = [
        n async for n in db.nutrition.find({"user_id": user_id, "log_ts": {"$gte": three_days_ago.isoformat()}})
    ]

    return {
        "user_id": user_id,
        "age": int(age),
        "gender": gender,
        "height_cm": height_cm,
        "weight_kg": weight_kg,
        "fitness_level": fitness_level,
        "goal": goal,
        "time_available": time_available,
        "recent_steps_avg": int(recent_steps_avg),
        "calorie_target": calorie_target,
        "recent_mood": mood,
        "recent_exertion": exertion,
        "recent_soreness": soreness,
        "favorite_activity": favorite_activity,
        "recent_nutrition": recent_nutrition,
    }
