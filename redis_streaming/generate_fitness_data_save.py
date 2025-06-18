#!/usr/bin/env python
"""
Synthetic data generator for fitness-tracker project
—————————————————————————————————————————————————————
Outputs six tables into ./data/  (CSV for slow-moving, Parquet for high-rate)
  users.csv
  devices.csv
  fitness_events.parquet
  sleep_sessions.csv
  nutrition_logs.csv
  feedback_events.csv
Requires: faker numpy pandas pyarrow
"""

import uuid, random, json, pathlib, datetime as dt
from faker import Faker
import numpy as np
import pandas as pd

# ─── Config ───────────────────────────────────────────────────────────
SEED              = 2025
NUM_USERS         = 300
DAYS_HISTORY      = 30
EVENTS_PER_MINUTE = 1           # 60 → per-second
DEVICE_RANGE      = (1, 3)
OUTPUT_DIR        = pathlib.Path("../data")
OUTPUT_DIR.mkdir(exist_ok=True, parents=True)

faker = Faker()
Faker.seed(SEED)
random.seed(SEED)
np.random.seed(SEED)

def rand_dt(start, end):
    delta = int((end - start).total_seconds())
    return start + dt.timedelta(seconds=random.randint(0, delta))

def beta_between(a, b, low, high):
    return low + (high - low) * np.random.beta(a, b)

# ─── 1. users ─────────────────────────────────────────────────────────
goal_types = ["lose_weight", "gain_muscle", "maintain"]
auth_providers = ["email_password", "google_oauth", "apple_id"]

users = []
for _ in range(NUM_USERS):
    dob = faker.date_of_birth(minimum_age=18, maximum_age=60)
    height  = round(np.random.normal(170, 10), 1)
    bmi     = np.random.normal(25, 4)
    weight  = round(bmi * (height/100) ** 2, 1)
    signup  = rand_dt(
        dt.datetime.now(dt.UTC)  - dt.timedelta(days=365),
        dt.datetime.now(dt.UTC) 
    )
    users.append(dict(
        user_id             = str(uuid.uuid4()),
        user_name           = faker.user_name(),
        email               = faker.email(),
        auth_provider       = random.choice(auth_providers),
        date_of_birth       = dob,
        gender              = random.choice(["male","female","other","prefer_not_to_say"]),
        height_cm           = height,
        weight_kg_start     = weight,
        resting_hr_baseline = int(np.random.normal(65, 8)),
        timezone            = "Asia/Karachi",
        goal_type           = random.choice(goal_types),
        signup_ts           = signup,
        country_code        = faker.country_code(representation="alpha-2"),
    ))

pd.DataFrame(users).to_csv(OUTPUT_DIR/"users.csv", index=False)

# ─── 2. devices ───────────────────────────────────────────────────────
device_types = {
    "watch":  ["Garmin-Fenix", "Fitbit-Charge", "Pixel-Watch"],
    "ring":   ["Oura-Gen3"],
    "band":   ["Whoop-4.0", "Mi-Band-9"],
}
devices = []
for u in users:
    for _ in range(random.randint(*DEVICE_RANGE)):
        dtype = random.choice(list(device_types))
        devices.append(dict(
            device_id        = str(uuid.uuid4()),
            user_id          = u["user_id"],
            device_type      = dtype,
            model            = random.choice(device_types[dtype]),
            firmware_version = f"{random.randint(1,3)}.{random.randint(0,9)}.{random.randint(0,9)}",
            battery_pct      = random.randint(20, 100),
            first_seen_ts    = u["signup_ts"],
            last_seen_ts     = dt.datetime.now(dt.UTC) ,
            last_sync_ts     = dt.datetime.now(dt.UTC)  - dt.timedelta(minutes=random.randint(0,60)),
        ))

pd.DataFrame(devices).to_csv(OUTPUT_DIR/"devices.csv", index=False)

user_to_devices = {}
for d in devices:
    user_to_devices.setdefault(d["user_id"], []).append(d["device_id"])

# ─── 3. fitness_events ────────────────────────────────────────────────
start_sim = dt.datetime.now(dt.UTC)  - dt.timedelta(days=DAYS_HISTORY)
activity_choices = ["walking","running","cycling","rest"]
weather_codes = ["clear","cloudy","rain","hot","cold"]

