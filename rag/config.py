from pydantic import BaseModel
from typing import List, Optional

class Settings(BaseModel):
    # Embeddings and reranker
    # NOTE: Currently disabled to prevent segfaults. BM25-only mode.
    embed_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    rerank_model: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"
    use_reranker: bool = False  # Disabled - enable once segfault issues resolved

    # Retrieval knobs
    ann_top_k: int = 24
    bm25_top_k: int = 24
    rrf_k: int = 60
    keep_top_n: int = 15  # Fetch more initially to ensure diversity after deduplication
    context_top_n: int = 3
    ambiguity_delta: float = 0.06

    # LangGraph / timeouts (seconds)
    tool_timeout_s: float = 30.0  # Increased for LLM API calls (typically 1-5s)

    # Thresholds
    low_confidence_tau: float = 0.7

    # Routing
    small_model: str = "gpt-4o-mini"  # via litellm
    mid_model: str = "gpt-4o-mini"
    large_model: str = "gpt-4o"       # gated for proposals

    # Currency
    currency: str = "AED"

settings = Settings()
