import os, json, sqlite3, time
from typing import List, Dict, Any, Tuple
import numpy as np
import pandas as pd
import faiss
from rank_bm25 import BM25Okapi

# Try to import sentence_transformers, fallback to alternative if not available
try:
    from sentence_transformers import SentenceTransformer
    SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError:
    SENTENCE_TRANSFORMERS_AVAILABLE = False
    print("⚠️  sentence-transformers not available, will use alternative embedding method")

DB_PATH = os.environ.get("SAHRA_DB", "sahra.db")

def row_to_doc(r):
    """Convert database row to document dict"""
    (id_, vendor_id, title, city, hmin, hmax, pmin, pmax, dur, occ, tags, upd, desc) = r
    text = f"{title}. {desc} (City: {city}; Capacity: {hmin}-{hmax}; Price: {pmin}-{pmax}; Occasions: {occ}; Tags: {tags})"
    meta = dict(
        id=id_, vendor_id=vendor_id, title=title, city=city, 
        headcount_min=hmin, headcount_max=hmax, 
        price_min=pmin, price_max=pmax, 
        duration_hours=dur,
        occasion=[o.strip() for o in str(occ).split(',') if o], 
        tags=[t.strip() for t in str(tags).split(',') if t],
        updated_at=upd
    )
    return {"id": id_, "text": text, "meta": meta}

class DualIndexStore:
    def __init__(self, embed_model: str):
        # SAFE MODE: Skip embedding model to prevent segfaults
        # TODO: Re-enable embeddings when segfault issues are resolved
        self.model = None  # Skip model loading to prevent segfaults
        
        self.conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        self.conn.execute("PRAGMA foreign_keys = ON")
        self._init_db()

        self.faiss_stable = None
        self.faiss_hot = None
        self.bm25_stable = None
        self.bm25_hot = None
        self.stable_texts = []
        self.hot_texts = []
        self.stable_ids = []
        self.hot_ids = []

    def _init_db(self):
        cur = self.conn.cursor()
        cur.execute(
            '''CREATE TABLE IF NOT EXISTS offers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                vendor_id TEXT,
                title TEXT,
                city TEXT,
                headcount_min INTEGER,
                headcount_max INTEGER,
                price_min REAL,
                price_max REAL,
                duration_hours REAL,
                occasion TEXT,
                tags TEXT,
                updated_at TEXT,
                description TEXT,
                is_hot INTEGER DEFAULT 0
            )'''
        )
        self.conn.commit()

    def clear(self):
        self.conn.execute("DELETE FROM offers")
        self.conn.commit()

    def add_offers_from_df(self, df: pd.DataFrame, mark_hot=False):
        cols = ["vendor_id","title","city","headcount_min","headcount_max","price_min","price_max",
                "duration_hours","occasion","tags","updated_at","description"]
        for _, row in df.iterrows():
            values = [row.get(c) for c in cols]
            self.conn.execute(
                "INSERT INTO offers (vendor_id,title,city,headcount_min,headcount_max,price_min,price_max,duration_hours,occasion,tags,updated_at,description,is_hot) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
                [*values, 1 if mark_hot else 0]
            )
        self.conn.commit()

    def load_corpus(self) -> Tuple[List[Dict[str,Any]], List[Dict[str,Any]]]:
        cur = self.conn.cursor()
        cur.execute("SELECT id,vendor_id,title,city,headcount_min,headcount_max,price_min,price_max,duration_hours,occasion,tags,updated_at,description FROM offers WHERE is_hot=0")
        stable_rows = cur.fetchall()
        cur.execute("SELECT id,vendor_id,title,city,headcount_min,headcount_max,price_min,price_max,duration_hours,occasion,tags,updated_at,description FROM offers WHERE is_hot=1")
        hot_rows = cur.fetchall()

        stable_docs = [row_to_doc(r) for r in stable_rows]
        hot_docs = [row_to_doc(r) for r in hot_rows]
        return stable_docs, hot_docs

    def build_indexes(self):
        stable_docs, hot_docs = self.load_corpus()
        
        # SAFE MODE: Skip FAISS, use BM25 only
        # TODO: Re-enable FAISS when segfault issues are resolved
        
        if stable_docs:
            self.stable_texts = [d["text"] for d in stable_docs]
            self.stable_ids = [d["id"] for d in stable_docs]
            self.faiss_stable = None  # Skip FAISS to prevent segfaults
            
        if hot_docs:
            self.hot_texts = [d["text"] for d in hot_docs]
            self.hot_ids = [d["id"] for d in hot_docs]
            self.faiss_hot = None

        # BM25 indexes - always build these
        from rank_bm25 import BM25Okapi
        if self.stable_texts:
            self.bm25_stable = BM25Okapi([t.split() for t in self.stable_texts])
        if self.hot_texts:
            self.bm25_hot = BM25Okapi([t.split() for t in self.hot_texts])

    def get_docs_by_ids(self, ids: List[int]) -> List[Dict[str,Any]]:
        q = "SELECT id,vendor_id,title,city,headcount_min,headcount_max,price_min,price_max,duration_hours,occasion,tags,updated_at,description FROM offers WHERE id IN ({})".format(",".join(["?"]*len(ids)))
        cur = self.conn.cursor()
        cur.execute(q, ids)
        rows = cur.fetchall()
        return [row_to_doc(r) for r in rows]