fitness_rows = []
for u in users:
    age, max_hr = (dt.date.today() - u["date_of_birth"]).days//365, 220 - (dt.date.today() - u["date_of_birth"]).days//365
    for day in range(DAYS_HISTORY):
        date_base = dt.date.today() - dt.timedelta(days=day)
        active_minutes = random.randint(20, 150)
        minute_slots = random.sample(range(24*60), active_minutes)
        for m in minute_slots:
            ts  = dt.datetime.combine(date_base, dt.time()) + dt.timedelta(minutes=m)
            act = random.choices(activity_choices, weights=[.55,.2,.05,.2])[0]
            steps = {"walking":random.randint(80,120),"running":random.randint(150,190),"cycling":0,"rest":0}[act]
            hr = int(beta_between(2,5,0.55,0.75)*max_hr) if act!="rest" else u["resting_hr_baseline"]
            fitness_rows.append(dict(
                event_id            = str(uuid.uuid4()),
                user_id             = u["user_id"],
                device_id           = random.choice(user_to_devices[u["user_id"]]),
                event_ts            = ts,
                step_increment      = steps,
                distance_m          = round(steps*0.78,2),
                gps_lat             = 24.5 + random.random()*4,
                gps_lon             = 66.0 + random.random()*3,
                altitude_m          = round(np.random.normal(50,15),1),
                sedentary_flag      = act=="rest",
                heart_rate_bpm      = hr,
                calories_burned     = round(steps*0.04,3),
                activity_type       = act,
                activity_duration_min = 1/EVENTS_PER_MINUTE,
                cadence_spm         = steps,
                elevation_gain_m    = round(np.random.exponential(0.2),2),
                temperature_c       = round(np.random.normal(30,5),1),
                weather_code        = random.choice(weather_codes),
            ))

pd.DataFrame(fitness_rows).to_parquet(OUTPUT_DIR/"fitness_events.parquet", index=False)

# ─── 4. sleep_sessions ────────────────────────────────────────────────
sleep_rows=[]
for u in users:
    for day in range(DAYS_HISTORY):
        start = dt.datetime.combine(
            dt.date.today()-dt.timedelta(days=day+1), dt.time(22)) + dt.timedelta(minutes=random.randint(-60,60))
        dur   = random.randint(360,540)
        end   = start + dt.timedelta(minutes=dur)
        sleep_rows.append(dict(
            session_id          = str(uuid.uuid4()),
            user_id             = u["user_id"],
            device_id           = random.choice(user_to_devices[u["user_id"]]),
            start_ts            = start,
            end_ts              = end,
            sleep_quality_score = random.randint(55,95),
            sleep_stage_seq     = json.dumps([{"stage":"light","start":0,"end":dur*0.6},
                                              {"stage":"deep","start":dur*0.6,"end":dur*0.8},
                                              {"stage":"rem","start":dur*0.8,"end":dur}]),
            avg_hr_bpm          = max(40,int(np.random.normal(u["resting_hr_baseline"]-10,3))),
            efficiency_pct      = round(beta_between(4,2,0.7,0.98)*100,1),
        ))

pd.DataFrame(sleep_rows).to_csv(OUTPUT_DIR/"sleep_sessions.csv", index=False)

# ─── 5. nutrition_logs ────────────────────────────────────────────────
food_db = [
    ("oatmeal",150,6,27,3,1,4,250),
    ("banana",89,1,23,0,12,3,100),
    ("chicken_breast",165,31,0,4,0,0,0),
    ("white_rice",200,4,45,0,0,1,100),
    ("lentil_soup",180,12,30,1,1,8,200),
    ("mixed_salad",90,3,10,5,3,2,150),
    ("protein_shake",130,24,5,2,1,0,250),
]
nutrition_rows=[]
for u in users:
    for day in range(DAYS_HISTORY):
        base_date = dt.date.today()-dt.timedelta(days=day)
        meals = [("breakfast","08:00"),("lunch","13:00"),("dinner","19:30")]
        if random.random()<0.4: meals.append(("snack","16:30"))
        for meal_type, when in meals:
            ts = dt.datetime.strptime(f"{base_date} {when}", "%Y-%m-%d %H:%M")
            food = random.choice(food_db)
            nutrition_rows.append(dict(
                meal_id        = str(uuid.uuid4()),
                log_id         = str(uuid.uuid4()),
                user_id        = u["user_id"],
                log_ts         = ts,
                meal_type      = meal_type,
                food_items     = json.dumps([{"name":food[0],"qty":1,"unit":"serving"}]),
                calories_kcal  = food[1],
                protein_g      = food[2],
                carbs_g        = food[3],
                fat_g          = food[4],
                sugar_g        = food[5],
                fibre_g        = food[6],
                water_ml       = food[7],
            ))

pd.DataFrame(nutrition_rows).to_csv(OUTPUT_DIR/"nutrition_logs.csv", index=False)

# ─── 6. feedback_events ───────────────────────────────────────────────
feedback_rows=[]
for row in fitness_rows:
    if row["activity_type"]!="rest" and random.random()<0.25:
        feedback_rows.append(dict(
            feedback_id    = str(uuid.uuid4()),
            user_id        = row["user_id"],
            event_ts       = row["event_ts"],
            context        = "workout",
            mood_level     = random.randint(2,5),
            energy_level   = random.randint(2,5),
            rpe_score      = random.randint(4,10),
            soreness_level = random.randint(1,5),
            free_text      = random.choice(["Felt great!","Could push harder","Legs sore","Too easy",""]),
        ))

pd.DataFrame(feedback_rows).to_csv(OUTPUT_DIR/"feedback_events.csv", index=False)

print("✔  Synthetic dataset written to", OUTPUT_DIR.resolve())
