import asyncio, os, json, time, datetime as dt
from typing import Dict, Any, List, TypedDict, Optional
from langgraph.graph import StateGraph, END
from litellm import acompletion  # Use async version
from .config import settings
from .prompts import SYSTEM_BASE, INTENT_SLOT_PROMPT, COMPOSER_PROMPT
from .retriever import HybridRetriever
from .utils import with_timeout
from .cache import qr_cache, completion_cache, query_cache_key

class RAGState(TypedDict):
    query: str
    retriever: Optional[HybridRetriever]
    slots: Optional[Dict[str, Any]]
    docs: Optional[List[Dict[str, Any]]]
    validation: Optional[Dict[str, Any]]
    answer: Optional[str]
    applied_filters: Optional[Dict[str, Any]]  # Pass filters explicitly

def _route_model(task: str):
    if task in ("intent", "slots"): return settings.small_model
    if task in ("compose",): return settings.mid_model
    return settings.large_model

async def node_intent_slots(state: RAGState):
    print("=" * 60)
    print("📍 CHECKPOINT 1: Intent & Slot Extraction - START")
    print("=" * 60)
    
    query = state["query"]
    print(f"   Query: '{query}'")
    
    model = _route_model("intent")
    print(f"   Model: {model}")
    
    # Get applied filters from state (passed from app.py)
    applied_filters = state.get("applied_filters") or {}
    print(f"   Applied filters: {applied_filters}")
    
    # Create enhanced prompt with applied filters context
    filter_context = ""
    if applied_filters:
        filter_parts = []
        if applied_filters.get("city"): filter_parts.append(f"City: {applied_filters['city']}")
        if applied_filters.get("occasion"): filter_parts.append(f"Occasion: {applied_filters['occasion']}")
        if applied_filters.get("headcount", 0) > 0: filter_parts.append(f"Headcount: {applied_filters['headcount']}")
        if applied_filters.get("budget", 0) > 0: filter_parts.append(f"Budget: {applied_filters['budget']} AED")
        if applied_filters.get("date"): filter_parts.append(f"Date: {applied_filters['date']}")
        
        if filter_parts:
            filter_context = f"\nApplied filters: {', '.join(filter_parts)}"
    
    enhanced_prompt = INTENT_SLOT_PROMPT.format(query=query) + filter_context
    
    try:
        print(f"   Calling LLM for slot extraction (timeout: {settings.tool_timeout_s}s)...")
        out = await with_timeout(async_completion(model, enhanced_prompt), settings.tool_timeout_s)
        slots = safe_json(out)
        print(f"   LLM extracted slots: {slots}")
        
        # Validate and clean extracted values
        valid_cities = ["Dubai", "Abu Dhabi"]
        valid_occasions = ["corporate", "party", "conference", "award", "intimate", "family", "wedding"]
        
        if slots.get("city") and slots["city"] not in valid_cities:
            print(f"   ⚠️ Invalid city '{slots['city']}', setting to null")
            slots["city"] = None
        
        if slots.get("occasion") and slots["occasion"] not in valid_occasions:
            print(f"   ⚠️ Invalid occasion '{slots['occasion']}', setting to null")
            slots["occasion"] = None
        
        if slots.get("intent") not in ["venue_search", None]:
            print(f"   ⚠️ Invalid intent '{slots['intent']}', defaulting to 'venue_search'")
            slots["intent"] = "venue_search"
        
        print(f"   Validated slots: {slots}")
        
        # Applied filters OVERRIDE query-extracted slots (user's explicit filters take precedence)
        if applied_filters:
            if applied_filters.get("city"):
                slots["city"] = applied_filters["city"]
            if applied_filters.get("occasion"):
                slots["occasion"] = applied_filters["occasion"]
            if applied_filters.get("headcount", 0) > 0:
                slots["headcount"] = applied_filters["headcount"]
            if applied_filters.get("budget", 0) > 0:
                slots["budget"] = applied_filters["budget"]
            if applied_filters.get("date"):
                slots["date"] = applied_filters["date"]
        
        print(f"   Final slots (after filter override): {slots}")
                
    except asyncio.TimeoutError:
        print(f"   ⚠️ LLM call timed out after {settings.tool_timeout_s}s, using fallback")
        slots = {
            "intent": "venue_search", 
            "city": applied_filters.get("city") if applied_filters.get("city") else None,
            "headcount": applied_filters.get("headcount") if applied_filters.get("headcount", 0) > 0 else None,
            "budget": applied_filters.get("budget") if applied_filters.get("budget", 0) > 0 else None,
            "occasion": applied_filters.get("occasion") if applied_filters.get("occasion") else None,
            "date": applied_filters.get("date") if applied_filters.get("date") else None,
            "constraints": None
        }
        print(f"   Fallback slots (from filters): {slots}")
    except Exception as e:
        print(f"   ⚠️ LLM failed with error: {type(e).__name__}: {e}, using fallback")
        slots = {
            "intent": "venue_search", 
            "city": applied_filters.get("city") if applied_filters.get("city") else None,
            "headcount": applied_filters.get("headcount") if applied_filters.get("headcount", 0) > 0 else None,
            "budget": applied_filters.get("budget") if applied_filters.get("budget", 0) > 0 else None,
            "occasion": applied_filters.get("occasion") if applied_filters.get("occasion") else None,
            "date": applied_filters.get("date") if applied_filters.get("date") else None,
            "constraints": None
        }
        print(f"   Fallback slots (from filters): {slots}")
    
    print("✅ CHECKPOINT 1: Intent & Slot Extraction - COMPLETE")
    print()
    return {"slots": slots}

