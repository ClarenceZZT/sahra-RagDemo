# SahraEvent RAG Demo

A fast, reliable RAG system for event venue recommendations using Streamlit and LangGraph.

## Features
- **BM25 Search**: Fast keyword-based retrieval (FAISS disabled for stability)
- **LangGraph Pipeline**: Slot extraction, retrieval, validation, and composition
- **Smart Validation**: Missing info detection and staleness checks (14-day threshold)
- **Context-Aware Responses**: Natural venue recommendations with citations
- **Filter Support**: City, occasion, headcount, budget, and date filters
- **Vendor Deduplication**: Ensures diverse results from different vendors
- **14 Sample Venues**: Dubai and Abu Dhabi venues with diverse options

## Quick Start

### Prerequisites
- Python 3.8+
- OpenAI API key

### Setup
1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Set your API key:**
   ```bash
   export OPENAI_API_KEY="your_api_key_here"
   ```

3. **Run the app:**
   ```bash
   streamlit run app.py
   ```

The app will be available at `http://localhost:8501`

### Getting an OpenAI API Key
1. Go to [OpenAI Platform](https://platform.openai.com/api-keys)
2. Create a new API key
3. Add it to your environment

## Project Structure
- `app.py` – Streamlit UI
- `rag/` – Core RAG pipeline
  - `graph.py` – LangGraph orchestration
  - `retriever.py` – Hybrid search with deduplication
  - `store.py` – Dual-index storage
  - `prompts.py` – System prompts
  - `config.py` – Configuration settings
  - `cache.py` – TTL caching
  - `utils.py` – Helper functions
- `data/` – Sample venue datasets
  - `vendors.csv` – Basic dataset (14 unique venues)
  - `vendors_extended.csv` – Extended dataset (24 venues, includes vendor duplicates for testing deduplication)

## Usage
Ask natural language questions like:
- "yacht party in Dubai for 25 people"
- "luxury wedding venue in Abu Dhabi under 50k"
- "beach club for corporate event"

**📖 Demo Resources:**
- **[DEMO_GUIDE.md](DEMO_GUIDE.md)** - Comprehensive testing scenarios organized by feature
- **[DEMO_CHEAT_SHEET.md](DEMO_CHEAT_SHEET.md)** - Quick reference for live demos (copy-paste queries)

### Quick Demo Queries

| Feature | Query | What it Demonstrates |
|---------|-------|---------------------|
| Basic Search | `"yacht party in Dubai"` | BM25 search + city filter |
| Headcount Filter | `"venue for 25 people"` | Capacity-based filtering |
| Budget Filter | `"corporate event under 20k AED"` | Price range filtering |
| Vendor Diversity | `"party venue in Dubai"` | Deduplication (3 unique vendors) |
| Staleness | `"wedding in Abu Dhabi"` | 14-day freshness check |
| Natural Language | `"Hey, sunset vibe for 20 friends DXB"` | Conversational slot extraction |
| Caching | Repeat any query twice | <1s cached response |
| Citations | Any query | [#ID] references in response |



## Summary: What's Ready vs What's Next

### ✅ **Production-Ready (MVP)**
- ✅ Core RAG pipeline with LangGraph orchestration
- ✅ BM25 hybrid search with metadata filters
- ✅ Vendor deduplication for result diversity
- ✅ Dual-index architecture (stable/hot)
- ✅ Staleness detection and display
- ✅ TTL-based caching
- ✅ Citation-enforced responses
- ✅ Model routing (cost-optimized)

### 🟡 **Partially Implemented / MVP Mode**
- 🟡 SQLite instead of Postgres (scalable to ~10K venues)
- 🟡 In-memory cache instead of Redis (single instance only)
- 🟡 Streamlit UI instead of FastAPI (demo/internal use)
- 🟡 Embeddings/FAISS disabled (BM25-only)
- 🟡 Reranker ready but not active

### ❌ **Not Yet Implemented**
- ❌ FastAPI REST endpoints
- ❌ WhatsApp/Stripe/Calendar integrations
- ❌ Real-time vendor availability checks
- ❌ Webhook-based ingestion
- ❌ Precomputed warm paths for seasonal queries
- ❌ Int8 quantized embeddings

### 🎯 **Next Steps for Production**
1. **Scale Storage**: Migrate to Postgres + pgvector when dataset >10K
2. **Enable Dense Search**: Fix segfault issues, re-enable FAISS
3. **Add Redis**: For multi-instance deployment
4. **FastAPI**: Expose REST endpoints for integrations
5. **External Tools**: Vendor availability API, calendar checks
6. **Webhooks**: Real-time vendor updates

---

## Technical Details
- **Storage**: SQLite database with dual-index architecture (stable/hot)
- **Search**: BM25-only mode (FAISS embeddings disabled for stability)
- **Pipeline**: LangGraph orchestration with async nodes
- **Validation**: Automatic detection of missing slots and stale data
- **Citations**: Proper venue ID references for traceability
- **Caching**: TTL-based caching for queries (6h) and completions (24h)
- **Deduplication**: Vendor-level filtering to ensure diverse results

## Performance Characteristics
- **Latency**: ~2-5s per query (mostly LLM API time)
- **Cache Hit Rate**: 60-80% for common queries
- **Throughput**: Suitable for <100 concurrent users (Streamlit limitation)
- **Cost**: ~$0.002-0.005 per query (gpt-4o-mini)

## Configuration
Edit `rag/config.py` to adjust:
- `keep_top_n`: Initial retrieval count (default: 15)
- `context_top_n`: Documents sent to LLM (default: 3)
- `tool_timeout_s`: LLM API timeout (default: 30s)
- `small_model` / `mid_model` / `large_model`: Model selection

## License
MIT
