import os, re, sqlite3, datetime as dt
import streamlit as st
from dotenv import load_dotenv
load_dotenv()

from rag.config import settings
from rag.store import DualIndexStore
from rag.ingest import ingest_csv
from rag.retriever import HybridRetriever
from rag.graph import build_graph, RAGState

# Debug API key
api_key = os.getenv('OPENAI_API_KEY')
if api_key:
    masked_key = f"{api_key[:8]}...{api_key[-4:]}" if len(api_key) > 12 else "***"

st.set_page_config(page_title="SahraEvent RAG Demo", page_icon="🎉", layout="wide")
st.title("🎉 SahraEvent — Fast, Reliable, Low-Cost RAG")

with st.expander("ℹ️ How this demo is built"):
    st.markdown("""
- BM25 keyword search with metadata filters (FAISS disabled for stability)
- LangGraph orchestration: slot extraction → retrieval → validation → composition
- Dual index architecture (stable + hot) with 14-day staleness detection
- Tiered models via `litellm` — set `OPENAI_API_KEY` in your environment
- TTL-based caching for queries and completions
    """)

# Initialize session state
def init_session_state():
    if "filters_applied" not in st.session_state:
        st.session_state.filters_applied = {"city": "", "occasion": "", "headcount": 0, "budget": 0, "date": ""}
    if "auto_search" not in st.session_state:
        st.session_state.auto_search = False
    # Store will be initialized only when searching, not on filter changes

# Sidebar filters
def render_filters():
    st.sidebar.header("Filters")
    
    city = st.sidebar.selectbox("City", ["", "Dubai", "Abu Dhabi"], key="filter_city")
    occasion = st.sidebar.selectbox("Occasion", ["", "corporate", "party", "conference", "award", "intimate", "family"], key="filter_occasion")
    headcount = st.sidebar.number_input("Headcount", min_value=0, max_value=1000, value=0, step=5, key="filter_headcount")
    budget = st.sidebar.number_input("Budget (AED)", min_value=0, max_value=1000000, value=0, step=500, key="filter_budget")
    date = st.sidebar.date_input("Event Date", value=None, key="filter_date")
    
    if st.sidebar.button("Apply Filters", type="primary"):
        st.session_state.filters_applied = {
            "city": city, "occasion": occasion, "headcount": headcount, 
            "budget": budget, "date": date.strftime("%Y-%m-%d") if date else ""
        }
        st.sidebar.success("Filters applied!")
    
    if st.sidebar.button("Clear Filters"):
        st.session_state.filters_applied = {"city": "", "occasion": "", "headcount": 0, "budget": 0, "date": ""}
        st.sidebar.info("Filters cleared!")
    
    # Display applied filters
    st.sidebar.markdown("**Applied Filters:**")
    applied = st.session_state.filters_applied
    if applied["city"]: st.sidebar.write(f"📍 City: {applied['city']}")
    if applied["occasion"]: st.sidebar.write(f"🎉 Occasion: {applied['occasion']}")
    if applied["headcount"] > 0: st.sidebar.write(f"👥 Headcount: {applied['headcount']}")
    if applied["budget"] > 0: st.sidebar.write(f"💰 Budget: {applied['budget']:,} AED")
    if applied["date"]: st.sidebar.write(f"📅 Date: {applied['date']}")

# Main search function using LangGraph
async def run_langgraph_search(query, store, retriever, graph, applied_filters, run_id):
    """Run LangGraph search with all dependencies passed in (no session state access)"""
    print()
    print("=" * 80)
    print(f"🚀 RUN ID: {run_id} | Query: '{query}'")
    print("=" * 80)
    
    # Debug: Check API key
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        print("⚠️ WARNING: OPENAI_API_KEY not set!")
    else:
        print(f"✅ API Key found: {api_key[:8]}...{api_key[-4:]}")
    
    try:
        # Run LangGraph pipeline
        initial_state = {
            "query": query,
            "retriever": retriever,
            "slots": None,
            "docs": None,
            "validation": None,
            "answer": None,
            "applied_filters": applied_filters
        }
        
        print(f"🔍 Running LangGraph pipeline (RUN ID: {run_id})...")
        result = await graph.ainvoke(initial_state)
        
        print()
        print("=" * 80)
        print(f"🎯 RUN ID: {run_id} | PIPELINE COMPLETE - Final Results:")
        print("=" * 80)
        print(f"   Slots extracted: {result.get('slots', {})}")
        print(f"   Documents retrieved: {len(result.get('docs', []))}")
        print(f"   Validation issues: {result.get('validation', {}).get('missing', [])}")
        print(f"   Stale documents: {result.get('validation', {}).get('stale_ids', [])}")
        answer = result.get('answer', '')
        print(f"   Answer length: {len(answer)} chars")
        print(f"   📝 Final Answer:")
        print(f"   {answer}")
        print("=" * 80)
        print(f"✅ RUN ID: {run_id} | COMPLETE")
        print("=" * 80)
        print()
        
        return {
            "answer": result.get("answer", "No answer generated"),
            "docs": result.get("docs", []),
            "validation": result.get("validation", {"missing": [], "stale_ids": []}),
            "slots": result.get("slots", {})
        }
        
    except Exception as e:
        print(f"❌ LangGraph Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return {
            "answer": f"I encountered an error: {str(e)}. Please try again.",
            "docs": [],
            "validation": {"missing": [], "stale_ids": []},
            "slots": {}
        }

