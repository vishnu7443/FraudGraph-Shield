# phase3/warm_cache.py
#
# Script to pre-populate Redis feature store cache with zero vectors or preprocessed arrays
# at startup, ensuring sub-millisecond latencies for demo scoring requests.

import os
# pyrefly: ignore [missing-import]
import redis
# pyrefly: ignore [missing-import]
import numpy as np
# pyrefly: ignore [missing-import]
import structlog
# pyrefly: ignore [missing-import]
from dotenv import load_dotenv

load_dotenv()
logger = structlog.get_logger()

def warm_cache():
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
    prefix = "fraudgraph:features:"
    
    logger.info("warming_cache_started", redis_url=redis_url)
    
    try:
        client = redis.from_url(redis_url)
        client.ping()
        logger.info("redis_connected_successfully")
    except Exception as e:
        logger.warning("redis_unreachable_skipping_cache_warm", error=str(e))
        return

    # Pre-populate distinct feature vectors for accounts in the graph (0 to 9082)
    # Each vector is 300 float32 features, generated deterministically based on account ID
    pipeline = client.pipeline()
    count = 0
    total_accounts = 9083
    
    for acc_id in range(total_accounts):
        # Generate varied features deterministically using acc_id as seed
        rng = np.random.default_rng(acc_id)
        # Use small values centered around typical feature scaling
        features = rng.normal(0, 0.5, 300).astype(np.float32)
        
        # Override some key features like tenure_days, product_complexity, peer_deviation_composite
        # so they reside in standard positive bounds
        features[0] = float(rng.integers(10, 1000)) # tenure_days
        features[1] = float(rng.uniform(0.1, 5.0))   # product_complexity
        features[2] = float(rng.uniform(-2.0, 5.0))  # peer_deviation
        
        features_bytes = features.tobytes()
        pipeline.setex(f"{prefix}{acc_id}", 3600 * 24, features_bytes)
        count += 1
        
        # Execute in batches of 1000 to avoid excessive memory hold
        if count % 1000 == 0:
            pipeline.execute()
            logger.info("cache_warming_progress", count=count)
            
    # Execute remaining
    pipeline.execute()
    logger.info("cache_warming_completed", total_cached=count)

if __name__ == "__main__":
    warm_cache()
