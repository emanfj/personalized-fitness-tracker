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
from pymongo import MongoClient, errors

# ─── Redis config ─────────────────────────────────────────────────────────────
REDIS_HOST = os.getenv("REDIS_HOST", "127.0.0.1")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=0, decode_responses=True)

# test Redis connection
def test_redis():
    try:
        pong = r.ping()
        print(f"[INFO] Connected to Redis at {REDIS_HOST}:{REDIS_PORT}! PING -> {pong}")
    except Exception as e:
        print(f"[ERROR] Redis connection failed: {e}")
        raise

# ─── Mongo config ─────────────────────────────────────────────────────────────
MONGO_URI = os.getenv("MONGO_URI", "mongodb://127.0.0.1:27017")  # Docker service hostname

# helper to wait for MongoDB readiness
def get_mongo_client(uri, retries=10, delay=5):
    last_exc = None
    for i in range(retries):
        try:
            client = MongoClient(uri, serverSelectionTimeoutMS=5000)
            client.admin.command("ping")
            print(f"[INFO] Connected to MongoDB at {uri} on attempt {i+1}")
            return client
        except Exception as e:
            print(f"[WARN] MongoDB not ready (attempt {i+1}/{retries}): {e}")
            last_exc = e
            time.sleep(delay)
    print(f"[ERROR] Could not connect to MongoDB at {uri} after {retries} retries")
    raise last_exc

# class for additional DB tests and creation
class DBTester:
    @staticmethod
    def test_and_create(db_name):
        try:
            # Ping to confirm connection
            mongo.admin.command("ping")
            print(f"[INFO] MongoDB ping successful.")
            # Create a temporary collection to force DB creation
            temp_db = mongo.get_database(db_name)
            tmp_coll = f"init_{db_name}"
            if tmp_coll in temp_db.list_collection_names():
                temp_db.drop_collection(tmp_coll)
            temp_db.create_collection(tmp_coll)
            print(f"[INFO] Created temp collection '{tmp_coll}' in '{db_name}'.")
            temp_db.drop_collection(tmp_coll)
            print(f"[INFO] Dropped temp collection '{tmp_coll}'. Database '{db_name}' is now initialized.")
        except Exception as e:
            print(f"[ERROR] DBTester failed for '{db_name}': {e}")
            raise

# establish Mongo connection
mongo = get_mongo_client(MONGO_URI)
# force-create the fitness_tracker database
temp_db = mongo.get_database("fitness_tracker")
# real DB and collections
_db = temp_db
col_users     = _db.users
col_devices   = _db.devices
col_fitness   = _db.fitness_events
col_sleep     = _db.sleep_sessions
col_nutrition = _db.nutrition_logs
col_feedback  = _db.feedback_events

# perform initial connectivity tests
if __name__ == '__main__':
    test_redis()
    DBTester.test_and_create("fitness_tracker")
    print("[INFO] Initialization complete. Starting writer threads...")

# ─── helper functions ──────────────────────────────────────────────────────────
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

# buffer bulk inserts for high-throughput streams
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
        if buffer and (len(buffer) >= 5000 or now - fitness_writer.last_flush >= 60):
            try:
                col_fitness.insert_many(buffer)
                print(f"[INFO] Inserted {len(buffer)} fitness events", flush=True)
            except errors.BulkWriteError as bwe:
                print(f"[WARN] Bulk insert error: {bwe.details}")
            buffer.clear()
            fitness_writer.last_flush = now
        time.sleep(1)

# immediate inserts with duplicate-key handling
def simple_writer(stream, coll, poll_interval=5):
    last_id = "0-0"
    while True:
        resp = r.xread({stream: last_id}, count=100, block=poll_interval * 1000)
        if resp:
            _, entries = resp[0]
            for eid, data in entries:
                data["_id"] = eid
                try:
                    coll.insert_one(data)
                    print(f"[INFO] Inserted into {coll.name}: {eid}", flush=True)
                except errors.DuplicateKeyError:
                    # duplicate _id, skip
                    pass
                last_id = eid
        time.sleep(poll_interval)

if __name__ != '__main__':
    # when imported, do nothing
    pass

if __name__ == '__main__':
    # load static streams once
    load_static("fitness:users", col_users)
    load_static("fitness:devices", col_devices)
    # start writer threads
    threads = [
        threading.Thread(target=fitness_writer, daemon=True),
        threading.Thread(target=lambda: simple_writer("fitness:sleep", col_sleep), daemon=True),
        threading.Thread(target=lambda: simple_writer("fitness:nutrition", col_nutrition), daemon=True),
        threading.Thread(target=lambda: simple_writer("fitness:feedback", col_feedback, poll_interval=60), daemon=True),
    ]
    for t in threads:
        t.start()
    print("[INFO] Storage writer threads started", flush=True)
    # keep main thread alive
    while True:
        time.sleep(3600)
