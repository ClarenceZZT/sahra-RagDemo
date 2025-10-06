import json, os
from .utils import TTLCache, hash_key, normalize_query, lf_bucket

qr_cache = TTLCache(ttl_seconds=21600, max_items=512)   # 6h
completion_cache = TTLCache(ttl_seconds=86400, max_items=256)  # 24h

def query_cache_key(query: str, city: str|None, occasion: str|None, headcount: int|None, budget: float|None, season: str|None):
    norm = normalize_query(query)
    parts = [norm, city or "", occasion or "", str((headcount or 0)//10*10), lf_bucket(budget or 0, step=1000), season or ""]
    return hash_key("|".join(parts))
