from typing import Dict, Any, List, Tuple
import numpy as np
from .config import settings
from .utils import rrf

# Try to import CrossEncoder, fallback if not available
try:
    from sentence_transformers import CrossEncoder
    CROSS_ENCODER_AVAILABLE = True
except ImportError:
    CROSS_ENCODER_AVAILABLE = False
    print("⚠️  CrossEncoder not available, reranking will be disabled")

def _bm25_scores(bm25, texts: List[str], query: str) -> List[float]:
    if bm25 is None or not texts:
        return []
    return bm25.get_scores(query.split())

class HybridRetriever:
    def __init__(self, store):
        self.store = store
        if CROSS_ENCODER_AVAILABLE and settings.use_reranker:
            self.reranker = CrossEncoder(settings.rerank_model)
        else:
            self.reranker = None
            if settings.use_reranker:
                print("⚠️  Reranking disabled - CrossEncoder not available")

    def _dense_search(self, query: str, top_k: int, hot=False) -> List[Tuple[int, float]]:
        # Skip dense search if FAISS is disabled
        if hot and self.store.faiss_hot is None:
            return []
        if not hot and self.store.faiss_stable is None:
            return []
            
        model = self.store.model
        qv = model.encode([query], convert_to_numpy=True, normalize_embeddings=True)[0]
        if hot and self.store.faiss_hot is not None:
            D, I = self.store.faiss_hot.search(np.array([qv]).astype('float32'), top_k)
            return [(self.store.hot_ids[i], float(d)) for d, i in zip(D[0], I[0]) if i != -1]
        if not hot and self.store.faiss_stable is not None:
            D, I = self.store.faiss_stable.search(np.array([qv]).astype('float32'), top_k)
            return [(self.store.stable_ids[i], float(d)) for d, i in zip(D[0], I[0]) if i != -1]
        return []

    def _bm25_search(self, query: str, top_k: int, hot=False) -> List[Tuple[int, float]]:
        if hot and self.store.bm25_hot is not None:
            scores = _bm25_scores(self.store.bm25_hot, self.store.hot_texts, query)
            ranked = np.argsort(scores)[::-1][:top_k]
            return [(self.store.hot_ids[i], float(scores[i])) for i in ranked]
        if not hot and self.store.bm25_stable is not None:
            scores = _bm25_scores(self.store.bm25_stable, self.store.stable_texts, query)
            ranked = np.argsort(scores)[::-1][:top_k]
            return [(self.store.stable_ids[i], float(scores[i])) for i in ranked]
        return []

    def search(self, query: str, filters: Dict[str, Any]) -> List[Dict[str, Any]]:
        # First-pass dense + BM25 on both stable/hot, then RRF merge
        dn_stable = self._dense_search(query, settings.ann_top_k, hot=False)
        dn_hot    = self._dense_search(query, settings.ann_top_k, hot=True)
        bm_stable = self._bm25_search(query, settings.bm25_top_k, hot=False)
        bm_hot    = self._bm25_search(query, settings.bm25_top_k, hot=True)

        # Convert to ranking dicts for RRF
        def rank_dict(pairs):
            # Convert scores to ranks (descending); if already similarity, higher is better
            sorted_pairs = sorted(pairs, key=lambda x: x[1], reverse=True)
            return {doc_id: score for doc_id, score in sorted_pairs}

        merged_scores = rrf([rank_dict(dn_stable), rank_dict(dn_hot), rank_dict(bm_stable), rank_dict(bm_hot)], k=settings.rrf_k)
        
        # Apply metadata filters
        if filters:
            filtered = {}
            for doc_id, score in merged_scores.items():
                try:
                    docs = self.store.get_docs_by_ids([doc_id])
                    if docs and _passes_filters(docs[0]["meta"], filters):
                        filtered[doc_id] = score
                except Exception:
                    continue
            merged_scores = filtered

        top_n = sorted(merged_scores.items(), key=lambda x: x[1], reverse=True)[:settings.keep_top_n]
        docs = self.store.get_docs_by_ids([doc_id for doc_id, _ in top_n])

        # Deduplicate by vendor_id to ensure diversity
        seen_vendors = set()
        deduped_docs = []
        for doc in docs:
            vendor_id = doc["meta"].get("vendor_id")
            if vendor_id not in seen_vendors:
                seen_vendors.add(vendor_id)
                deduped_docs.append(doc)
        docs = deduped_docs
        print(f"   After deduplication: {len(docs)} unique vendors from {len(top_n)} results")

        # Ambiguity check
        ambiguous = False
        if len(top_n) >= 3:
            s1 = top_n[0][1]; s3 = top_n[2][1]
            ambiguous = (s1 - s3) < settings.ambiguity_delta
        
        # Optional rerank on the top-3 if ambiguous
        if settings.use_reranker and ambiguous and self.reranker is not None:
            try:
                pairs = [(doc, self._salient_text(doc)) for doc in docs[:3]]
                inputs = [(query, txt) for _, txt in pairs]
                scores = self.reranker.predict(inputs)
                order = np.argsort(scores)[::-1]
                docs[:3] = [docs[i] for i in order]
            except Exception:
                pass  # Continue without reranking if it fails

        # Limit context to top-3 with salient snippets
        for d in docs[:settings.context_top_n]:
            try:
                d["snippet"] = self._salient_text(d)
            except Exception:
                d["snippet"] = d["meta"].get("title", "")

        return docs[:settings.keep_top_n]

    def _salient_text(self, doc):
        try:
            # title + first sentence of description (cheap salience)
            title = doc["meta"]["title"]
            body = doc["text"]
            
            # Get first sentence properly
            sentences = body.split(".")
            first = sentences[0].strip() if sentences else body
            
            return f"{title}: {first}"
        except Exception as e:
            return doc["meta"].get("title", "Error generating salient text")

def _passes_filters(meta: Dict[str, Any], filters: Dict[str, Any]) -> bool:
    city = filters.get("city")
    if city and meta.get("city","").lower() != city.lower():
        return False
    headcount = filters.get("headcount")
    if headcount and not (meta.get("headcount_min",0) <= headcount <= meta.get("headcount_max",10**9)):
        return False
    budget = filters.get("budget")
    if budget and not (meta.get("price_min",0) <= budget <= meta.get("price_max",10**12)):
        return False
    occasion = filters.get("occasion")
    if occasion and occasion.lower() not in [o.lower() for o in meta.get("occasion",[])]:
        return False
    return True
