#!/usr/bin/env python
"""
Multi-threaded Publisher for Synthetic Fitness Data
Each stream runs in its own thread, publishing forever in parallel.
"""
import threading
import time
import random
import datetime as dt
import redis

from generate_fitness_data_return import (
    generate_users,
    generate_devices,
    make_fitness_event,
    make_sleep_event,
    make_nutrition_event,
    make_feedback_event
)

# ─── configuration ─────────────────────────────────────────────────────────────
REDIS_HOST        = "localhost"
REDIS_PORT        = 6379

STREAM_USERS      = "fitness:users"
STREAM_DEVICES    = "fitness:devices"
STREAM_FITNESS    = "fitness:events"
STREAM_SLEEP      = "fitness:sleep"
STREAM_NUTRITION  = "fitness:nutrition"
STREAM_FEEDBACK   = "fitness:feedback"

N_USERS           = 100
DEVICES_PER_USER  = 1
EVENTS_PER_SEC    = 1

# ─── Redis setup ───────────────────────────────────────────────────────────────
r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=0, decode_responses=True)

def publish_event(stream, payload):
    r.xadd(stream, {k: str(v) for k, v in payload.items()})

# ─── bootstrap users & devices ─────────────────────────────────────────────────
users_df        = generate_users(num_users=N_USERS)
devices_df, dev_map = generate_devices(users_df, device_range=(1, DEVICES_PER_USER))

# publish static streams once
for rec in users_df.to_dict("records"):
    publish_event(STREAM_USERS, rec)

for rec in devices_df.to_dict("records"):
    publish_event(STREAM_DEVICES, rec)

# ─── threaded loops ────────────────────────────────────────────────────────────
def fitness_loop():
    """Publish fitness events every second."""
    user_ids = list(users_df["user_id"])
    while True:
        start = time.time()
        for u in user_ids:
            for _ in range(EVENTS_PER_SEC):
                ev = make_fitness_event(u, dev_map)
                publish_event(STREAM_FITNESS, ev)
        elapsed = time.time() - start
        time.sleep(0.01)

def sleep_loop():
    """Publish one 1-hour sleep session per user per day."""
    user_ids = list(users_df["user_id"])
    today = dt.datetime.utcnow().date()
    sleep_done = set()
    while True:
        now = dt.datetime.utcnow()
        if now.date() != today:
            today = now.date()
            sleep_done.clear()
        for u in user_ids:
            # approx 1 per day: 1/86400 chance each second
            if u not in sleep_done and random.random() < 1/86400:
                ev = make_sleep_event(u, dev_map)
                publish_event(STREAM_SLEEP, ev)
                sleep_done.add(u)
        time.sleep(1)

def nutrition_loop():
    """Publish up to 3 nutrition logs per user per day."""
    user_ids = list(users_df["user_id"])
    today = dt.datetime.utcnow().date()
    counts = {u: 0 for u in user_ids}
    while True:
        now = dt.datetime.utcnow()
        if now.date() != today:
            today = now.date()
            counts = {u: 0 for u in user_ids}
        for u in user_ids:
            # approx 3 per day: 3/86400 chance each second
            if counts[u] < 3 and random.random() < 3/86400:
                ev = make_nutrition_event(u)
                publish_event(STREAM_NUTRITION, ev)
                counts[u] += 1
        time.sleep(1)

def feedback_loop():
    """Publish one feedback event per user at 23:59 UTC."""
    user_ids = list(users_df["user_id"])
    today = dt.datetime.utcnow().date()
    done = set()
    while True:
        now = dt.datetime.utcnow()
        if now.date() != today:
            today = now.date()
            done.clear()
        # fire at 23:59 exactly
        if now.hour == 23 and now.minute == 59:
            for u in user_ids:
                if u not in done:
                    ev = make_feedback_event(u)
                    publish_event(STREAM_FEEDBACK, ev)
                    done.add(u)
        # sleep 30s to avoid double-firing in the same minute
        time.sleep(30)

# ─── start threads ─────────────────────────────────────────────────────────────
threads = [
    threading.Thread(target=fitness_loop,   daemon=True),
    threading.Thread(target=sleep_loop,     daemon=True),
    threading.Thread(target=nutrition_loop, daemon=True),
    threading.Thread(target=feedback_loop,  daemon=True),
]

for t in threads:
    t.start()

print(f"Running multi-threaded publisher with {N_USERS} users…")
# keep main thread alive forever
while True:
    time.sleep(3600)
