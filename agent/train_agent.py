import os
from multiprocessing import freeze_support

from stable_baselines3 import PPO
from stable_baselines3.common.vec_env import SubprocVecEnv, DummyVecEnv, VecMonitor, VecNormalize
from stable_baselines3.common.callbacks import EvalCallback, StopTrainingOnNoModelImprovement

from fitness_env import FitnessEnv

def make_env():
    return FitnessEnv(
        redis_host="localhost",
        redis_port=6379,
        window_size=30,
        max_episode_steps=100,
    )

def linear_schedule(initial_value: float):
    """
    Returns a function (progress_remaining) → lr
    that linearly anneals from `initial_value` → 0.
    """
    def func(progress_remaining: float) -> float:
        return progress_remaining * initial_value
    return func

def main():
    freeze_support()
    num_envs = 4

    #training envs
    envs = SubprocVecEnv([make_env for _ in range(num_envs)])
    envs = VecMonitor(envs)
    envs = VecNormalize(envs, norm_obs=True, norm_reward=True, clip_obs=10.0)
    #reload normalization if previously saved
    if os.path.exists("models/vecnormalize_stats.pkl"):
        envs = VecNormalize.load("models/vecnormalize_stats.pkl", envs)

    # eval env (deterministic rollouts)
    eval_env = DummyVecEnv([make_env])
    eval_env = VecMonitor(eval_env)
    eval_env = VecNormalize(eval_env, norm_obs=True, norm_reward=True, clip_obs=10.0)
    if os.path.exists("models/vecnormalize_stats.pkl"):
        eval_env = VecNormalize.load("models/vecnormalize_stats.pkl", eval_env)

    #load existing model override key hyperparams
    model = PPO.load(
        "models/fitness_agent_final",
        env=envs,
        reset_num_timesteps=False,
        custom_objects={
            "n_steps": 4096,
            "batch_size": 4096 // num_envs,
            "gamma": 0.995,
            "gae_lambda": 0.98,
            "learning_rate": linear_schedule(3e-4),
            "clip_range": 0.1,
            "ent_coef": 0.01,
            "vf_coef": 0.5,
        },
        tensorboard_log="./tensorboard_logs/",
    )

    #set up evaluation + early stopping
    stop_callback = StopTrainingOnNoModelImprovement(
        max_no_improvement_evals=3,
        min_evals=1,
        verbose=1
    )
    eval_callback = EvalCallback(
        eval_env,
        best_model_save_path="models/",
        log_path="models/",
        eval_freq=100_000,         # run eval every 100k steps
        n_eval_episodes=10,
        deterministic=True,        # use deterministic actions
        callback_on_new_best=stop_callback,
        verbose=1
    )

    # resume training with callbacks
    model.learn(
        total_timesteps=1_000_000,
        tb_log_name="ppo_fitness_final_v2",
        reset_num_timesteps=False,
        progress_bar=True,
        callback=eval_callback,
    )

    # final save
    model.save("models/fitness_agent_final.zip")
    envs.save("models/vecnormalize_stats.pkl")
    print("Training completed and model saved!")

if __name__ == "__main__":
    main()

  