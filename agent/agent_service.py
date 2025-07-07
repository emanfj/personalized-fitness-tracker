import os
import time
import numpy as np
from redis import Redis
from stable_baselines3 import PPO
from fitness_env import FitnessEnv

REDIS_HOST = os.getenv("REDIS_HOST", "redis")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
MODEL_PATH = os.getenv("RL_MODEL_PATH", "models/fitness_agent_ppo.zip")

def main():
    redis = Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)
    # load RL policy
    model = PPO.load(MODEL_PATH, device="cpu")
    env   = FitnessEnv(redis_host=REDIS_HOST, redis_port=REDIS_PORT)
    obs   = env.reset()

    while True:
        action, _ = model.predict(obs, deterministic=True)
        obs, reward, done, info = env.step(action)
        # wait a bit between decisions
        time.sleep(10)

if __name__ == "__main__":
    main()