async def node_retrieve(state: RAGState):
    print("=" * 60)
    print("📍 CHECKPOINT 2: Hybrid Retrieval - START")
    print("=" * 60)
    
    retriever: HybridRetriever = state["retriever"]
    slots = state.get("slots", {}) or {}
    print(f"   Slots for filtering: {slots}")
    
    filters = {
        "city": slots.get("city"),
        "headcount": slots.get("headcount"),
        "budget": slots.get("budget"),
        "occasion": slots.get("occasion"),
    }
    print(f"   Active filters: {filters}")
    
    print("   Executing hybrid search (BM25 stable + hot)...")
    docs = retriever.search(state["query"], filters)
    print(f"   Retrieved {len(docs)} unique vendor documents")
    
    if docs:
        print(f"   Top result: {docs[0]['meta']['title']} (ID: {docs[0]['meta']['id']}, Vendor: {docs[0]['meta'].get('vendor_id')})")
        if len(docs) >= 3:
            unique_vendors = len(set(d['meta'].get('vendor_id') for d in docs[:3]))
            print(f"   Top 3 diversity: {unique_vendors} unique vendors")
    else:
        print("   ⚠️ No documents retrieved")
    
    print("✅ CHECKPOINT 2: Hybrid Retrieval - COMPLETE")
    print()
    return {"docs": docs}

