import os
import logging
from datetime import datetime

from fastapi import FastAPI, HTTPException, Body
from fastapi.responses import JSONResponse
from llm.user_context import build_context
from llm.plan_generator import generate_plan, MONGO_URI, DB_NAME
from pymongo import MongoClient
import uvicorn

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="AI Fitness & Nutrition Coach",
    version="0.2.0"
)

@app.get("/")
def root():
    return {"msg": "AI Fitness & Nutrition API up."}

@app.get("/workout/{user_id}")
async def get_workout(user_id: str):
    ctx = await build_context(user_id)
    if not ctx:
        raise HTTPException(status_code=404, detail=f"User {user_id} not found")
    try:
        plan = generate_plan(user_id, ctx, "workout")
        return JSONResponse(content=[p.dict() for p in plan])
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Unexpected error generating workout for {user_id}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/nutrition/{user_id}")
async def get_nutrition(user_id: str):
    ctx = await build_context(user_id)
    if not ctx:
        raise HTTPException(status_code=404, detail=f"User {user_id} not found")
    try:
        meals = generate_plan(user_id, ctx, "nutrition")
        return JSONResponse(content=meals)
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Unexpected error generating nutrition for {user_id}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.post("/feedback/{user_id}")
def post_feedback(user_id: str, payload: dict = Body(...)):
    try:
        client = MongoClient(MONGO_URI)
        db = client[DB_NAME]
        record = {
            "user_id": user_id,
            "event_ts": datetime.utcnow().isoformat(),
            **payload
        }
        db.feedback_events.insert_one(record)
        return {"msg": "Feedback saved in feedback_events."}
    except Exception as e:
        logger.error(f"Feedback save failed for {user_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to save feedback")

@app.get("/plans/{user_id}/history")
def get_history(user_id: str, plan_type: str = None):
    try:
        client = MongoClient(MONGO_URI)
        db = client[DB_NAME]
        query = {"user_id": user_id}
        if plan_type:
            query["type"] = plan_type
        docs = []
        cursor = db.plans.find(query).sort("time", -1).limit(10)
        # cursor = db.plans.find(query).sort("time", -1).limit(1) # For testing, limit to 1

        for doc in cursor:
            doc["_id"] = str(doc["_id"])
            docs.append(doc)
        return docs
    except Exception as e:
        logger.error(f"History retrieval failed for {user_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve history")

if __name__ == "__main__":
    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", 8000)),
        reload=True,
        log_level="info"
    )
