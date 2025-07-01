import uuid, random, json
import datetime as dt
from faker import Faker
import numpy as np
import pandas as pd

faker = Faker()
np.random.seed(2025)
random.seed(2025)

def generate_users(num_users=300, seed=2025) -> pd.DataFrame:
    random.seed(seed); np.random.seed(seed); Faker.seed(seed)
    now = dt.datetime.now(dt.timezone.utc)
    one_year_ago = now - dt.timedelta(days=365)
    rows = []
    for _ in range(num_users):
        dob = faker.date_of_birth(minimum_age=18, maximum_age=60)
        height = round(np.random.normal(170,10),1)
        bmi    = np.random.normal(25,4)
        weight = round(bmi*(height/100)**2,1)
        signup = one_year_ago + dt.timedelta(seconds=random.randint(0,365*24*3600))
        rows.append({
            "user_id": str(uuid.uuid4()),
            "user_name": faker.user_name(),
            "email": faker.email(),
            "date_of_birth": dob.isoformat(),
            "height_cm": height,
            "weight_kg_start": weight,
            "resting_hr_baseline": int(np.random.normal(65,8)),
            "signup_ts": signup.isoformat(),
        })
    return pd.DataFrame(rows)

def generate_devices(users_df: pd.DataFrame,
                     device_range=(1,3), seed=2025):
    random.seed(seed)
    types = {"watch":["Garmin","Fitbit"],"ring":["Oura"],"band":["Whoop"]}
    now = dt.datetime.now(dt.timezone.utc)
    rows, mapping = [], {}
    for rec in users_df.to_dict('records'):
        uid = rec["user_id"]
        mapping[uid] = []
        for _ in range(random.randint(*device_range)):
            did = str(uuid.uuid4())
            t   = random.choice(list(types))
            rows.append({
                "device_id":       did,
                "user_id":         uid,
                "device_type":     t,
                "model":           random.choice(types[t]),
                "first_seen_ts":   rec["signup_ts"],
                "last_seen_ts":    now.isoformat()
            })
            mapping[uid].append(did)
    return pd.DataFrame(rows), mapping

def make_fitness_event(user_id, devices):
    return {
        "event_id":       str(uuid.uuid4()),
        "user_id":        user_id,
        "device_id":      random.choice(devices[user_id]),
        "heart_rate_bpm": random.randint(60,180),
        "step_increment": random.randint(0,20),
        "event_ts":       dt.datetime.now(dt.timezone.utc).isoformat()
    }

def make_sleep_event(user_id, devices):
    start = dt.datetime.now(dt.timezone.utc) + dt.timedelta(seconds=random.randint(0,86400))
    end   = start + dt.timedelta(hours=1)
    return {
        "session_id": str(uuid.uuid4()),
        "user_id":    user_id,
        "device_id":  random.choice(devices[user_id]),
        "start_ts":   start.isoformat(),
        "end_ts":     end.isoformat(),
        "quality":    random.randint(50,100)
    }

def make_nutrition_event(user_id):
    meals = {"breakfast":8,"lunch":13,"dinner":19}
    m = random.choice(list(meals))
    ts = dt.datetime.now(dt.timezone.utc).replace(
        hour=meals[m], minute=random.randint(0,59), second=0)
    return {
        "log_id":       str(uuid.uuid4()),
        "user_id":      user_id,
        "meal_type":    m,
        "calories":     random.randint(200,600),
        "log_ts":       ts.isoformat()
    }

def make_feedback_event(user_id):
    ts = dt.datetime.now(dt.timezone.utc).replace(hour=23,minute=59,second=0)
    return {
        "feedback_id": str(uuid.uuid4()),
        "user_id":     user_id,
        "event_ts":    ts.isoformat(),
        "mood":        random.randint(1,5),
        "energy":      random.randint(1,5)
    }