async def node_validate(state: RAGState):
    print("=" * 60)
    print("📍 CHECKPOINT 3: Validation - START")
    print("=" * 60)
    
    # Lightweight, rule-based validation
    slots = state.get("slots", {})
    docs = state.get("docs", [])
    applied_filters = state.get("applied_filters") or {}
    
    print(f"   Docs count (before filter): {len(docs)}")
    print(f"   Slots: {slots}")
    print(f"   Applied filters: {applied_filters}")
    
    # CRITICAL: Filter out documents that don't match applied_filters
    # This is a safety net to ensure webpage filters are strictly enforced
    if applied_filters and docs:
        filtered_docs = []
        for doc in docs:
            meta = doc.get("meta", {})
            passes = True
            
            # Check city filter
            if applied_filters.get("city"):
                if meta.get("city", "").lower() != applied_filters["city"].lower():
                    passes = False
                    print(f"   ❌ Filtered out {meta.get('id')}: city mismatch (doc={meta.get('city')}, filter={applied_filters['city']})")
            
            # Check occasion filter
            if applied_filters.get("occasion") and passes:
                occasions = [o.lower() for o in meta.get("occasion", [])]
                if applied_filters["occasion"].lower() not in occasions:
                    passes = False
                    print(f"   ❌ Filtered out {meta.get('id')}: occasion mismatch (doc={meta.get('occasion')}, filter={applied_filters['occasion']})")
            
            # Check headcount filter
            if applied_filters.get("headcount", 0) > 0 and passes:
                hmin = meta.get("headcount_min", 0)
                hmax = meta.get("headcount_max", 10**9)
                print(hmin, hmax)
                if not (hmin <= applied_filters["headcount"] <= hmax):
                    passes = False
                    print(f"   ❌ Filtered out {meta.get('id')}: headcount out of range (doc={hmin}-{hmax}, filter={applied_filters['headcount']})")
            
            # Check budget filter
            if applied_filters.get("budget", 0) > 0 and passes:
                pmin = meta.get("price_min", 0)
                pmax = meta.get("price_max", 10**12)
                if not (pmin <= applied_filters["budget"] <= pmax):
                    passes = False
                    print(f"   ❌ Filtered out {meta.get('id')}: budget out of range (doc={pmin}-{pmax}, filter={applied_filters['budget']})")
            
            if passes:
                filtered_docs.append(doc)
        
        print(f"   Docs count (after filter): {len(filtered_docs)} (removed {len(docs) - len(filtered_docs)})")
        docs = filtered_docs
    
    # Smart validation: only flag truly missing critical info
    # Check BOTH slots (from query) AND applied_filters (from sidebar)
    issues = []
    
    # Helper function to check if a field is set either in slots or applied filters
    def has_value(field_name):
        slot_value = slots.get(field_name)
        filter_value = applied_filters.get(field_name)
        
        # For numeric fields (headcount, budget), check if > 0
        if field_name in ["headcount", "budget"]:
            return (slot_value and slot_value > 0) or (filter_value and filter_value > 0)
        # For string fields (city, occasion), check if non-empty
        return bool(slot_value) or bool(filter_value)
    
    # If we have no results, suggest key filters to narrow down
    if not docs:
        print("   Validation strategy: NO RESULTS - suggest critical filters")
        if not has_value("city"):
            issues.append("city")
        if not has_value("occasion"):
            issues.append("occasion")
    # If we have results but they're ambiguous, suggest refinement
    elif len(docs) > 5:
        print("   Validation strategy: MANY RESULTS - suggest refinement filters")
        # Only suggest helpful filters that would narrow results
        if not has_value("city"):
            issues.append("city")
        if not has_value("headcount"):
            issues.append("headcount")
    else:
        print("   Validation strategy: GOOD RESULTS - no suggestions needed")
    
    print(f"   Missing info to suggest: {issues if issues else 'None'}")
    
    # staleness check
    stale = []
    now = dt.date.today()
    for d in docs[:3]:
        upd = d["meta"].get("updated_at")
        try:
            ddate = dt.datetime.strptime(upd, "%Y-%m-%d").date()
            if (now - ddate).days > 14:
                stale.append(d["meta"]["id"])
        except:
            pass
    
    print(f"   Stale documents: {stale if stale else 'None'}")
    
    validation = {"missing": issues, "stale_ids": stale}
    
    print("✅ CHECKPOINT 3: Validation - COMPLETE")
    print()
    return {"validation": validation, "docs": docs}

