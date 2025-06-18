# user_context.py

import json
import redis
from pymongo import MongoClient
from datetime import datetime, timedelta

redis_client = redis.Redis(host="localhost", port=6379, db=0)
mongo       = MongoClient("mongodb://localhost:27017").fitness_tracker

def load_user_context(user_id: str) -> dict:
    cache_key = f"user_ctx:{user_id}"
    cached = redis_client.get(cache_key)
    if cached:
        return json.loads(cached)

    #fetch from MongoDB
    users = mongo.users.find_one({"user_id": user_id})
    steps = mongo.fitness_events.count_documents({
        "user_id": user_id,
        "event_ts": {"$gte": datetime.utcnow() - timedelta(days=7)}
    })
    avg_steps = steps / 7

    ctx = {
        "age": users["age"],
        "goal": users.get("goal", "general_fitness"),
        "height_cm": users["height_cm"],
        "weight_kg": users["weight_kg_start"],
        "avg_steps_last_7d": avg_steps,
        "avg_hr_last_7d": mongo.fitness_events.aggregate([
            {"$match": {"user_id": user_id}},
            {"$group": {"_id": None, "avg": {"$avg": "$heart_rate_bpm"}}}
        ]).next().get("avg", 70),
    }

    # cache 1 h
    redis_client.setex(cache_key, 3600, json.dumps(ctx))
    return ctx
