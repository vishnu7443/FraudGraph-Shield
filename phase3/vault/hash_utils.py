import hashlib

def hash_account_id(account_id: int) -> str:
    """
    Computes the SHA-256 hash of the string representation of an account ID.
    Used for lookups to protect raw account numbers.
    """
    if account_id is None:
        return ""
    return hashlib.sha256(str(account_id).strip().encode('utf-8')).hexdigest()
