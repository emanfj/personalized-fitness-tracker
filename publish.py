# redis_streaming/publish.py
#!/usr/bin/env python
"""
Multi-threaded Publisher for Synthetic Fitness Data
Each stream runs in its own thread, publishing forever in parallel.
"""
import os
import threading
import time
import random
import datetime as dt
import redis

from redis_streaming.return_generated_fitness_data import (
    generate_users,
    generate_devices,
    make_fitness_event,
    make_sleep_event,
    make_nutrition_event,
    make_feedback_event
)

# ─── configuration ─────────────────────────────────────────────────────────────
REDIS_HOST       = os.getenv("REDIS_HOST", "redis")
REDIS_PORT       = int(os.getenv("REDIS_PORT", 6379))

STREAM_USERS     = "fitness:users"
STREAM_DEVICES   = "fitness:devices"
STREAM_FITNESS   = "fitness:events"
STREAM_SLEEP     = "fitness:sleep"
STREAM_NUTRITION = "fitness:nutrition"
STREAM_FEEDBACK  = "fitness:feedback"

N_USERS          = 100
DEVICES_PER_USER = 1
EVENTS_PER_SEC   = 1

# ─── Redis setup ───────────────────────────────────────────────────────────────
r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=0, decode_responses=True)

def publish_event(stream, payload):
    r.xadd(stream, {k: str(v) for k, v in payload.items()})

# ─── bootstrap users & devices ─────────────────────────────────────────────────
users_df, dev_map = (
    generate_users(num_users=N_USERS),
    None
)
devices_df, dev_map = generate_devices(users_df, device_range=(1, DEVICES_PER_USER))

# publish static streams once
for rec in users_df.to_dict("records"):
    publish_event(STREAM_USERS, rec)

for rec in devices_df.to_dict("records"):
    publish_event(STREAM_DEVICES, rec)

# ─── threaded loops ────────────────────────────────────────────────────────────
def fitness_loop():
    user_ids = list(users_df["user_id"])
    while True:
        start = time.time()
        for u in user_ids:
            for _ in range(EVENTS_PER_SEC):
                ev = make_fitness_event(u, dev_map)
                publish_event(STREAM_FITNESS, ev)
        time.sleep(max(0, 1 - (time.time() - start)))

def sleep_loop():
    user_ids = list(users_df["user_id"])
    # use timezone-aware UTC
    today = dt.datetime.now(dt.timezone.utc).date()
    sleep_done = set()
    while True:
        now = dt.datetime.now(dt.timezone.utc)
        if now.date() != today:
            today = now.date()
            sleep_done.clear()
        for u in user_ids:
            if u not in sleep_done and random.random() < 1/86400:
                ev = make_sleep_event(u, dev_map)
                publish_event(STREAM_SLEEP, ev)
                sleep_done.add(u)
        time.sleep(1)

def nutrition_loop():
    user_ids = list(users_df["user_id"])
    today = dt.datetime.now(dt.timezone.utc).date()
    counts = {u: 0 for u in user_ids}
    while True:
        now = dt.datetime.now(dt.timezone.utc)
        if now.date() != today:
            today = now.date()
            counts = {u: 0 for u in user_ids}
        for u in user_ids:
            if counts[u] < 3 and random.random() < 3/86400:
                ev = make_nutrition_event(u)
                publish_event(STREAM_NUTRITION, ev)
                counts[u] += 1
        time.sleep(1)

def feedback_loop():
    user_ids = list(users_df["user_id"])
    today = dt.datetime.now(dt.timezone.utc).date()
    done = set()
    while True:
        now = dt.datetime.now(dt.timezone.utc)
        if now.date() != today:
            today = now.date()
            done.clear()
        if now.hour == 23 and now.minute == 59:
            for u in user_ids:
                if u not in done:
                    ev = make_feedback_event(u)
                    publish_event(STREAM_FEEDBACK, ev)
                    done.add(u)
        time.sleep(30)

# ─── start threads ─────────────────────────────────────────────────────────────
for fn in (fitness_loop, sleep_loop, nutrition_loop, feedback_loop):
    threading.Thread(target=fn, daemon=True).start()

print(f"Running multi-threaded publisher with {N_USERS} users…")
while True:
    time.sleep(3600)
