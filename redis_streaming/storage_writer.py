#!/usr/bin/env python
"""
Redis → MongoDB writer
  • tails your six fitness streams
  • writes users/devices once
  • buffers fitness_events in 60s windows (bulk insert)
  • writes sleep/nutrition immediately
  • writes feedback once/day (polled every 60s)
"""
import os
import threading
import time
import redis
from pymongo import MongoClient

# ─── Redis config ─────────────────────────────────────────────────────────────
REDIS_HOST = os.getenv("REDIS_HOST", "127.0.0.1")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=0, decode_responses=True)

# ─── Mongo config ─────────────────────────────────────────────────────────────
MONGO_URI = os.getenv("MONGO_URI", "mongodb://127.0.0.1:27017")
mongo     = MongoClient(MONGO_URI)
db        = mongo.fitness_tracker
col_users     = db.users
col_devices   = db.devices
col_fitness   = db.fitness_events
col_sleep     = db.sleep_sessions
col_nutrition = db.nutrition_logs
col_feedback  = db.feedback_events

def load_static(stream, coll):
    last_id = "0-0"
    while True:
        resp = r.xread({stream: last_id}, count=100, block=2000)
        if not resp:
            break
        for _, entries in resp:
            for eid, data in entries:
                data["_id"] = data.get("user_id") or data.get("device_id") or eid
                coll.replace_one({"_id": data["_id"]}, data, upsert=True)
                last_id = eid

def fitness_writer():
    buffer = []
    last_id = "0-0"
    fitness_writer.last_flush = time.time()
    while True:
        resp = r.xread({"fitness:events": last_id}, count=500, block=2000)
        if resp:
            _, entries = resp[0]
            for eid, data in entries:
                data.pop("event_ts", None)
                buffer.append(data)
                last_id = eid

        now = time.time()
        if len(buffer) >= 5000 or (buffer and now - fitness_writer.last_flush >= 60):
            col_fitness.insert_many(buffer)
            buffer.clear()
            fitness_writer.last_flush = now

        time.sleep(1)

def simple_writer(stream, coll, poll_interval=5):
    last_id = "0-0"
    while True:
        resp = r.xread({stream: last_id}, count=100, block=poll_interval * 1000)
        if resp:
            _, entries = resp[0]
            for eid, data in entries:
                data["_id"] = eid
                coll.insert_one(data)
                last_id = eid
        time.sleep(poll_interval)

if __name__ == "__main__":
    load_static("fitness:users",   col_users)
    load_static("fitness:devices", col_devices)

    threads = [
        threading.Thread(target=fitness_writer, daemon=True),
        threading.Thread(target=lambda: simple_writer("fitness:sleep",     col_sleep),     daemon=True),
        threading.Thread(target=lambda: simple_writer("fitness:nutrition", col_nutrition), daemon=True),
        threading.Thread(target=lambda: simple_writer("fitness:feedback",  col_feedback,  poll_interval=60), daemon=True),
    ]
    for t in threads:
        t.start()

    # keep the main thread alive
    while True:
        time.sleep(3600)
