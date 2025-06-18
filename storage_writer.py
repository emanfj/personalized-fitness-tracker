#!/usr/bin/env python
"""
Redis → MongoDB writer
  • tails your six fitness streams
  • writes users/devices once
  • buffers fitness_events in 60s windows (bulk insert or when large)
  • writes sleep/nutrition on arrival (low-volume)
  • writes feedback once/day (polled every 60s)
"""
import threading
import time
import redis
from pymongo import MongoClient

# ─── Redis config ─────────────────────────────────────────────────────────────
r = redis.Redis(host="localhost", port=6379, db=0, decode_responses=True)

# ─── Mongo config ─────────────────────────────────────────────────────────────
mongo = MongoClient("mongodb://localhost:27017")
db    = mongo.fitness_tracker
col_users      = db.users
col_devices    = db.devices
col_fitness    = db.fitness_events
col_sleep      = db.sleep_sessions
col_nutrition  = db.nutrition_logs
col_feedback   = db.feedback_events

# ─── initial load (only needed once if you already inserted) ─────────────────
def load_static(stream, coll):
    last_id = "0-0"
    while True:
        resp = r.xread({stream: last_id}, count=100, block=2000)
        if not resp:
            break
        for _, entries in resp:
            for eid, data in entries:
                # use user_id or device_id as the Mongo _id
                data["_id"] = data.get("user_id") or data.get("device_id") or eid
                coll.replace_one({"_id": data["_id"]}, data, upsert=True)
                last_id = eid

# ─── fitness buffer thread ───────────────────────────────────────────────────
def fitness_writer():
    buffer = []
    last_id = "0-0"
    while True:
        # read up to 500 at a time, block up to 2s if empty
        resp = r.xread({"fitness:events": last_id}, count=500, block=2000)
        if resp:
            _, entries = resp[0]
            for eid, data in entries:
                # drop the raw string timestamp if you prefer to store real Date fields
                data.pop("event_ts", None)
                buffer.append(data)
                last_id = eid

        now = time.time()
        # flush if >5000 records or every 60s
        if len(buffer) >= 5000 or (buffer and now - fitness_writer.last_flush >= 60):
            col_fitness.insert_many(buffer)
            buffer.clear()
            fitness_writer.last_flush = now

        time.sleep(1)

# initialize our last-flush timestamp
fitness_writer.last_flush = time.time()

# ─── one-off writer for sleep / nutrition / feedback ─────────────────────────
def simple_writer(stream, coll, poll_interval=5):
    """
    poll_interval: how often (in seconds) to check for new entries
    """
    last_id = "0-0"
    while True:
        # block for up to poll_interval seconds (converted to ms)
        resp = r.xread({stream: last_id}, count=100, block=poll_interval * 1000)
        if not resp:
            continue
        _, entries = resp[0]
        for eid, data in entries:
            data["_id"] = eid
            coll.insert_one(data)
            last_id = eid

# ─── start everything ─────────────────────────────────────────────────────────
if __name__ == "__main__":
    # initial load of our two static streams
    load_static("fitness:users",   col_users)
    load_static("fitness:devices", col_devices)

    # spawn writers
    threads = [
        threading.Thread(target=fitness_writer,                                        daemon=True),
        threading.Thread(target=lambda: simple_writer("fitness:sleep",     col_sleep),     daemon=True),
        threading.Thread(target=lambda: simple_writer("fitness:nutrition", col_nutrition), daemon=True),
        # feedback only arrives at 23:59, so polling every 60s is plenty
        threading.Thread(target=lambda: simple_writer("fitness:feedback",  col_feedback,  poll_interval=60), daemon=True),
    ]
    for t in threads:
        t.start()

    # keep main thread alive
    while True:
        time.sleep(3600)
