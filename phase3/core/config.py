import os

class Settings:
    CRYPTO_EXIT_BOOST: int = int(os.getenv("CRYPTO_EXIT_BOOST", 20))
    
    # Thresholds for severity levels
    SEVERITY_THRESHOLD_CRITICAL: float = 90.0
    SEVERITY_THRESHOLD_HIGH: float = 75.0
    SEVERITY_THRESHOLD_MEDIUM: float = 50.0

    # Vault alert threshold for automated fraud events insertion
    VAULT_ALERT_THRESHOLD: float = float(os.getenv("VAULT_ALERT_THRESHOLD", 80.0))

settings = Settings()
