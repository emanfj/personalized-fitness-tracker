#!/usr/bin/env python
"""
Redis Streams Reader for Synthetic Fitness Data

Tails:
  • fitness:users
  • fitness:devices
  • fitness:events
  • fitness:sleep
  • fitness:nutrition
  • fitness:feedback

Run alongside your publisher to see each record in real time.
Requires: redis
"""

import time
import redis

# ─── configuration ─────────────────────────────────────────────────────────────
REDIS_HOST      = "localhost"
REDIS_PORT      = 6379
STREAM_USERS    = "fitness:users"
STREAM_DEVICES  = "fitness:devices"
STREAM_FITNESS  = "fitness:events"
STREAM_SLEEP    = "fitness:sleep"
STREAM_NUTRITION= "fitness:nutrition"
STREAM_FEEDBACK = "fitness:feedback"

# ─── connect ───────────────────────────────────────────────────────────────────
r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=0, decode_responses=True)

# start reading from the beginning of each stream
last_ids = {
    STREAM_USERS:     "0-0",
    STREAM_DEVICES:   "0-0",
    STREAM_FITNESS:   "0-0",
    STREAM_SLEEP:     "0-0",
    STREAM_NUTRITION: "0-0",
    STREAM_FEEDBACK:  "0-0",
}

print("⏳ Waiting for new events (Ctrl-C to quit)…")

try:
    while True:
        # XREAD blocks up to 5s if no data, returns list of (stream, entries)
        resp = r.xread(streams=last_ids, count=100, block=5000)
        if not resp:
            continue

        for stream_name, entries in resp:
            for entry_id, data in entries:
                # data is already a dict of str→str thanks to decode_responses=True
                print(f"[{stream_name}] {entry_id} → {data}")
                # update our last-seen ID so we don’t re-read
                last_ids[stream_name] = entry_id

except KeyboardInterrupt:
    print("\n👋  Exiting reader.")
