import os
from stable_baselines3 import PPO
from fitness_env import FitnessEnv

def main():
    redis_host = os.getenv("REDIS_HOST", "localhost")
    redis_port = int(os.getenv("REDIS_PORT", 6379))
    window_size = int(os.getenv("WINDOW_SIZE", 30))
    max_episode_steps = int(os.getenv("MAX_EPISODE_STEPS", 100))

    env = FitnessEnv(redis_host=redis_host, redis_port=redis_port,
                     window_size=window_size, max_episode_steps=max_episode_steps)
    
    model = PPO("MlpPolicy", env, verbose=1, tensorboard_log="./logs", 
            policy_kwargs=None)
    model.learn(total_timesteps=200_000, tb_log_name="ppo_fitness")
    os.makedirs("models", exist_ok=True)
    model.save("models/fitness_agent_ppo")
    print("Training completed and model saved!")

if __name__ == "__main__":
    main()

# once training starts: tensorboard --logdir=logs
