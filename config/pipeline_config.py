# =============================================================================
# config/pipeline_config.py
# =============================================================================

import os
from dataclasses import dataclass
from typing import Dict, Any

@dataclass
class RedisConfig:
    host: str = "localhost"
    port: int = 6379
    db: int = 0
    password: str = None
    decode_responses: bool = True
    
@dataclass
class PipelineConfig:
    redis: RedisConfig
    batch_size: int = 100
    processing_interval: int = 5  # seconds
    max_retries: int = 3
    data_retention_hours: int = 24
    
    # Redis keys
    raw_stream_key: str = "fitness:raw"
    processed_stream_key: str = "fitness:processed"
    aggregates_key_prefix: str = "fitness:agg"
    user_metrics_prefix: str = "user:metrics"
    device_status_prefix: str = "device:status"

# Global config
CONFIG = PipelineConfig(
    redis=RedisConfig()
)
