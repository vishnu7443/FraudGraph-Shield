# phase3/warm_cache.py
#
# Script to pre-populate Redis feature store cache with zero vectors or preprocessed arrays
# at startup, ensuring sub-millisecond latencies for demo scoring requests.

import os
import redis
import numpy as np
import structlog
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

    # Pre-populate feature vectors for accounts in the graph (0 to 9082)
    # Each vector is 300 float32 features
    features_bytes = np.zeros(300, dtype=np.float32).tobytes()
    
    pipeline = client.pipeline()
    count = 0
    total_accounts = 9083
    
    for acc_id in range(total_accounts):
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
