import os
import torch.nn as nn
from multiprocessing import freeze_support

from stable_baselines3 import PPO
from stable_baselines3.common.vec_env import SubprocVecEnv, VecMonitor, VecNormalize
from fitness_env import FitnessEnv

def make_env():
    return FitnessEnv(
        redis_host="localhost",
        redis_port=6379,
        window_size=30,
        max_episode_steps=100,
    )

def main():
    freeze_support()

    num_envs = 4
    # 1) create 4 parallel environments
    envs = SubprocVecEnv([make_env for _ in range(num_envs)])
    # 2) track episode stats
    envs = VecMonitor(envs)
    # 3) normalize observations (and rewards if you like)
    envs = VecNormalize(envs, norm_obs=True, norm_reward=True, clip_obs=10.0)

    # 4) load existing model and override hyperparameters
    model = PPO.load(
        "models/fitness_agent_ppo_after500k",
        env=envs,
        reset_num_timesteps=False,
        custom_objects={
            "n_steps": 4096,
            "batch_size": 4096 // num_envs,
            "gamma": 0.995,
            "gae_lambda": 0.98,
            "learning_rate": 5e-4,
            "clip_range": 0.05,

        },
        tensorboard_log="./tensorboard_logs/",
    )
    # model = PPO(
    #     "MlpPolicy",
    #     env=envs,
    #     n_steps=4096,
    #     batch_size=4096 // num_envs,
    #     gamma=0.995,
    #     gae_lambda=0.98,
    #     learning_rate=5e-4,
    #     clip_range=0.05,
    #     tensorboard_log="./tensorboard_logs/",
    #     verbose=1,
    # )

    # 5) resume training
    model.learn(
        total_timesteps=30_00_000,
        tb_log_name="ppo_fitness_after3kk",
        reset_num_timesteps=False,
        progress_bar=True,

    )

    # 6) save model and normalization stats
    model.save("models/fitness_agent_ppo_after3kk.zip")
    envs.save("models/vecnormalize_stats.pkl")
    print("Training completed and model saved!")

if __name__ == "__main__":
    main()
