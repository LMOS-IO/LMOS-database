from secrets import token_hex
import hashlib
from lmos_config import config

def generate_api_key():
    prefix = config.auth.key_prefix
    suffix = token_hex(64)
    return f"{prefix}_{suffix}"

def hash_str(api_key:str, is_api_key=False) -> str:
    if is_api_key:
        hashable = api_key.split("_")[-1]
    else:
        hashable = api_key
    return hashlib.sha512(hashable.encode(), usedforsecurity=True).hexdigest()
