# Fed Communications RAG System

## Project Overview

A retrieval-augmented generation system for querying Federal Reserve communications, enabling analysts and researchers to ask natural language questions about Fed policy, speaker views, and how messaging has evolved over time.

---

## Data Sources

| Source | URL | Content | Update Frequency |
|--------|-----|---------|------------------|
| FOMC Statements | federalreserve.gov/monetarypolicy/fomccalendars.htm | Post-meeting statements | 8x/year |
| FOMC Minutes | Same as above | Detailed meeting minutes | 8x/year (3 week lag) |
| Fed Speeches | federalreserve.gov/newsevents/speeches.htm | All governor/president speeches | Several per week |
| Testimony | federalreserve.gov/newsevents/testimony.htm | Congressional testimony | As scheduled |
| Press Conferences | YouTube transcripts or Fed site | Powell Q&A | 8x/year |

**Optional:** Regional Fed president speeches from district sites (richmondfed.org, chicagofed.org, etc.)

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        INGESTION                            │
├─────────────────────────────────────────────────────────────┤
│  Scraper → Clean/Parse → Chunk → Embed → Store w/ metadata  │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                      VECTOR DB                              │
│   Chunk text + metadata: {speaker, date, doc_type, url}     │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                     QUERY LAYER                             │
├─────────────────────────────────────────────────────────────┤
│  User query                                                 │
│      │                                                      │
│      ▼                                                      │
│  Query Analyzer (LLM)                                       │
│      - Classify: simple vs temporal vs comparison           │
│      - Extract filters: speaker, date range, topic          │
│      - Decompose if needed                                  │
│      │                                                      │
│      ▼                                                      │
│  Retrieval                                                  │
│      - Hybrid search (vector + BM25)                        │
│      - Metadata filters applied                             │
│      - Rerank top results                                   │
│      │                                                      │
│      ▼                                                      │
│  Synthesis (LLM)                                            │
│      - Combine chunks                                       │
│      - Generate answer with citations                       │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                       OUTPUT                                │
│   Answer + source citations (speaker, date, link)           │
└─────────────────────────────────────────────────────────────┘
```

---

## Metadata Schema

```python
{
    "chunk_id": str,
    "text": str,
    "speaker": str,          # "Jerome Powell", "Christopher Waller", etc.
    "date": datetime,
    "doc_type": str,         # "speech", "minutes", "statement", "testimony"
    "title": str,
    "url": str,
    "section": str           # optional: "economic outlook", "policy decision"
}
```

---

## Query Types & Handling

| Query Type | Example | Handling |
|------------|---------|----------|
| Simple factual | "What's the Fed's view on housing?" | Direct hybrid retrieval |
| Speaker-filtered | "What has Waller said about inflation?" | Hybrid + speaker filter |
| Temporal | "How has Powell's tone changed since 2023?" | Decompose by time period, retrieve each, synthesize |
| Comparison | "Compare Goolsbee and Bowman on rate cuts" | Retrieve for each speaker, synthesize comparison |
| Aggregation | "Which members mentioned recession recently?" | Retrieve broadly, LLM extracts speaker list |

---

## Implementation Phases

### Phase 1: Data Collection
1. Write scrapers for Fed speeches, statements, minutes, testimony
2. Parse HTML/PDF to clean text
3. Extract metadata: speaker, date, title, doc_type, url
4. Store raw documents in structured format

### Phase 2: Chunking & Indexing
5. Chunk documents (1000 tokens, with overlap)
6. Preserve metadata on each chunk
7. Embed with sentence-transformers or OpenAI embeddings
8. Store in vector DB with metadata filtering support
9. Set up BM25 index for hybrid search

### Phase 3: Query Pipeline
The LLM receives user queries and has access to a search tool. It decides when and how to call the tool, then synthesizes the final answer. There is no separate "query analyzer" component.

**Components:**
- LLM with tool/function calling (OpenAI gpt-5.2)
- Search tool (hybrid retrieval wrapped as a callable)
- Reranker (cross-encoder, runs inside tool before returning results)

**Tool Definition:**
```python
tools = [{
    "name": "search_fed_documents",
    "description": "Search Federal Reserve speeches, statements, and minutes to find what Fed officials have said about economic topics.",
    "input_schema": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Search query describing the topic"
            },
            "speaker": {
                "type": "string",
                "description": "Filter by speaker name, e.g. 'Jerome Powell', 'Christopher Waller'"
            },
            "doc_type": {
                "type": "string",
                "enum": ["speech", "statement", "minutes"],
                "description": "Filter by document type"
            },
            "date_start": {
                "type": "string",
                "format": "date",
                "description": "Filter to documents on or after this date (YYYY-MM-DD)"
            },
            "date_end": {
                "type": "string",
                "format": "date",
                "description": "Filter to documents on or before this date (YYYY-MM-DD)"
            }
        },
        "required": ["query"]
    }
}]
```

**What the LLM handles:**
- Decides if search is needed at all
- Extracts filters from natural language ("What did Waller say last month?" → speaker="Christopher Waller", date_start/end for last month)
- Decomposes complex queries into multiple tool calls
- Synthesizes results into a coherent answer with citations

**What the tool handles:**
- Hybrid search (dense + sparse vectors with RRF fusion)
- Metadata filtering (speaker, date range, doc_type)
- Reranking top results with cross-encoder
- Returning formatted chunks with source metadata

**Example Flow - Temporal Query:**
```
User: "How has Powell's tone on inflation changed since 2023?"
                    │
                    ▼
