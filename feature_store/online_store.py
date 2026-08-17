import os
import json
import time
from typing import Dict, Any, Optional
from src.utils import get_logger, ensure_dirs

logger = get_logger()

# Optional Redis import
try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False

class OnlineFeatureStore:
    def __init__(self, host: str = "localhost", port: int = 6379, db: int = 0, fallback_file: str = "data/online_store.json"):
        self.fallback_file = fallback_file
        ensure_dirs([os.path.dirname(fallback_file)])
        self.use_redis = False
        
        if REDIS_AVAILABLE:
            try:
                self.r = redis.Redis(host=host, port=port, db=db, socket_connect_timeout=2)
                self.r.ping()
                self.use_redis = True
                logger.info(f"Connected to Redis Feature Store at {host}:{port}")
            except Exception:
                logger.warning("Redis connection failed. Using file-based online store fallback.")
                
        if not self.use_redis:
            self.cache = self._load_fallback_cache()

    def _load_fallback_cache(self) -> Dict[str, Any]:
        if os.path.exists(self.fallback_file):
            try:
                with open(self.fallback_file, "r") as f:
                    return json.load(f)
            except Exception:
                return {}
        return {}

    def _save_fallback_cache(self):
        with open(self.fallback_file, "w") as f:
            json.dump(self.cache, f, indent=2)

    def cache_features(self, address: str, features: Dict[str, Any], ttl_seconds: int = 300):
        """Caches wallet features with a time-to-live (TTL)."""
        address_key = address.lower()
        if self.use_redis:
            try:
                self.r.setex(address_key, ttl_seconds, json.dumps(features))
                logger.info(f"Cached features in Redis for {address_key}")
            except Exception as e:
                logger.error(f"Redis cache save failed: {str(e)}")
        else:
            self.cache[address_key] = {
                "expires_at": time.time() + ttl_seconds,
                "features": features
            }
            self._save_fallback_cache()
            logger.info(f"Cached features in local file for {address_key}")

    def get_cached_features(self, address: str) -> Optional[Dict[str, Any]]:
        """Retrieves cached features if they haven't expired."""
        address_key = address.lower()
        if self.use_redis:
            try:
                val = self.r.get(address_key)
                if val:
                    logger.info(f"Cache hit (Redis) for {address_key}")
                    return json.loads(val)
            except Exception as e:
                logger.error(f"Redis cache retrieve failed: {str(e)}")
        else:
            cached_data = self.cache.get(address_key)
            if cached_data:
                if time.time() < cached_data.get("expires_at", 0):
                    logger.info(f"Cache hit (local file) for {address_key}")
                    return cached_data["features"]
                else:
                    # Clean up expired entry
                    del self.cache[address_key]
                    self._save_fallback_cache()
                    
        return None