async def node_compose(state: RAGState):
    print("=" * 60)
    print("📍 CHECKPOINT 4: Response Composition - START")
    print("=" * 60)
    
    # Cache first
    slots = state.get("slots", {})
    ck = query_cache_key(state["query"], slots.get("city"), slots.get("occasion"), slots.get("headcount"), slots.get("budget"), None)
    cached = completion_cache.get(ck)
    if cached:
        print("   ✨ Using cached response")
        print("✅ CHECKPOINT 4: Response Composition - COMPLETE (cached)")
        print()
        return {"answer": cached}

    docs = state.get("docs", [])
    print(f"   Composing answer from {len(docs)} documents")
    
    # Handle no results case - generate direct response without LLM call
    if not docs:
        print("   No venues found - generating no-results response")
        answer = _generate_no_results_answer(slots)
        completion_cache.set(ck, answer)
        print(f"   No-results response generated: {len(answer)} characters")
        print("✅ CHECKPOINT 4: Response Composition - COMPLETE (no results)")
        print("=" * 60)
        print()
        return {"answer": answer}
    
    facts = {
        "slots": slots,
        "candidates": [
            {"id": d["meta"]["id"], "title": d["meta"]["title"], "city": d["meta"]["city"],
             "price_min": d["meta"]["price_min"], "price_max": d["meta"]["price_max"],
             "headcount_min": d["meta"]["headcount_min"], "headcount_max": d["meta"]["headcount_max"],
             "snippet": d.get("snippet",""), "updated_at": d["meta"]["updated_at"]}
            for d in docs[:3]
        ],
    }
    
    model = _route_model("compose")
    print(f"   Using model: {model}")
    
    sys = SYSTEM_BASE
    user = COMPOSER_PROMPT.format(facts=json.dumps(facts, ensure_ascii=False))
    
    try:
        print(f"   Calling LLM for response composition (timeout: {settings.tool_timeout_s}s)...")
        out = await with_timeout(async_completion(model, user, system=sys), settings.tool_timeout_s)
        answer = out
        completion_cache.set(ck, out)
        print(f"   LLM generated {len(answer)} character response")
        print(f"   Answer preview: {answer[:100]}...")
    except asyncio.TimeoutError:
        print(f"   ⚠️ LLM composition timed out after {settings.tool_timeout_s}s, using fallback")
        answer = _generate_fallback_answer(docs, slots, facts)
    except Exception as e:
        print(f"   ⚠️ LLM composition failed with error: {type(e).__name__}: {e}, using fallback")
        answer = _generate_fallback_answer(docs, slots, facts)
    
    print("✅ CHECKPOINT 4: Response Composition - COMPLETE")
    print("=" * 60)
    print()
    return {"answer": answer}

def _generate_no_results_answer(slots):
    """Generate helpful response when no venues match the search criteria"""
    criteria = []
    suggestions = []
    
    # Build what user asked for
    if slots.get("city"):
        criteria.append(f"in {slots['city']}")
    if slots.get("occasion"):
        criteria.append(f"for {slots['occasion']} events")
    if slots.get("headcount"):
        criteria.append(f"with capacity for {slots['headcount']} guests")
    if slots.get("budget"):
        criteria.append(f"within {slots['budget']:,} AED budget")
    
    # Build helpful suggestions based on what was specified
    if slots.get("budget"):
        suggestions.append("Try increasing your budget")
    if slots.get("headcount") and slots.get("headcount") > 200:
        suggestions.append("Consider splitting into multiple venues for very large groups")
    if slots.get("city") and slots.get("occasion") and slots.get("headcount"):
        suggestions.append("Try relaxing some requirements")
    elif not slots.get("city"):
        suggestions.append("Specify a city (Dubai or Abu Dhabi)")
    elif not slots.get("occasion"):
        suggestions.append("Specify the occasion type")
    
    # Build the response
    if criteria:
        criteria_text = " ".join(criteria)
        response = f"I couldn't find any venues {criteria_text}."
    else:
        response = "I couldn't find any venues matching your search."
    
    if suggestions:
        response += f"\n\nSuggestions:\n- " + "\n- ".join(suggestions)
    
    response += "\n\nWould you like to adjust your search criteria?"
    
    return response

