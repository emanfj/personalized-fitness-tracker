# Personalized Fitness Tracker

## 1. Project Overview


This repository implements an end-to-end real-time pipeline that generates, streams, and stores synthetic fitness data, ready for ai/ml and analytics.

## introduction

this project simulates a wearable-to-database workflow using docker, redis streams, and mongodb. it publishes user profiles, devices, workout events, sleep sessions, nutrition logs, and daily feedback into redis streams, then writes them into mongodb collections. the resulting data lake powers recommendation engines, adaptive agents, and fitness analytics.

## prerequisites

- docker & docker compose (v2+)  
- optional: python 3.8+ & pip (for local runs)  
- at least 8 gb ram for local development  


## architecture overview

1. **publisher**  
   - multi-threaded python service that generates synthetic data and XADDs into six redis streams  
2. **storage_writer**  
   - python service that XREADs from redis, upserts users/devices, bulk-inserts fitness events, and writes other streams to mongodb  
3. **redis**  
   - message broker for streams (image: redis:7)  
4. **mongodb**  
   - persistent storage for collections under `fitness_tracker` (image: mongo:6)  

all services run in containers and communicate over the default compose network.

## data pipeline

### redis streams

- `fitness:users`  
- `fitness:devices`  
- `fitness:events`  
- `fitness:sleep`  
- `fitness:nutrition`  
- `fitness:feedback`

### publisher.py

on startup publishes static streams once:
```python
fitness:users → {
  user_id, user_name, email, date_of_birth, age,
  height_cm, weight_kg_start, resting_hr_baseline,
  max_hr_estimate, goal_type, dietary_preference, signup_ts
}
fitness:devices → {
  device_id, user_id, device_type, model,
  first_seen_ts, last_seen_ts
}
then in parallel threads emits:
fitness:events → {
  event_id, user_id, device_id, activity_type,
  duration_s, distance_m, pace_s_per_km,
  heart_rate_bpm, hr_variability, spo2_pct,
  respiration_rate, skin_temp_c, gsr_us,
  calories_burned, step_increment, indoor,
  gps_lat, gps_lon, event_ts
}

fitness:sleep → {
  session_id, user_id, device_id, start_ts,
  end_ts, quality, sleep_stage_breakdown, awakenings
}

fitness:nutrition → {
  log_id, user_id, meal_type, calories,
  protein_g, carbs_g, fat_g, water_ml, log_ts
}

fitness:feedback → {
  feedback_id, user_id, event_ts, mood,
  energy, perceived_exertion, soreness_level
}
# one event per user per day at 23:59 UTC
storage_writer.py
on startup:

waits for redis & mongo readiness

creates/drops a temp collection to force the fitness_tracker DB

loads static streams (fitness:users, fitness:devices) via XREAD into db.users and db.devices

then spawns threads:

buffers 5000 fitness:events or 60 s windows → bulk-inserts into db.fitness_events

simple writers for

fitness:sleep → db.sleep_sessions

fitness:nutrition → db.nutrition_logs

fitness:feedback → db.feedback_events (once-per-day enforced)

creates indexes on key fields (event_ts, activity_type, start_ts, log_ts) for fast queries.

usage
from the project root (where docker-compose.yml lives):
```
docker compose up --build -d
docker compose logs -f publisher storage_writer
```
to stop and remove containers and volumes:
```
docker compose down -v
```
AI/ML Engineering
this layer provides a lightweight REST api backed by an llm and mongodb for generating personalized workout and nutrition plans, and collecting user feedback.

components
app.py
fastapi application defining routes, error handling, and mongodb interactions

plan_generator.py
prompt builders, llm call logic, json cleanup, data normalization, pydantic models, logging

user_context.py
builds user context from the database

features
generate 7-day workout plans via GET /workout/{user_id}

generate 3-day meal plans via GET /nutrition/{user_id}

collect user feedback via POST /feedback/{user_id}

view history of past plans via GET /plans/{user_id}/history
requirements
python 3.10+

mongodb instance (local or remote)

ollama llm server (or compatible http endpoint)

installation
```
pip install -r requirements.txt
```
environment variables
OLLAMA_API (e.g. http://127.0.0.1:11434/api/generate)

OLLAMA_MODEL (default llama3.2:latest)

MONGO_URI (default mongodb://localhost:27017)

PORT (optional, default 8000)

running the server
```
uvicorn app:app --reload --host 0.0.0.0 --port ${PORT:-8000}
```
api endpoints
GET /
health check

Response

json
Copy
Edit
{ "msg": "AI Fitness & Nutrition API up." }
GET /workout/{user_id}
7-day workout plan

GET /nutrition/{user_id}
3-day meal plan

POST /feedback/{user_id}
record feedback event

GET /plans/{user_id}/history
retrieve last 10 plans

data flow
user context fetched from mongodb

plan_generator builds prompt and calls llm

raw json cleaned & validated

plans saved in plans collection

feedback stored in feedback_events

contributing
pull requests welcome. run tests with pytest and update this readme.

<old below>
- **Publisher**: Generates and publishes synthetic fitness data (users, devices, fitness events, sleep sessions, nutrition logs, feedback events) to Redis streams.
- **Storage Writer**: Tails Redis streams and writes data into MongoDB collections, with batching for high‑volume streams and one‑off writes for low‑volume streams.
- **(Optional) Reader**: A simple script to tail and display streams for debugging.

A `data/` folder contains static exports of previous runs in CSV and Parquet format for direct ingestion or reference:

```
data/
├── devices.csv
├── feedback_events.csv
├── fitness_events.parquet
├── nutrition_logs.csv
├── sleep_sessions.csv
└── users.csv
```

## 2. Prerequisites

- Docker & Docker Compose (v2+)
- (Optional) Python 3.8+ and `pip` if you want to run scripts locally
- 8 GB RAM (for local development)

## 3. Directory Structure

```
├── data/                         # Static exports (CSV & Parquet)
├── publish.py                    # Multi-threaded Redis publisher
├── storage_writer.py             # Redis → MongoDB writer
├── redis_reader_testing.py       # (Optional) Stream tailing script
├── requirements.txt              # Python dependencies
├── Dockerfile                    # Base image for all Python services
└── docker-compose.yml            # Defines Redis, Mongo, publisher, writer services
```

## 4. Configuration

- The default Redis host/port and MongoDB URL are configured in the scripts (`localhost:6379`, `mongodb://localhost:27017`).
- To change, update the `environment` section in `docker-compose.yml` or set environment variables in your shell for local runs:

