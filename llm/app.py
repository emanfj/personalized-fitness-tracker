# llm/app.py

from fastapi import FastAPI, HTTPException
from user_context   import build_context
from plan_generator import generate_workout_plan, generate_nutrition_plan

app = FastAPI(
    title="AI Fitness & Nutrition Coach",
    version="0.1.0",
)

@app.get("/")
def read_root():
    return {"message": "Welcome to the AI Fitness & Nutrition Coach API"}

@app.get("/workout/{user_id}")
def workout(user_id: str):
    ctx = build_context(user_id)
    if not ctx:
        raise HTTPException(status_code=404, detail=f"User {user_id} not found")
    plan = generate_workout_plan(ctx, model="llama3.2:3b")
    return plan

@app.get("/nutrition/{user_id}")
def nutrition(user_id: str):
    ctx = build_context(user_id)
    if not ctx:
        raise HTTPException(status_code=404, detail=f"User {user_id} not found")
    plan = generate_nutrition_plan(ctx, model="llama3.2:3b")
    return plan
