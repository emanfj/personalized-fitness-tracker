import argparse
import uuid
import random
import datetime as dt
import pymongo
import numpy as np
from faker import Faker

# Only feedback events population script

faker = Faker()
np.random.seed(2025)
random.seed(2025)

# Generate a feedback_event document
def make_feedback_event(user_id):
    ts = dt.datetime.utcnow().replace(hour=23, minute=59, second=0, tzinfo=dt.timezone.utc)
    mood = random.randint(1,5)
    energy = random.randint(1,5)
    exertion = random.randint(1,10)
    soreness = min(10, max(1, exertion + random.choice([-1,0,1])))
    return {
        "feedback_id": str(uuid.uuid4()),
        "user_id": user_id,
        "event_ts": ts.isoformat(),
        "mood": mood,
        "energy": energy,
        "perceived_exertion": exertion,
        "soreness_level": soreness,
    }

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Populate synthetic feedback_events for a specific user")
    parser.add_argument("--user_id", "-u", required=True, help="Target user_id")
    parser.add_argument("--n", "-n", type=int, default=10, help="Number of feedback events to generate")
    parser.add_argument(
        "--mongo_uri", "-m", default="mongodb://localhost:27017", help="MongoDB connection URI"
    )
    args = parser.parse_args()

    client = pymongo.MongoClient(args.mongo_uri)
    db = client["fitness_tracker"]

    docs = [make_feedback_event(args.user_id) for _ in range(args.n)]
    result = db.feedback_events.insert_many(docs)
    print(f"Inserted {len(result.inserted_ids)} synthetic 'feedback_events' documents for user {args.user_id}")
