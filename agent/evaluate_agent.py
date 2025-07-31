import os
import numpy as np
from stable_baselines3 import PPO
from fitness_env import FitnessEnv

def evaluate(model_path="models/fitness_agent_ppo", num_steps=100):
    #pickRedis config from env for consistency
    redis_host = os.getenv("REDIS_HOST", "localhost")
    redis_port = int(os.getenv("REDIS_PORT", 6379))
    window_size = int(os.getenv("WINDOW_SIZE", 30))
    max_episode_steps = int(os.getenv("MAX_EPISODE_STEPS", 100))
    
    env = FitnessEnv(redis_host=redis_host, redis_port=redis_port,
                     window_size=window_size, max_episode_steps=max_episode_steps)

    print(f"Loading model from: {model_path}")
    model = PPO.load(model_path, env=env)

    obs, info = env.reset()
    total_reward = 0

    print("\nStep | Action               | Reward    | Cumulative Reward")
    print("-" * 55)
    for step in range(num_steps):
        action, _states = model.predict(obs, deterministic=True)
        obs, reward, terminated, truncated, info = env.step(action)
        total_reward += reward
        print(f"{step+1:>4} | {action} | {reward:8.3f} | {total_reward:16.3f}")
        if terminated or truncated:
            print(f"Episode finished after {step+1} steps.")
            break

    print(f"\nEvaluation completed. Cumulative reward: {total_reward:.3f}")

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--model_path", default="models/fitness_agent_ppo", help="Path to saved agent model")
    parser.add_argument("--num_steps", type=int, default=100, help="Number of evaluation steps")
    args = parser.parse_args()

    evaluate(model_path=args.model_path, num_steps=args.num_steps)

# python agent/evaluate_agent.py --num_steps 100
# python agent/evaluate_agent.py --model_path models/fitness_agent_ppo --num_steps 100