```bash
env REDIS_HOST=redis
env REDIS_PORT=6379
env MONGO_URL=mongodb://mongo:27017
```

## 5. Running with Docker Compose

1. **Build & start services**
   ```bash
   docker-compose up --build -d
   ```
2. **View logs**
   ```bash
   docker-compose logs -f publisher storage_writer
   ```
   for all logs:
   ```
   docker compose logs --tail=50
   ```
3. **Verify services**
   - Redis: `redis-cli -h localhost -p 6379 PING` ⇒ `PONG`
   - MongoDB: connect with `mongo --host localhost --port 27017` and check `use fitness_tracker`

## 6. Initial Load of Static Exports

If you wish to bulk-load the existing CSV/Parquet exports into MongoDB (bypassing the Redis streams):

1. Install dependencies and start a Python REPL:
   ```bash
   pip install pandas pyarrow pymongo
   python
   ```
2. Run:
   ```python
   import pandas as pd
   from pymongo import MongoClient

   client = MongoClient("mongodb://localhost:27017")
   db = client.fitness_tracker

   # Load users
   df = pd.read_csv('data/users.csv')
   df.to_dict('records') and db.users.insert_many(...)

   # Similarly for devices, sleep_sessions, nutrition_logs, feedback_events

   # For Parquet:
   df = pd.read_parquet('data/fitness_events.parquet')
   db.fitness_events.insert_many(df.to_dict('records'))
   ```

## 7. Running the Optional Reader

For debugging or live monitoring:

```bash
python redis_reader_testing.py
```

## 8. Verifying Data in MongoDB

1. **Mongo Shell**
   ```bash
   mongo --host localhost --port 27017
   > use fitness_tracker
   > db.fitness_events.count()
   > db.users.findOne()
   ```
2. **MongoDB Compass**: connect to `mongodb://localhost:27017` and inspect collections.

## 9. Stopping & Cleaning Up

```bash
docker-compose down
# to remove volumes (data):
docker-compose down -v
```

## 10. Next Steps & Integration

- **ML/LLM**: Tail `fitness_events` and `sleep_sessions` streams to compute real-time features in a new container.
- **Analytics**: Schedule daily jobs (e.g., with Airflow) to aggregate `fitness_events` into summary tables.
- **UI/UX**: Build a Streamlit or FastAPI frontend that reads Redis hashes for live metrics and Mongo for history.
- **Production**: Split each service into its own image, add logging, metrics, and deploy on Kubernetes with Secrets and ConfigMaps.



to run fastapi: uvicorn llm.app:app --reload