# Synchronous wrapper for LangGraph
def run_search(query):
    import asyncio
    import concurrent.futures
    import time
    
    # Generate unique run ID
    run_id = f"{int(time.time() * 1000)}"
    
    # Initialize store, retriever, and graph (in main thread with session state access)
    try:
        if "store" not in st.session_state:
            print("🔍 Initializing store for search...")
            store = DualIndexStore(settings.embed_model)
            store.clear()  # Clear existing data to avoid duplicates
            ingest_csv("data/vendors.csv", store, mark_hot=False)
            st.session_state.store = store
            print("✅ Store initialized for search")
        
        if "retriever" not in st.session_state:
            st.session_state.retriever = HybridRetriever(st.session_state.store)
        if "graph" not in st.session_state:
            st.session_state.graph = build_graph(st.session_state.retriever)
        
        # Capture all needed values before entering thread
        store = st.session_state.store
        retriever = st.session_state.retriever
        graph = st.session_state.graph
        applied_filters = st.session_state.filters_applied
        
    except Exception as e:
        print(f"❌ Initialization Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return {
            "answer": f"Failed to initialize: {str(e)}. Please try again.",
            "docs": [],
            "validation": {"missing": [], "stale_ids": []},
            "slots": {}
        }
    
    def _run_async():
        """Run async code in a new event loop (no session state access here)"""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(
                run_langgraph_search(query, store, retriever, graph, applied_filters, run_id)
            )
        finally:
            loop.close()
    
    try:
        # Always use thread executor in Streamlit to avoid event loop conflicts
        with concurrent.futures.ThreadPoolExecutor() as executor:
            future = executor.submit(_run_async)
            return future.result(timeout=30)  # 30 second timeout
    except concurrent.futures.TimeoutError:
        print(f"❌ Timeout Error: Search took too long")
        return {
            "answer": "The search timed out. Please try again with a simpler query.",
            "docs": [],
            "validation": {"missing": [], "stale_ids": []},
            "slots": {}
        }
    except Exception as e:
        print(f"❌ Async Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return {
            "answer": f"I encountered an error: {str(e)}. Please try again.",
            "docs": [],
            "validation": {"missing": [], "stale_ids": []},
            "slots": {}
        }


# Initialize and render UI
init_session_state()
render_filters()

# Query input
def on_query_change():
    if st.session_state.query_input and st.session_state.query_input.strip():
        st.session_state.auto_search = True

query = st.text_input(
    "Ask about venues, packages, or ideas (e.g., 'sunset yacht for 25 people in Dubai, 15k budget in Oct')",
    key="query_input",
    on_change=on_query_change,
    help="Press Enter to search automatically"
)

# Search logic - simplified to avoid session state conflicts
search_button = st.button("Search & Compose")
should_search = (search_button and query.strip()) or (st.session_state.auto_search and query.strip())

# Perform search and display results in one flow
if should_search:
    st.session_state.auto_search = False
    print("🔍 Starting search...")
    
    try:
        with st.spinner("Thinking..."):
            res = run_search(query)
        
        print(f"🔍 Search completed successfully")
        print(f"🔍 Result keys: {res.keys() if res else 'None'}")
        print(f"🔍 Answer length: {len(res.get('answer', ''))}")
        print(f"🔍 Docs count: {len(res.get('docs', []))}")
        
        # Display results immediately (no session state storage - just show it)
        st.success("✅ Search completed! Here are your results:")
        
        missing = res.get("validation", {}).get("missing", [])
        stale_ids = set(res.get("validation", {}).get("stale_ids", []))
        docs = res.get("docs", [])
        
        # Only show missing info warning if we have no results or many ambiguous results
        if missing and (not docs or len(docs) > 5):
            st.info(f"💡 To get better results, try adding: {', '.join(missing)}")
        
        if docs:
            st.subheader("Top candidates")
            for i, d in enumerate(docs[:3]):
                try:
                    meta = d.get("meta", {})
                    sid = meta.get("id", f"doc_{i}")
                    title = meta.get("title", "Unknown Title")
                    city = meta.get("city", "Unknown City")
                    hmin = meta.get("headcount_min", 0)
                    hmax = meta.get("headcount_max", 0)
                    pmin = meta.get("price_min", 0)
                    pmax = meta.get("price_max", 0)
                    updated = meta.get("updated_at", "Unknown")
                    
                    staleness = "🕑 Stale — please reconfirm" if sid in stale_ids else ""
                    snippet = d.get('snippet', '')
                    
                    st.markdown(f"**{title}** · {city} · Capacity {hmin}-{hmax} · AED {int(pmin)}-{int(pmax)}  {staleness}  \n_{snippet}_  \nUpdated: {updated}  \n**Citation:** [#{sid}]")
                    st.divider()
                except Exception as e:
                    st.error(f"Error displaying document {i}: {str(e)}")
                    continue
        
        st.subheader("Assistant reply")
        answer = res.get("answer", "(no answer)")
        st.write(answer)
        print(f"🔍 Display complete!")
        
    except Exception as e:
        print(f"❌ Search exception: {e}")
        import traceback
        traceback.print_exc()
        st.error(f"Search failed: {str(e)}")

st.caption("💡 Use the sidebar filters or natural language to narrow down results")