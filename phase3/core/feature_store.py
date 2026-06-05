import redis
import numpy as np
import joblib
import json
import structlog
from typing import Optional, Dict, List

logger = structlog.get_logger()

class FeatureStore:
    def __init__(self, redis_url: str, preprocessor_path: str, ttl_seconds: int = 3600):
        self.client = redis.from_url(redis_url, decode_responses=False)
        self.preprocessor = joblib.load(preprocessor_path)
        self.ttl = ttl_seconds
        self.prefix = "fraudgraph:features:"

    def _key(self, account_id: int) -> str:
        return f"{self.prefix}{account_id}"

    def get(self, account_id: int) -> Optional[np.ndarray]:
        try:
            raw = self.client.get(self._key(account_id))
            if raw is None:
                return None
            features = np.frombuffer(raw, dtype=np.float32)
            logger.debug("feature_store_hit", account_id=account_id)
            return features
        except Exception as e:
            logger.warn("feature_store_get_failed", error=str(e), account_id=account_id)
            return None

    def set(self, account_id: int, features: np.ndarray) -> None:
        try:
            self.client.setex(
                self._key(account_id),
                self.ttl,
                features.astype(np.float32).tobytes()
            )
            logger.debug("feature_store_write", account_id=account_id)
        except Exception as e:
            logger.warn("feature_store_set_failed", error=str(e), account_id=account_id)

    def get_or_compute(self, account_id: int, raw_data: dict) -> np.ndarray:
        cached = self.get(account_id)
        if cached is not None:
            return cached
        
        # Cache miss — compute and store
        import pandas as pd
        if isinstance(raw_data, dict):
            df_raw = pd.DataFrame([raw_data])
        elif isinstance(raw_data, list):
            df_raw = pd.DataFrame(raw_data)
        else:
            df_raw = raw_data
            
        features_df = self.preprocessor.transform(df_raw)
        features = features_df.values[0].astype(np.float32)
        self.set(account_id, features)
        return features

    def invalidate(self, account_id: int) -> None:
        try:
            self.client.delete(self._key(account_id))
        except Exception as e:
            logger.warn("feature_store_invalidate_failed", error=str(e), account_id=account_id)

    def warm_cache(self, account_ids: list, raw_data_batch: list) -> int:
        """Pre-populate cache for known accounts at startup. Returns count cached."""
        count = 0
        import pandas as pd
        for acc_id, raw in zip(account_ids, raw_data_batch):
            if self.get(acc_id) is None:
                df_raw = pd.DataFrame([raw])
                features = self.preprocessor.transform(df_raw).values[0].astype(np.float32)
                self.set(acc_id, features)
                count += 1
        logger.info("cache_warmed", accounts_cached=count)
        return count

    def health_check(self) -> bool:
        try:
            self.client.ping()
            return True
        except Exception:
            return False

class InMemoryFeatureStore(FeatureStore):
    """Fallback when Redis is unavailable. Not for production."""
    def __init__(self, preprocessor_path: str):
        self.preprocessor = joblib.load(preprocessor_path)
        self._cache: Dict[int, np.ndarray] = {}

    def get(self, account_id: int) -> Optional[np.ndarray]:
        return self._cache.get(account_id)

    def set(self, account_id: int, features: np.ndarray) -> None:
        self._cache[account_id] = features

    def invalidate(self, account_id: int) -> None:
        if account_id in self._cache:
            del self._cache[account_id]

    def health_check(self) -> bool:
        return True
