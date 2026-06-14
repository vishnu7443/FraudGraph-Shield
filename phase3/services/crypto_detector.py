import json
import os
import structlog
from typing import Optional, Dict
from core.config import settings

logger = structlog.get_logger()

class CryptoDetector:
    def __init__(self, registry_path: Optional[str] = None):
        if not registry_path:
            current_dir = os.path.dirname(os.path.abspath(__file__))
            registry_path = os.path.abspath(os.path.join(current_dir, "../data/vda_registry.json"))
            
        self.registry = []
        try:
            if os.path.exists(registry_path):
                with open(registry_path, "r", encoding="utf-8") as f:
                    self.registry = json.load(f)
                logger.info("crypto_registry_loaded", size=len(self.registry))
            else:
                logger.error("crypto_registry_file_missing", path=registry_path)
        except Exception as e:
            logger.error("crypto_registry_load_failed", error=str(e))

    def detect_crypto(self, destination_name: str) -> Dict:
        """
        Scans destination name to see if it matches any known VDA exchange or its aliases.
        Returns detection metadata including confidence and the configured risk boost.
        """
        if not destination_name:
            return {
                "is_crypto": False,
                "exchange": None,
                "confidence": 0.0,
                "risk_boost": 0
            }
            
        norm_name = destination_name.strip().upper()
        
        for entry in self.registry:
            name = entry["name"]
            
            # 1. Direct exact match
            if norm_name == name:
                return {
                    "is_crypto": True,
                    "exchange": name,
                    "confidence": 1.0,
                    "risk_boost": settings.CRYPTO_EXIT_BOOST
                }
            
            # 2. Alias/substring match
            for alias in entry.get("aliases", []):
                alias_upper = alias.upper()
                if alias_upper in norm_name or norm_name in alias_upper:
                    # Longer exact alias match yields higher confidence
                    confidence = 0.95 if alias_upper in norm_name else 0.80
                    return {
                        "is_crypto": True,
                        "exchange": name,
                        "confidence": confidence,
                        "risk_boost": settings.CRYPTO_EXIT_BOOST
                    }
                    
        return {
            "is_crypto": False,
            "exchange": None,
            "confidence": 0.0,
            "risk_boost": 0
        }

# Global singleton instance
detector = CryptoDetector()
