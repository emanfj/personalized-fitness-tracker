from stable_baselines3 import PPO
from fitness_env import FitnessEnv

def main():
    env = FitnessEnv()
    model = PPO("MlpPolicy", env, verbose=1)
    model.learn(total_timesteps=200_000)
    model.save("models/fitness_agent_ppo")

if __name__ == "__main__":
    main()
