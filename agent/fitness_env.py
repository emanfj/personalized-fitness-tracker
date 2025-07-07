import gym
from gym import spaces
import numpy as np
from redis import Redis
from collections import deque

class FitnessEnv(gym.Env):
    """
    A minimal Gym-style wrapper around your Redis streams.
    State is a 1D float vector of last-N features.
    Action is a 2D vector: [delta_intensity, delta_duration].
    """

    def __init__(self,
                 redis_host="redis", redis_port=6379,
                 window_size=30):
        super().__init__()
        self.redis = Redis(host=redis_host, port=redis_port, decode_responses=True)
        self.window_size = window_size

        # Example: 5 features (avg_hr, avg_pace, exertion, sleep_quality, nutrition_score)
        D = 5
        self.observation_space = spaces.Box(-np.inf, np.inf, shape=(D,), dtype=np.float32)
        self.action_space      = spaces.Box(-1.0, 1.0, shape=(2,), dtype=np.float32)

        # rolling buffer for features
        self.buffer = deque(maxlen=window_size)

    def reset(self):
        # clear buffer
        self.buffer.clear()
        # seed with zeros
        initial = np.zeros(self.observation_space.shape, dtype=np.float32)
        for _ in range(self.window_size):
            self.buffer.append(initial)
        return initial

    def _fetch_features(self):
        # pull last window_size events from Redis
        entries = self.redis.xrevrange("fitness:events", count=self.window_size)
        # compute simple stats
        hrs = [float(e[1].get("heart_rate_bpm", 0)) for e in entries]
        steps = [float(e[1].get("step_increment", 0)) for e in entries]
        avg_hr = np.mean(hrs) if hrs else 0.0
        avg_step = np.mean(steps) if steps else 0.0
        # placeholders for demonstration
        exertion = float(self.redis.get("latest_exertion") or 0)
        sleep_q = float(self.redis.get("latest_sleep_quality") or 0)
        nutri = float(self.redis.get("latest_nutrition_score") or 0)
        return np.array([avg_hr, avg_step, exertion, sleep_q, nutri], dtype=np.float32)

    def step(self, action):
        """
        action: [delta_intensity, delta_duration]
        We simulate the effect by publishing a plan update, then reading new features.
        Reward is negative L2 of action (encourage small changes) for this prototype.
        """
        # publish to plan_updates
        delta_intensity, delta_duration = action.tolist()
        self.redis.xadd("plan_updates", {
            "delta_intensity": str(delta_intensity),
            "delta_duration":  str(delta_duration),
        })

        # get next observation
        obs = self._fetch_features()
        self.buffer.append(obs)
        state = np.stack(self.buffer).mean(axis=0)

        # dummy reward
        reward = -np.linalg.norm(action)  
        done = False
        return state, reward, done, {}
