import gymnasium as gym
from gymnasium import spaces
import numpy as np
from redis import Redis
from collections import deque

class FitnessEnv(gym.Env):
    """
    Gym-style RL environment for adaptive workout planning.
    State: window_size x 5 features (buffered)
    Action: [delta_intensity, delta_duration]
    """

    def __init__(self,
                 redis_host="localhost", redis_port=6379,
                 window_size=30,
                 max_episode_steps=100):
        super().__init__()
        self.redis = Redis(host=redis_host, port=redis_port, socket_connect_timeout=1, socket_timeout=1,decode_responses=True, )
        self.window_size = window_size
        self.max_episode_steps = max_episode_steps

        self.n_features = 5  # avg_hr, avg_step, exertion, sleep_quality, nutrition_score
        self.observation_space = spaces.Box(
            -np.inf, np.inf, shape=(self.window_size * self.n_features,), dtype=np.float32)
        self.action_space = spaces.Box(-1.0, 1.0, shape=(2,), dtype=np.float32)
        self.buffer = deque(maxlen=self.window_size)
        self.steps = 0

    def reset(self, seed=None, **kwargs):
        if seed is not None:
            np.random.seed(seed)
        self.buffer.clear()
        initial = np.zeros(self.n_features, dtype=np.float32)
        for _ in range(self.window_size):
            self.buffer.append(initial)
        self.steps = 0
        state = np.concatenate(self.buffer)
        return state, {}

    def _fetch_features(self):
        try:
            entries = self.redis.xrevrange("fitness:events", count=self.window_size)
            hrs   = [float(e[1].get("heart_rate_bpm", 0)) for e in entries]
            steps = [float(e[1].get("step_increment", 0)) for e in entries]
            avg_hr   = np.mean(hrs) if hrs else 0.0
            avg_step = np.mean(steps) if steps else 0.0
            exertion = float(self.redis.get("latest_exertion") or 0)
            sleep_q  = float(self.redis.get("latest_sleep_quality") or 0)
            nutri    = float(self.redis.get("latest_nutrition_score") or 0)
            return np.array([avg_hr, avg_step, exertion, sleep_q, nutri], dtype=np.float32)
        except Exception as e:
            print(f"Error fetching features from Redis: {e}")
            return np.zeros(self.n_features, dtype=np.float32)

    def step(self, action):
        # Publish action
        try:
            delta_intensity, delta_duration = action.tolist()
            self.redis.xadd("plan_updates", {
                "delta_intensity": str(delta_intensity),
                "delta_duration":  str(delta_duration),
            })
        except Exception as e:
            print(f"Error publishing to Redis: {e}")

        obs = self._fetch_features()
        self.buffer.append(obs)
        state = np.concatenate(self.buffer)

        # Reward: small for adjustment, +ve for improved exertion/sleep, -ve for over adjustment
        prev = np.array(self.buffer[-2]) if len(self.buffer) > 1 else np.zeros(self.n_features)
        improvement = obs[2] - prev[2] + obs[3] - prev[3]  # exertion + sleep_quality improvement
        reward = (
            -0.5 * np.linalg.norm(action) +  # discourage big changes
            0.2 * improvement  # encourage good health feedback
        )

        self.steps += 1
        terminated = self.steps >= self.max_episode_steps
        truncated = False
        info = {}

        return state, reward, terminated, truncated, info
