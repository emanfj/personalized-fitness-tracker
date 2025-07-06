# Personalized Fitness Tracker

## 1. Project Overview

This repository implements a real-time data pipeline using Redis Streams and MongoDB, containerized with Docker Compose. It consists of:

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
