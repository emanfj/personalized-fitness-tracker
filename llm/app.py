# app.py

from fastapi import FastAPI, HTTPException
from user_context import load_user_context    
from plan_generator import generate_workout_plan, generate_nutrition_plan

app = FastAPI(
    title="AI Fitness & Nutrition Coach",
    description="Separate endpoints for workouts and meal plans",
)

@app.get("/workout/{user_id}")
def workout(user_id: str):
    """
    Return a 7-day workout plan for user_id.
    """
    try:
        ctx  = load_user_context(user_id)
        plan = generate_workout_plan(ctx)
        return {"user_id": user_id, "workout_plan": plan}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/nutrition/{user_id}")
def nutrition(user_id: str):
    """
    Return a 3-day meal plan for user_id.
    """
    try:
        ctx  = load_user_context(user_id)
        plan = generate_nutrition_plan(ctx)
        return {"user_id": user_id, "nutrition_plan": plan}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