┌─────────────────────────────────────────────────────────────┐
│  LLM receives query                                         │
│  Decides: temporal evolution → needs multiple searches      │
└─────────────────────────────────────────────────────────────┘
                    │
        ┌───────────┴───────────┐
        ▼                       ▼
   Tool call #1            Tool call #2
   query: "inflation"      query: "inflation"
   speaker: "Jerome Powell" speaker: "Jerome Powell"
   date_start: "2023-01-01" date_start: "2024-01-01"
   date_end: "2023-12-31"   date_end: "2025-01-18"
        │                       │
        ▼                       ▼
   [2023 chunks]           [2024-25 chunks]
        │                       │
        └───────────┬───────────┘
                    ▼
┌─────────────────────────────────────────────────────────────┐
│  LLM receives both result sets                              │
│  Synthesizes: "In early 2023, Powell emphasized... By late  │
│  2024, his tone shifted to..." with citations               │
└─────────────────────────────────────────────────────────────┘
```

**Example Flow - Speaker Comparison:**
```
User: "Compare Goolsbee and Bowman on rate cuts"
                    │
                    ▼
        ┌───────────┴───────────┐
        ▼                       ▼
   Tool call #1            Tool call #2
   query: "rate cuts"      query: "rate cuts"
   speaker: "Austan Goolsbee"  speaker: "Michelle Bowman"
        │                       │
        └───────────┬───────────┘
                    ▼
   LLM synthesizes side-by-side comparison with citations
```

### Phase 4: Interface
14. Build FastAPI backend with `/query` endpoint
15. Vite + React frontend with chat interface
16. Display answer + collapsible source cards (speaker, date, link)
17. Optional sidebar filters: date range, speaker select

---

## Tech Stack

### Backend
| Component | Choice |
|-----------|--------|
| API Framework | FastAPI (Python) |
| Scraping | BeautifulSoup, Selenium (for JS-heavy pages) |
| Embeddings | `all-MiniLM-L6-v2` (free, local) or OpenAI `text-embedding-3-small` |
| Vector DB | Qdrant (free, good metadata filtering) or Chroma (simpler) |
| BM25 | `rank_bm25` library or built into Qdrant |
| Reranker | `cross-encoder/ms-marco-MiniLM-L-6-v2` |
| LLM | Claude API or GPT-4o |

### Frontend
| Component | Choice |
|-----------|--------|
| Build Tool | Vite |
| Framework | React |
| Language | TypeScript |
| Styling | Tailwind CSS |
| Deployment | Vercel or Netlify (static)

---

## Query Flow Detail

### Simple Query
```
"What's the Fed's current view on inflation?"
    │
    ▼
Query Analyzer: simple factual, no filters needed
    │
    ▼
Hybrid search: vector("Fed view inflation") + BM25("inflation")
    │
    ▼
Rerank top 10 → select top 5
    │
    ▼
