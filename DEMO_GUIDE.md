# SahraEvent RAG Demo Guide

This guide provides sample data and queries designed to showcase all implemented features.

## Quick Start for Demo

**5-Minute Demo Script:**

1. **Basic Search** (30 sec)
   - Query: `"yacht party in Dubai"`
   - Point out: Fast results, citations [#ID], clean UI

2. **Show Deduplication** (45 sec)
   - Query: `"party venue in Dubai"`
   - Point out: "3 different vendors, not 3 from same vendor"
   - Show console: `Top 3 diversity: 3 unique vendors`

3. **Natural Language** (30 sec)
   - Query: `"Hey, need beach vibe for 20 friends DXB, maybe 15k budget"`
   - Point out: "Understood DXB=Dubai, extracted all filters"

4. **Staleness Detection** (30 sec)
   - Query: `"wedding Abu Dhabi"`
   - Point out: 🕑 Stale flags on old data, "Updated: date" shown

5. **Caching** (30 sec)
   - Repeat query: `"yacht party in Dubai"`
   - Point out: "<1 second response vs 2-5s first time"
   - Show console: `✨ Using cached response`

6. **Filters** (45 sec)
   - Open sidebar, set: Dubai, corporate, 50 people, 20k budget
   - Query: `"any venue"`
   - Point out: "Filters override query, precise results"

7. **Pipeline** (30 sec)
   - Show console output with 4 checkpoints
   - Point out: "LangGraph orchestration, timeout handling"

**Total: ~4 minutes + Q&A**

---

## Demo Dataset Options

### Option 1: Basic Dataset (Default)
The default `data/vendors.csv` includes 14 unique venues - sufficient for basic demos.

### Option 2: Extended Dataset (Recommended for Deduplication Demo)
Use `data/vendors_extended.csv` (24 venues) which includes:
- **Multiple offers from same vendors** (yacht_01 has 3 variants, beach_01 has 2, etc.)
- **Perfect for testing deduplication** - shows how system picks best offer per vendor
- **4 additional unique vendors** for more diversity

**To use extended dataset:**
```python
# In app.py, line 150, change:
ingest_csv("data/vendors.csv", store, mark_hot=False)
# To:
ingest_csv("data/vendors_extended.csv", store, mark_hot=False)
```

---

## Current Demo Dataset (Basic)

The basic demo includes 14 diverse venues across Dubai and Abu Dhabi:

### Dubai Venues (8)
1. **Sunset Yacht** - Yacht cruise for 2-30 pax, AED 12k-18k
2. **Desert Camp** - Bedouin camp for 10-80 pax, AED 9k-14k
3. **Ballroom** - Hotel ballroom for 50-300 pax, AED 45k-90k
4. **Beach Club** - Beachfront venue for 15-150 pax, AED 18k-35k
5. **Art Gallery** - Contemporary space for 10-80 pax, AED 15k-28k
6. **Sports Complex** - Multi-sport facility for 20-100 pax, AED 12k-25k
7. **Marina Deck** - Waterfront deck for 8-60 pax, AED 10k-20k
8. **Private Club** - Exclusive club for 12-90 pax, AED 20k-38k

### Abu Dhabi Venues (6)
1. **Rooftop Lounge** - Skyline venue for 20-120 pax, AED 25k-42k
2. **Botanical Garden** - Outdoor garden for 25-200 pax, AED 22k-45k
3. **Luxury Spa** - Wellness facility for 5-40 pax, AED 8k-15k
4. **Heritage Palace** - Historic palace for 30-250 pax, AED 35k-65k
5. **Bedouin Tent** - Traditional tent for 15-120 pax, AED 16k-30k
6. **Historic Courtyard** - Cultural venue for 25-180 pax, AED 28k-50k

---

## Demo Queries by Feature

### 🎯 **1. Basic Search & Metadata Filtering**

**Feature Showcased:** BM25 search with city, occasion, headcount, and budget filters

#### Query 1.1: Simple Search
```
"yacht party in Dubai"
```
**Expected Result:**
- Sunset Yacht appears
- Dubai filter automatically applied
- Shows capacity, pricing, and citation [#369]

#### Query 1.2: With Headcount Filter
```
"venue for 25 people in Dubai"
```
**Expected Result:**
- Multiple venues shown (Desert Camp, Beach Club, Marina Deck, etc.)
- All venues have capacity range that includes 25
- Venues with 2-30 or 10-80 capacity appear

#### Query 1.3: With Budget Constraint
```
"corporate event under 20k AED in Abu Dhabi"
```
**Expected Result:**
- Luxury Spa (8k-15k) and Bedouin Tent (16k-30k) appear
- Higher-priced venues (Palace, Courtyard) excluded
- Shows budget-appropriate options only

#### Query 1.4: Multiple Filters Combined
```
"wedding venue in Abu Dhabi for 150 people, budget 40k"
```
**Expected Result:**
- Botanical Garden (25-200 pax, 22k-45k)
- Historic Courtyard (25-180 pax, 28k-50k)
- Heritage Palace (30-250 pax, 35k-65k)
- All meet capacity and budget requirements

---

### 🔄 **2. Vendor Deduplication**

**Feature Showcased:** Results show diverse vendors (no duplicate vendors in top 3)

> **💡 Best tested with `vendors_extended.csv`** which includes multiple offers from same vendors

#### Query 2.1: Test Deduplication (Extended Dataset)
```
"yacht in Dubai"
```

**With Extended Dataset, Before Deduplication:**
- Would retrieve: Sunset Yacht (3h), Morning Yacht (2h), Full Day Yacht (8h)
- All from `yacht_01` vendor
- Total: 3 results, 1 unique vendor

**After Deduplication:**
- Shows: Sunset Yacht (best match for query)
- Plus: Marina Deck (marina_01), Beach Club (beach_01)
- Total: 3 results, 3 unique vendors ✅
- Console log: `After deduplication: 3 unique vendors from 12 results`
- Console log: `Top 3 diversity: 3 unique vendors`

#### Query 2.2: Beach Venues (Extended Dataset)
```
"beach venue Dubai 50 people"
```

**With Extended Dataset:**
- Beach Club has 2 offers: Regular (15-150 pax) and Daytime (10-100 pax)
- System picks the best matching offer (regular for 50 people)
- Also shows other vendors: Marina Deck, Desert Camp
- No duplicate `beach_01` in top 3

#### Query 2.3: Verify with Broad Search
```
"party venue in Dubai"
```
**Expected Behavior:**
- Results show variety: Sunset Yacht, Desert Camp, Beach Club, Marina Deck, etc.
- No vendor appears twice in the displayed results
- User sees diverse options from different vendors
- Even if system retrieves 15+ documents, only 1 per vendor shown

#### Query 2.4: Compare Systems (Demo Tip)

**Show "Before" behavior:**
> "Imagine without deduplication, you'd see:
> - Sunset Yacht 3h [#369]
> - Sunset Yacht 2h morning [#370]  
> - Sunset Yacht 8h full day [#371]
> 
> All same vendor - poor user experience!"

**Show "After" (current system):**
> - Sunset Yacht 3h [#369] (yacht_01)
> - Beach Club [#406] (beach_01)
> - Marina Deck [#412] (marina_01)
> 
> Three different vendors - much better!

---

### 🕑 **3. Staleness Detection**

**Feature Showcased:** 14-day freshness threshold with visual indicators

#### Query 3.1: Identify Stale Data
```
"wedding venue in Abu Dhabi"
```
**Check Current Date vs Updated Dates:**
- Heritage Palace: 2025-08-15 (OLD - likely stale)
- Rooftop Lounge: 2025-08-29 (OLD - likely stale)
- Bedouin Tent: 2025-09-18 (depends on current date)

**Expected Display:**
- Stale venues show: 🕑 **Stale — please reconfirm**
- Updated date clearly visible: "Updated: 2025-08-15"
- Assistant mentions data freshness in response
- Console log: `Stale documents: [ID list]`

#### Query 3.2: Fresh vs Stale
```
"venue in Dubai for party"
```
**Expected Behavior:**
- Beach Club (2025-10-15) - likely fresh
- Private Club (2025-10-20) - likely fresh
- Ballroom (2025-07-03) - likely stale
- UI clearly distinguishes between fresh and stale options

---

### 🎨 **4. Occasion-Based Filtering**

**Feature Showcased:** Semantic understanding of event types

#### Query 4.1: Corporate Events
```
"corporate team building event"
```
**Expected Result:**
- Sports Complex (sports, team-building)
- Desert Camp (corporate, party)
- Rooftop Lounge (corporate, award)
- Shows venues tagged with "corporate"

#### Query 4.2: Wedding Events
```
"wedding venue with traditional style"
```
**Expected Result:**
- Bedouin Tent (traditional, cultural)
- Heritage Palace (heritage, luxury)
- Historic Courtyard (historic, outdoor)
- Botanical Garden (nature, outdoor)

#### Query 4.3: Awards & Galas
```
"award ceremony venue with stage"
```
**Expected Result:**
- Rooftop Lounge (award nights, live-dj, AV)
- Ballroom (conference, award, 5-star)
- Heritage Palace (prestigious awards)

#### Query 4.4: Wellness Events
```
"wellness retreat for executives"
```
**Expected Result:**
- Luxury Spa (wellness, relaxation)
- May also suggest Botanical Garden (nature, relaxation)

---

### 📊 **5. Natural Language Understanding**

**Feature Showcased:** LLM slot extraction from conversational queries

#### Query 5.1: Conversational Style
```
"Hey, I need something for a sunset party, maybe on the water? Around 25 guests, Dubai area"
```
**Expected Slot Extraction:**
- City: Dubai
- Headcount: 25
- Occasion: party
- Constraints: "sunset", "on the water"

**Expected Results:**
- Sunset Yacht (water, sunset tags)
- Marina Deck (waterfront)
- Beach Club (beachfront)

#### Query 5.2: Abbreviated Language
```
"bday party DXB 20 ppl beach vibes 15k budget"
```
**Expected Slot Extraction:**
- City: Dubai (from "DXB")
- Headcount: 20
- Budget: 15000
- Occasion: party
- Constraints: "beach"

**Expected Results:**
- Beach Club
- Marina Deck
- Shows budget-appropriate beach venues

#### Query 5.3: Date Mentions
```
"wedding venue in October for 100 people in Abu Dhabi"
```
**Expected Slot Extraction:**
- City: Abu Dhabi
- Headcount: 100
- Occasion: wedding
- Date: October (2025-10-XX)

**Expected Results:**
- Bedouin Tent
- Historic Courtyard
- Botanical Garden

---

### 💬 **6. Clarification & Missing Information**

**Feature Showcased:** Smart validation suggests missing critical filters

#### Query 6.1: Ambiguous Query (Many Results)
```
"I need a venue"
```
**Expected Behavior:**
- System returns multiple results (>5)
- Shows info box: 💡 "To get better results, try adding: city, headcount"
- Still shows some results, doesn't refuse
- Console log: `Validation strategy: MANY RESULTS - suggest refinement filters`

#### Query 6.2: No City Specified
```
"corporate event for 50 people"
```
**Expected Behavior:**
- Returns results from both cities
- May suggest: "Try specifying: city"
- Shows diverse options across Dubai and Abu Dhabi

#### Query 6.3: No Results
```
"venue for 500 people in Dubai under 10k"
```
**Expected Behavior:**
- No matches (capacity too high + budget too low)
- Suggests: "No venues found. Try specifying: city (Dubai or Abu Dhabi)"
- Or: "No venues found matching your criteria. Try adjusting your filters."

---

### 📝 **7. Citations & Traceability**

**Feature Showcased:** Every recommendation includes venue ID citation

#### Query 7.1: Verify Citations
```
"luxury venue in Abu Dhabi"
```
**Expected Response Format:**
```
Here are some luxury venues in Abu Dhabi:

- **Heritage Palace**: Historic palace venue with grand halls and cultural 
  performances. Capacity 30-250 guests, AED 35k-65k. [#411]
  
- **Historic Courtyard**: Traditional architecture with fountain centerpiece. 
  Capacity 25-180 guests, AED 28k-50k. [#415]
  
- **Rooftop Lounge**: Skyline venue with stage and AV. Capacity 20-120 guests, 
  AED 25k-42k. [#404]
```

**Validation:**
- Every venue mentioned has [#ID] citation
- IDs match the database records
- No claims without citations
- Console shows: `📝 LLM Response:` with citations

---

### ⚡ **8. Caching & Performance**

**Feature Showcased:** TTL-based query and completion caching

#### Query 8.1: Repeat Query (Cache Hit)
```
First search: "yacht party in Dubai for 10 people"
Wait 2 seconds
Second search: "yacht party in Dubai for 10 people"
```
**Expected Behavior:**
- First search: ~2-5 seconds (LLM call)
- Second search: <1 second (cached)
- Console log: `✨ Using cached response` (on second search)
- Exact same results returned

#### Query 8.2: Similar Query (Same Cache Bucket)
```
First: "party in Dubai for 10 people"
Second: "party in Dubai for 12 people"
```
**Expected Behavior:**
- Both queries hit same cache key (headcount bucketed to 10)
- Console shows cache key includes: `query + city + occasion + headcount_bucket + budget_bucket`
- Second query returns instantly

#### Query 8.3: Different Query (Cache Miss)
```
First: "yacht in Dubai"
Second: "desert camp in Abu Dhabi"
```
**Expected Behavior:**
- Both queries require LLM calls
- Different cache keys (different city and query)
- No cache hit message

---

### 🎯 **9. Hybrid Search Quality**

**Feature Showcased:** BM25 + RRF merge with stable/hot indexes

#### Query 9.1: Keyword Match
```
"rooftop venue with DJ"
```
**Expected Behavior:**
- Rooftop Lounge ranks high (title match + "live-dj" tag)
- BM25 score high due to keyword overlap
- Console log: `Executing hybrid search (BM25 stable + hot)...`

#### Query 9.2: Semantic Match
```
"outdoor nature event space"
```
**Expected Behavior:**
- Botanical Garden (garden, outdoor, nature)
- Desert Camp (outdoor, desert)
- Historic Courtyard (outdoor, historic)
- BM25 matches on tags and description

#### Query 9.3: Multi-Index Retrieval
```
"party venue in Dubai"
```
**Expected Behavior:**
- Searches both stable and hot indexes
- Console logs:
  - `Retrieved X unique vendor documents`
  - Shows merge of stable + hot results via RRF

---

### 🔧 **10. Sidebar Filters**

**Feature Showcased:** Manual filter application overrides NL query

#### Test 10.1: Filter Override
```
Sidebar: City = "Abu Dhabi", Occasion = "wedding", Headcount = 100
Query: "any venue"
```
**Expected Behavior:**
- Sidebar filters take precedence
- Only Abu Dhabi wedding venues for 100+ capacity shown
- Console log: `Applied filters: {'city': 'Abu Dhabi', 'occasion': 'wedding', 'headcount': 100}`

#### Test 10.2: Clear Filters
```
1. Set filters: Dubai, party, 50 people
2. Click "Clear Filters"
3. Search: "venue in Abu Dhabi"
```
**Expected Behavior:**
- Filters reset to empty
- Query extracts Abu Dhabi correctly
- No stale filter data affects results

---

## Advanced Demo Scenarios

### Scenario A: Corporate Event Planner
**Context:** Planning a 50-person team building event in Dubai, budget 15k

**Query Sequence:**
1. "team building activity Dubai 50 people"
   → Sports Complex appears
2. "what about something more relaxed, outdoor?"
   → Desert Camp, Beach Club appear
3. Apply budget filter: 15k
   → Desert Camp highlighted (9k-14k)

### Scenario B: Luxury Wedding
**Context:** Planning a 200-guest wedding in Abu Dhabi, high budget

**Query Sequence:**
1. "luxury wedding venue Abu Dhabi 200 guests"
   → Heritage Palace, Historic Courtyard, Botanical Garden
2. "I want something traditional and cultural"
   → Bedouin Tent, Historic Courtyard rise in ranking
3. Check staleness flags
   → Verify fresh data or see reconfirm warnings

### Scenario C: Last-Minute Party
**Context:** Urgent party planning, 20 people, Dubai, tonight

**Query Sequence:**
1. "quick party venue Dubai 20 people tonight"
   → Multiple options shown
2. Check for availability (manual - external tool not implemented)
3. "something on the water or beach"
   → Sunset Yacht, Marina Deck, Beach Club

---

## Console Output to Watch For

### Successful Search Pipeline:
```
🚀 RUN ID: 1759735189225 | Query: 'yacht party in Dubai for 10 ppl'
============================================================
📍 CHECKPOINT 1: Intent & Slot Extraction - START
   Model: gpt-4o-mini
   LLM extracted slots: {'intent': 'venue_search', 'city': 'Dubai', 'headcount': 10, ...}
✅ CHECKPOINT 1: Intent & Slot Extraction - COMPLETE

📍 CHECKPOINT 2: Hybrid Retrieval - START
   Executing hybrid search (BM25 stable + hot)...
   Retrieved 8 unique vendor documents
   After deduplication: 5 unique vendors from 8 results
   Top 3 diversity: 3 unique vendors
✅ CHECKPOINT 2: Hybrid Retrieval - COMPLETE

📍 CHECKPOINT 3: Validation - START
   Validation strategy: GOOD RESULTS - no suggestions needed
   Stale documents: [369, 383, 397]
✅ CHECKPOINT 3: Validation - COMPLETE

📍 CHECKPOINT 4: Response Composition - START
   Composing answer from 8 documents
   Using model: gpt-4o-mini
   LLM generated 590 character response
✅ CHECKPOINT 4: Response Composition - COMPLETE

🎯 PIPELINE COMPLETE - Final Results
```

### Cache Hit:
```
📍 CHECKPOINT 4: Response Composition - START
   ✨ Using cached response
✅ CHECKPOINT 4: Response Composition - COMPLETE (cached)
```

### Deduplication:
```
   After deduplication: 5 unique vendors from 12 results
   Top 3 diversity: 3 unique vendors
```

### Staleness Detection:
```
   Stale documents: [404, 405, 411]
```

---

## Expected UI Behavior

### Result Card Format:
```
**Sunset Yacht** · Dubai · Capacity 2-30 · AED 12,000-18,000 🕑 Stale — please reconfirm
_Premium 55ft yacht with crew. Soft drinks included. Marina departure..._
Updated: 2025-09-20
**Citation:** [#369]
```

### Info Boxes:
- 💡 Blue: Suggestions for refinement
- ✅ Green: "Search completed! Here are your results:"
- ⚠️ Yellow: Warning messages
- 🕑 Orange: Staleness indicator

### Assistant Reply Section:
- Natural language summary
- Bullet points with venue names
- Citations after each mention [#ID]
- Next step suggestion if needed

---

## Performance Benchmarks

**Target Metrics:**
- First query (cold): 2-5 seconds
- Cached query: <1 second  
- Cache hit rate: 60-80% for common queries
- Top-3 diversity: 100% (always 3 unique vendors)
- Citation coverage: 100% (every claim cited)

**Cost per Query:**
- With cache miss: ~$0.002-0.005 (gpt-4o-mini)
- With cache hit: $0 (served from cache)
- Average (60% cache hit): ~$0.001-0.002/query

---

## Testing Checklist

- [ ] All 14 venues appear in appropriate searches
- [ ] Staleness flags show for >14 day old data
- [ ] Vendor deduplication works (no duplicate vendors in top 3)
- [ ] Citations present in all responses [#ID]
- [ ] Sidebar filters override query extraction
- [ ] Cache hits on repeat queries (<1s response)
- [ ] Missing info suggestions appear for ambiguous queries
- [ ] All occasions searchable (corporate, party, wedding, etc.)
- [ ] Budget filters work correctly
- [ ] Headcount filters work correctly
- [ ] Both Dubai and Abu Dhabi venues searchable
- [ ] Natural language variations understood ("DXB" = Dubai, "bday" = party)
- [ ] Console logs show all 4 checkpoints
- [ ] UI displays results immediately after search
- [ ] No hanging or freezing during search

---

## Tips for Demo Presentation

1. **Start Simple:** Begin with "yacht party in Dubai" to show basic flow
2. **Show Diversity:** Follow up with broader query to demonstrate deduplication
3. **Highlight Intelligence:** Use conversational query like "Hey, I need a beach vibe for 20 friends"
4. **Demonstrate Filters:** Use sidebar to override and refine
5. **Show Caching:** Repeat a query to show instant results
6. **Point Out Details:** Highlight staleness flags, citations, suggestions
7. **Console Demo:** Show terminal to display pipeline checkpoints
8. **Performance:** Emphasize sub-5s responses and caching

---

## Known Limitations (Be Transparent)

1. **No Real-Time Availability:** System doesn't check actual vendor calendars
2. **No WhatsApp Integration:** Manual follow-up required
3. **Single-Instance Only:** In-memory cache doesn't share across instances
4. **Embeddings Disabled:** Currently BM25-only (semantic search limited)
5. **No Payment Integration:** Booking must happen externally
6. **Limited Dataset:** Only 14 sample venues (real system would have 1000s)

---

## Next Steps After Demo

**If audience is impressed, mention:**
- Postgres + pgvector for 10K+ venues
- Redis for multi-instance caching
- FastAPI endpoints for integrations
- Real-time availability checks via vendor APIs
- WhatsApp bot for customer interactions
- Stripe integration for deposits/payments

