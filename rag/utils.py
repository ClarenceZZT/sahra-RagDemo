import re, json, os, hashlib, time, asyncio
from typing import Dict, Any, List

def normalize_query(q: str) -> str:
    q = q.strip().lower()
    q = re.sub(r"\s+", " ", q)
    return q

def rrf(scores_lists: List[Dict[int, float]], k: int = 60) -> Dict[int, float]:
    merged = {}
    for scores in scores_lists:
        # scores: doc_id -> rank (or score); convert to reciprocal of rank
        ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        for rank, (doc_id, _) in enumerate(ranked, start=1):
            merged[doc_id] = merged.get(doc_id, 0.0) + 1.0 / (k + rank)
    return merged

def lf_bucket(x: float, step: int = 1000) -> str:
    try:
        i = int(x) // step
        return f"{i*step}-{(i+1)*step}"
    except:
        return "na"

def hash_key(s: str) -> str:
    return hashlib.sha256(s.encode()).hexdigest()

class TTLCache:
    def __init__(self, ttl_seconds: int = 21600, max_items: int = 1000):
        self.ttl = ttl_seconds
        self.max_items = max_items
        self.store = {}

    def get(self, key: str):
        now = time.time()
        item = self.store.get(key)
        if not item: return None
        val, ts = item
        if now - ts > self.ttl:
            del self.store[key]
            return None
        return val

    def set(self, key: str, val):
        if len(self.store) >= self.max_items:
            # pop arbitrary (demo)
            self.store.pop(next(iter(self.store)))
        self.store[key] = (val, time.time())

async def with_timeout(coro, timeout_s: float):
    return await asyncio.wait_for(coro, timeout=timeout_s)