def _generate_fallback_answer(docs, slots, facts):
    """Generate deterministic fallback answer when LLM fails"""
    lines = []
    
    if docs:
        # We have results, show them
        for d in facts["candidates"]:
            sid = d["id"]
            staleness = ""
            try:
                upd = dt.datetime.strptime(d["updated_at"], "%Y-%m-%d").date()
                if (dt.date.today()-upd).days>14:
                    staleness = " (stale; needs reconfirmation)"
            except:
                pass
            lines.append(f"- {d['title']} in {d['city']} • {d['price_min']}-{d['price_max']} {staleness} [#{sid}]")
        
        # Add helpful context about what filters are active
        active_filters = []
        if slots.get("city"): active_filters.append(f"{slots['city']}")
        if slots.get("occasion"): active_filters.append(f"{slots['occasion']} events")
        if slots.get("headcount"): active_filters.append(f"{slots['headcount']} people")
        if slots.get("budget"): active_filters.append(f"{slots['budget']} AED budget")
        
        if active_filters:
            lines.insert(0, f"Here are venues for {', '.join(active_filters)}:\n")
        else:
            lines.insert(0, "Here are some venue recommendations:\n")
    else:
        # No results - use the dedicated no-results function
        return _generate_no_results_answer(slots)
    
    answer = "\n".join(lines)
    print(f"   Fallback generated {len(answer)} character response")
    return answer

async def async_completion(model: str, prompt: str, system: str|None=None):
    """Call LLM with detailed error handling"""
    msgs = []
    if system:
        msgs.append({"role": "system", "content": system})
    msgs.append({"role": "user", "content": prompt})
    
    print(f"   🔧 LLM Call Debug:")
    print(f"      Model: {model}")
    print(f"      Message count: {len(msgs)}")
    print(f"      System prompt length: {len(system) if system else 0}")
    print(f"      User prompt length: {len(prompt)}")
    
    try:
        resp = await acompletion(model=model, messages=msgs, temperature=0.2)
        print(f"      ✅ LLM responded successfully")
        
        # Try to extract content
        try:
            content = resp.choices[0].message.content
            print(f"      Content length: {len(content)} chars")
            print(f"      📝 LLM Response: {content}")
            print()
            return content
        except AttributeError:
            # Try dict access
            content = resp.choices[0].message["content"]
            print(f"      Content length: {len(content)} chars")
            print(f"      📝 LLM Response: {content}")
            print()
            return content
        except Exception as e:
            print(f"      ⚠️ Error extracting content: {e}")
            print(f"      Response type: {type(resp)}")
            print(f"      Response: {resp}")
            return str(resp)
            
    except Exception as e:
        print(f"      ❌ LLM Call Failed!")
        print(f"      Error type: {type(e).__name__}")
        print(f"      Error message: {str(e)}")
        import traceback
        print(f"      Traceback: {traceback.format_exc()}")
        raise  # Re-raise to be caught by node error handling

def safe_json(s: str):
    """Parse JSON from string, handling markdown code blocks"""
    try:
        # Strip markdown code blocks if present
        s = s.strip()
        if s.startswith("```"):
            # Remove opening ```json or ``` and closing ```
            lines = s.split('\n')
            # Remove first line if it's ```json or ```
            if lines[0].startswith("```"):
                lines = lines[1:]
            # Remove last line if it's ```
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            s = '\n'.join(lines).strip()
        
        print(f"   🔧 Parsing JSON (cleaned): {s[:200]}...")
        parsed = json.loads(s)
        print(f"   ✅ JSON parsed successfully: {parsed}")
        return parsed
    except (json.JSONDecodeError, TypeError) as e:
        print(f"   ❌ JSON parsing failed: {e}")
        print(f"   Original string: {s[:500]}")
        # Fallback to default
        return {"intent":"unknown","city":None,"headcount":None,"budget":None,"occasion":None,"date":None,"constraints":None}

def build_graph(retriever: HybridRetriever):
    g = StateGraph(RAGState)
    g.add_node("intent_slot_filler", node_intent_slots)
    g.add_node("retrieve_hybrid", node_retrieve)
    g.add_node("validator", node_validate)
    g.add_node("composer", node_compose)

    g.set_entry_point("intent_slot_filler")
    g.add_edge("intent_slot_filler", "retrieve_hybrid")
    g.add_edge("retrieve_hybrid", "validator")
    g.add_edge("validator", "composer")
    g.add_edge("composer", END)
    return g.compile()