Synthesis prompt + chunks → Answer with citations
```

### Temporal Evolution Query
```
"How has Waller's hawkishness evolved since 2021?"
    │
    ▼
Query Analyzer: temporal, speaker=Waller, needs decomposition
    │
    ▼
Decompose into sub-queries:
    - "Waller monetary policy stance 2021"
    - "Waller monetary policy stance 2022"
    - "Waller monetary policy stance 2023"
    - "Waller monetary policy stance 2024"
    │
    ▼
For each: hybrid search + filter(speaker=Waller, date in year)
    │
    ▼
Combine all chunks, sorted by date
    │
    ▼
Synthesis prompt: "Trace how this speaker's stance evolved chronologically"
    │
    ▼
Answer with timeline structure + citations
```

### Speaker Comparison Query
```
"Compare Goolsbee and Bowman on rate cuts"
    │
    ▼
Query Analyzer: comparison, speakers=[Goolsbee, Bowman]
    │
    ▼
Two retrievals:
    - hybrid search("rate cuts") + filter(speaker=Goolsbee)
    - hybrid search("rate cuts") + filter(speaker=Bowman)
    │
    ▼
Synthesis prompt: "Compare these two speakers' views"
    │
    ▼
Answer with side-by-side comparison + citations
```

---

## MVP vs Future Scope

### MVP
- Speeches + statements only
- Basic hybrid search + metadata filters
- Simple query classification (simple vs filtered)
- Clean React chat UI with source citations
- ~500 documents

### Future Additions
- Minutes, testimony, press conferences
- Full temporal decomposition for evolution queries
- Hawk/dove stance scoring as metadata
- Auto-updating ingestion pipeline
- Speaker clustering/alignment analysis

---

## Example Queries the System Should Handle

1. What has the Fed said about the neutral rate recently?
2. How has Powell's tone on inflation changed over the past year?
3. Which FOMC members have mentioned recession risk in the last 3 months?
4. What's the Fed's current view on the labor market?
5. Has anyone on the committee pushed back on the consensus view lately?
6. What did the Fed say about banking stress after SVB?
7. Compare Waller and Goolsbee on the pace of rate cuts.
8. What forward guidance language has appeared in recent statements?
9. When did the Fed stop calling inflation "transitory"?
10. Which regional Fed presidents have been most hawkish this year?

---

## Estimated Timeline

| Phase | Time |
|-------|------|
| Data collection + parsing | 1-2 days |
| Chunking + indexing | 1 day |
| Query pipeline + FastAPI | 2-3 days |
| React frontend | 1-2 days |
| Testing + polish | 1-2 days |
| **Total** | **6-10 days** |

---

## Success Criteria

- [ ] Can answer simple factual queries with relevant citations
- [ ] Metadata filtering works (speaker, date range)
- [ ] Temporal queries return chronologically structured answers
- [ ] Speaker comparisons retrieve from both speakers
- [ ] Clean UI with collapsible source cards linking to original documents
- [ ] Response latency under 10 seconds for typical queries

---

## Project Structure

```
fed-rag/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI app
│   │   ├── routers/
│   │   │   └── query.py         # /query endpoint
│   │   ├── services/
│   │   │   ├── retrieval.py     # Hybrid search logic
│   │   │   ├── query_analyzer.py # Query classification/decomposition
│   │   │   └── synthesis.py     # LLM response generation
│   │   └── db/
│   │       └── vector_store.py  # Qdrant/Chroma interface
│   ├── scripts/
│   │   ├── scrape.py            # Data collection
│   │   ├── parse.py             # HTML/PDF parsing
│   │   └── index.py             # Chunking + embedding + indexing
│   ├── data/
│   │   └── raw/                 # Raw scraped documents
│   └── requirements.txt
│
├── frontend/
│   ├── src/
│   │   ├── App.tsx
│   │   ├── main.tsx
│   │   ├── components/
│   │   │   ├── ChatInput.tsx
│   │   │   ├── ChatMessage.tsx
│   │   │   ├── SourceCard.tsx
│   │   │   └── Filters.tsx
│   │   ├── api/
│   │   │   └── client.ts
│   │   └── index.css
│   ├── index.html
│   ├── tailwind.config.js
│   ├── vite.config.ts
│   ├── tsconfig.json
│   └── package.json
│
└── README.md
```
