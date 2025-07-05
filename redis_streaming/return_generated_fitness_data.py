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
        age = int((now.date() - dob).days / 365)
        height = round(np.random.normal(170,10),1)
        bmi    = np.random.normal(25,4)
        weight = round(bmi*(height/100)**2,1)
        signup = one_year_ago + dt.timedelta(seconds=random.randint(0,365*24*3600))
        rows.append({
            "user_id":            str(uuid.uuid4()),
            "user_name":          faker.user_name(),
            "email":              faker.email(),
            "date_of_birth":      dob.isoformat(),
            "age":                age,
            "height_cm":          height,
            "weight_kg_start":    weight,
            "resting_hr_baseline":int(np.random.normal(65,8)),
            "max_hr_estimate":    220 - age,
            "goal_type":          random.choices(
                                     ["weight_loss","endurance","strength"],
                                     [0.5,0.3,0.2])[0],
            "dietary_preference": random.choice(
                                     ["omnivore","vegetarian","vegan"]),
            "signup_ts":          signup.isoformat(),
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
                "device_id":     did,
                "user_id":       uid,
                "device_type":   t,
                "model":         random.choice(types[t]),
                "first_seen_ts": rec["signup_ts"],
                "last_seen_ts":  now.isoformat()
            })
            mapping[uid].append(did)
    return pd.DataFrame(rows), mapping

def make_fitness_event(user_id, devices):
    # choose activity and derive metrics
    activity = random.choices(
        ["walking","running","cycling","strength","yoga"],
        [0.80,0.10,0.05,0.03,0.02])[0]
    # duration in seconds
    duration_s = random.randint(300, 3600) if activity in ("running","cycling") else random.randint(60,600)
    distance_m = None
    pace_s_per_km = None
    if activity == "running":
        distance_m = max(0, random.gauss(3000,500))
        pace_s_per_km = distance_m / 1000 / (duration_s/3600)
    elif activity == "cycling":
        distance_m = max(0, random.gauss(10000,2000))
        pace_s_per_km = distance_m / 1000 / (duration_s/3600)

    hr = random.randint(60,180)
    # finer-grained signals
    hr_variability = random.uniform(20, 60)
    spo2 = round(random.uniform(95, 100),1)
    respiration = random.randint(12,20)
    skin_temp = round(random.uniform(36.0,37.5),1)
    gsr = round(random.uniform(0.2,5.0),2)

    # estimate calories burned via a rough MET formula
    # assume weight_kg in mapping if available; default to 70
    weight = 70
    met = {"walking":3.5,"running":8,"cycling":6,"strength":5,"yoga":2.5}[activity]
    cal_burned = int(met * weight * (duration_s/3600) * 1.05)

    return {
        "event_id":          str(uuid.uuid4()),
        "user_id":           user_id,
        "device_id":         random.choice(devices[user_id]),
        "activity_type":     activity,
        "duration_s":        duration_s,
        "distance_m":        distance_m,
        "pace_s_per_km":     pace_s_per_km,
        "heart_rate_bpm":    hr,
        "hr_variability":    hr_variability,
        "spo2_pct":          spo2,
        "respiration_rate":  respiration,
        "skin_temp_c":       skin_temp,
        "gsr_us":            gsr,
        "calories_burned":   cal_burned,
        "indoor":            random.choice([True, False]),
        "gps_lat":           round(random.uniform(-90,90),6),
        "gps_lon":           round(random.uniform(-180,180),6),
        "step_increment":    random.randint(0,20),
        "event_ts":          dt.datetime.now(dt.timezone.utc).isoformat(),
    }

def make_sleep_event(user_id, devices):
    start = dt.datetime.now(dt.timezone.utc) + dt.timedelta(seconds=random.randint(0,86400))
    end   = start + dt.timedelta(hours=random.uniform(6,9))
    total_h = (end - start).total_seconds()/3600
    light = random.uniform(50,60)
    deep  = random.uniform(15,25)
    rem   = 100 - light - deep
    awakenings = np.random.poisson(total_h/2)
    return {
        "session_id":            str(uuid.uuid4()),
        "user_id":               user_id,
        "device_id":             random.choice(devices[user_id]),
        "start_ts":              start.isoformat(),
        "end_ts":                end.isoformat(),
        "quality":               random.randint(50,100),
        "sleep_stage_breakdown": {"light":light, "deep":deep, "rem":rem},
        "awakenings":            int(awakenings),
    }

def make_nutrition_event(user_id):
    meals = {"breakfast":8,"lunch":13,"dinner":19,"snack":16}
    m = random.choice(list(meals))
    ts = dt.datetime.now(dt.timezone.utc).replace(
        hour=meals[m], minute=random.randint(0,59), second=0)
    cal = random.randint(200,600)
    protein = random.randint(20,40)
    carbs   = random.randint(30,80)
    fat = max(0, int((cal - (4*protein+4*carbs)) / 9))
    water = random.randint(200,500)
    return {
        "log_id":       str(uuid.uuid4()),
        "user_id":      user_id,
        "meal_type":    m,
        "calories":     cal,
        "protein_g":    protein,
        "carbs_g":      carbs,
        "fat_g":        fat,
        "water_ml":     water,
        "log_ts":       ts.isoformat(),
    }

def make_feedback_event(user_id):
    ts = dt.datetime.now(dt.timezone.utc).replace(hour=23,minute=59,second=0)
    # subjective feedback
    mood    = random.randint(1,5)
    energy  = random.randint(1,5)
    exertion = random.randint(1,10)
    soreness  = min(10, max(1, exertion + random.choice([-1,0,1])))
    return {
        "feedback_id":       str(uuid.uuid4()),
        "user_id":           user_id,
        "event_ts":          ts.isoformat(),
        "mood":              mood,
        "energy":            energy,
        "perceived_exertion":exertion,
        "soreness_level":    soreness,
    }
