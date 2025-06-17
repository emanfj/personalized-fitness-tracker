import faust
from datetime import timedelta
import json

# 1 define the event schema
class FitnessEvent(faust.Record, serializer='json'):
    user_id: str
    device_id: str
    timestamp: str       # ISO-format string
    event_type: str      # e.g. walking, running
    value: float         # e.g. heart_rate_bpm
    ingestion_time: str

# 2 create the Faust app, pointing at your local Kafka broker
app = faust.App(
    'fitness_tracker_app',
    broker='kafka://localhost:9092',
    value_serializer='raw',
)

# 3 set up the input topic
events_topic = app.topic('fitness-events', value_type=FitnessEvent)

# 4 define a tumbling windowed table: one 60s bucket per user
stats = app.Table(
    'user_hr_stats',
    default=list,
    partitions=1,
).tumbling(
    size=timedelta(seconds=60),
    expires=timedelta(seconds=120),
)

# 5 agent to consume incoming events into the windowed table
@app.agent(events_topic)
async def process(events):
    async for ev in events:
        # add each reading to the list for that user in the current window
        stats[ev.user_id].append(ev.value)

# 6 timer that fires every 60s to compute and output aggregates
@app.timer(interval=60.0)
async def emit_window_stats():
    now = app.loop.time()
    print(f'\n=== aggregates @ {now:.0f} ===')
    for user, readings in stats.items():
        if not readings:
            continue
        count = len(readings)
        avg   = sum(readings) / count
        mn    = min(readings)
        mx    = max(readings)
        # print or write to Parquet / database here
        print(f'user={user:12s}  count={count:4d}  avg={avg:6.1f}  min={mn:3.0f}  max={mx:3.0f}')
    # Faust will expire old windows automatically

if __name__ == '__main__':
    app.main()
