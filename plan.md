# Plan: "VS." — Two-Video RAG Comparison Chatbot (Engineer Screening Challenge)
## Context

**The task.** Take two short-form video URLs (one YouTube, one Instagram Reel — both mandatory),
pull each video's transcript + metadata (views, likes, comments, creator, follower count, hashtags,
upload date, duration), compute engagement rate, chunk+embed both transcripts into a vector DB
(each chunk tagged `video_id = A | B`), and expose a **streaming RAG chat** (LangChain/LangGraph
mandatory) that answers comparison questions with **source citations** and **conversation memory**.
Frontend: side-by-side video cards + chat panel. Everything **dynamic** (only the input URLs may be
hard-coded). Deliverables: deployed URL, Loom demo, clean GitHub repo (README + `.env.example` +
commits that tell a story). They explicitly want **cost + scale reasoning** for 1,000 creators/day
and "what breaks at 10,000 users."

**Why these choices.** Independent research into the 2026 landscape (Instagram extraction, transcript
reliability, RAG economics, LangGraph patterns) converged on nearly the exact stack shown in the
challenge's own reference "winning" answer (FastAPI + LangGraph + Gemini Flash + BGE + Qdrant +
yt-dlp + Apify + SSE). That convergence is the signal this is the defensible solution — we adopt it,
with the *reasoning* baked in so it can be defended, not parroted.

**Intended outcome.** A bug-free, fast, fully-dynamic full-stack RAG app + a README and a set of
talking points the user genuinely understands and can defend on the CEO/Head-of-Eng call.

**Decisions (locked):** Deliverable = **architecture plan / flow** (you build from it, so you can
defend it on the call). · Instagram = **hybrid (OSS → Apify fallback)** — chosen as the most defensible
("the hard way, with a safety net"). · LLM/services = **cloud free tiers, Gemini 2.5 Flash**.

---

## The Stack (and the one-line defense for each)

| Layer | Choice | Why this / what it beats |
|---|---|---|
| Frontend | **React + Vite + TS + Tailwind** | Tool, not a content site → no SSR needed. Vite cold-starts faster than Next for a demo; smaller. (Next.js is a fine swap; they allow either.) |
| Backend | **FastAPI (Python)** | Native to the ML/LangChain ecosystem; async + first-class SSE streaming; pydantic validation. Node would force a polyglot split for Whisper/BGE. |
| Orchestration | **LangGraph** (LangChain ecosystem) | Need **stateful memory** (checkpointer), **conditional routing** (stats vs transcript vs comparison), node-level streaming. Plain LCEL is linear and has no first-class state — the comparison logic needs branches. |
| Embeddings | **BGE (`bge-small-en-v1.5`) self-hosted via FastEmbed** | $0 marginal, no API key, no rate limit, deterministic, strong MTEB. At scale, API embeddings (OpenAI $0.02/M) add up; BGE runs on CPU at this volume. |
| Vector DB | **Qdrant** (Docker local → Qdrant Cloud free 1 GB) | Best free tier (1 GB *forever*), first-class **metadata filtering** (we filter by `video_id` + time window — core to this app), fast HNSW, identical local/prod via Docker. Pinecone bills per read (pricey, hosted-only); Chroma is weaker for prod filtering/scale; pgvector works but Qdrant is purpose-built. |
| LLM | **Gemini 2.5 Flash** (free tier; abstracted behind an interface) | Generous free tier, fast streaming, strong long-context comparison reasoning, cheap paid. Swappable to Groq Llama (cheapest) or Claude Haiku (most polish) via one env var. |
| Transcript | **Fallback chain** (captions → ASR) | Reliability > any single source. See pipeline below. |
| ASR fallback | **Groq Whisper (free, ~228× RT) → faster-whisper `base` local ($0)** | Reels rarely have captions. Groq free tier is fast for a live demo; local Whisper is the $0 no-rate-limit backstop. |
| IG data | **Hybrid: yt-dlp/instaloader → Apify fallback** | OSS is $0 but fragile in 2026 (login walls, null engagement, 200 req/hr). Apify Reel+Profile scrapers (~$5/mo free credit ≈ 1,900 reels) are the reliable net, and follower count *only* comes cleanly from a profile scrape. Hybrid = great "I did it the hard way, with a safety net" story. |
| Streaming | **SSE** | One-way token stream → SSE is simpler than WebSockets, HTTP-native, passes through Cloud Run/proxies. |
| Caching | **Transcript/metadata cache keyed by `video_id`** (SQLite/JSON) | Re-ingest = instant + free. Also the headline cost lever at scale. |
| Deploy | **Docker** → backend on **Cloud Run** (scale-to-zero), frontend on **Vercel**, **Qdrant Cloud** free | All free-tier; `docker-compose` gives one-command local parity. |

---

## Architecture / End-to-end flow

```
                       ┌──────────────── INGESTION (once per URL pair) ────────────────┐
  YouTube URL ─┐       │  fetch metadata ──► compute engagement_rate ──► transcript     │
               ├──────►│  (yt-dlp / Apify)    (likes+comments)/views×100   (fallback     │──► chunk (~300 tok,
  IG Reel URL ─┘       │  + follower count                                  chain)        │     15% overlap, keep
                       └───────────────────────────────────────────────────────────────┘     start/end timestamps)
                                                                                                     │
                                                              BGE embed each chunk ◄────────────────┘
                                                                     │
                                          Qdrant upsert: vector + payload{video_id:A|B, chunk_id,
                                                     start_time, end_time, text}  +  stats stored per video
                                                                     │
   ┌──────────────────────────────── CHAT (LangGraph, per session thread_id) ───────────────────────────────┐
   │  user q ─► [route] ─► stats? ──────────────► read structured stats (no vector search)                    │
   │                     ─► transcript? ────────► semantic search (filter video_id)                           │
   │                     ─► comparison? ────────► balanced retrieve top-k from A AND top-k from B             │
   │                     ─► hook? ──────────────► time-window filter start_time < 5s, per video               │
   │                            │                                                                              │
   │            [assemble context]  = always inject A & B stats cards + retrieved chunks (with ids)           │
   │                            │                                                                              │
   │            [generate]  Gemini streams tokens; cites [A#chunk]/[B#chunk] from the injected ids            │
   │                            │                                                                              │
   │   SSE ►  {type:token}... {type:citation, video_id,chunk_id,start,quote}... {type:done}                   │
   │   memory: LangGraph checkpointer keyed by thread_id (history persists across turns)                      │
   └─────────────────────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## Ingestion details

**YouTube (primary path is robust & free):**
- Metadata via `yt-dlp` (JSON dump): `view_count`, `like_count`, `comment_count`, `uploader`,
  `channel_follower_count`, `upload_date`, `duration`, `tags`/hashtags, `description`.
- Transcript: `yt-dlp --write-auto-sub --sub-langs en --skip-download` (different code path than
  `youtube-transcript-api`, dodges its cloud-IP `RequestBlocked` problem) → parse VTT into
  timestamped segments. Fallback to `youtube-transcript-api`, then ASR.

**Instagram Reel (hybrid):**
- Try `instaloader` / `yt-dlp` for caption, likes, comments, uploader, duration, audio/MP4.
- **Detect null/blocked fields** (views, follower count commonly missing) → **fall back to Apify**
  `instagram-reel-scraper` for engagement + MP4, and `instagram-followers-count-scraper` (or profile
  scraper) for **follower count** (a separate profile fetch — note this in the README as a known
  quirk: follower count is never on the reel page).
- Transcript: Reels rarely have captions → extract audio with `yt-dlp -f bestaudio` → ASR.

**Transcript fallback chain (shared):**
1. Platform captions (yt-dlp auto-sub / youtube-transcript-api)
2. `yt-dlp -f bestaudio` → **Groq Whisper** (free, fast)
3. → **faster-whisper `base`** local ($0, no rate limit) — final backstop
- Every path normalizes to `[{start, end, text}]` segments so chunks carry timestamps.

**Metrics (`metrics.py`):** `engagement_rate = (likes + comments) / views * 100`, computed in code
(dynamic), rounded, stored per video. Guard divide-by-zero / null views (IG) → fall back to plays or
mark `N/A` and say so in the answer. Normalize both platforms into one `VideoMeta` schema.

**Caching:** key by canonical `video_id`; store metadata + transcript so re-runs are instant and free.

---

## RAG design (the part they grade hardest)

**Chunking — defensible default:** group transcript segments into **~300-token** chunks
(`RecursiveCharacterTextSplitter`, sentence-boundary separators) with **~15% overlap**, **carrying
`start_time`/`end_time`** from the segments.
- *Why 300 not 512:* short-form transcripts are tiny; smaller chunks → sharper retrieval, cheaper
  context, and **granular citations**. *Why overlap:* preserves the hook→body bridge. *Why timestamps:*
  they're what make "compare the first 5 seconds" a real query (filter `start_time < 5`), not a guess.
  Sub-60s videos may yield 1–3 chunks — fine; we retrieve top-k per video to recover context.

**Payload per chunk in Qdrant:** `{video_id: "A"|"B", chunk_id, start_time, end_time, text}`.
Per-video **stats** stored separately (small) and always injected — so metadata questions never depend
on fuzzy vector search.

**LangGraph graph (`rag/graph.py`):**
- **State:** `messages[]`, `query`, `route`, `retrieved[]`, `citations[]`.
- **Nodes:** `route` → (`retrieve_stats` | `retrieve_transcript` | `retrieve_comparison` | `retrieve_hook`)
  → `assemble_context` → `generate` → END.
- **`route`** (cheap LLM or rules) classifies: `stats` (engagement/views/followers/date),
  `transcript` (content/themes), `comparison` ("why did A beat B"), `hook` ("first 5 seconds").
- **Balanced retrieval** for comparison: top-k from `video_id=A` **and** top-k from `video_id=B`
  separately (never a global top-k that could return only A).
- **Hook retrieval:** filter `start_time < 5` per video → earliest chunk(s).
- **`assemble_context`** ALWAYS prepends compact **A & B stats cards** + the retrieved chunks with
  their `[A#id]/[B#id]` tags → makes both metadata and transcript answers grounded and citable.
- **`generate`:** Gemini streams; system prompt forces citations using only the injected chunk ids
  (anti-hallucination: the client also receives the real retrieved-chunk list, so citations are
  verifiable, not LLM-invented).

**Memory:** LangGraph **checkpointer** (`MemorySaver` dev / `SqliteSaver` persistent) keyed by
`thread_id` (one per chat session) → follow-ups like "and what about B?" work. Keep last N turns to
cap tokens.

**Streaming (SSE):** FastAPI `StreamingResponse` over `graph.astream_events(version="v2")`; emit
`{type:"token"}` per chunk, `{type:"citation", video_id, chunk_id, start_time, quote}` for sources,
and a final `{type:"done"}`. Frontend renders tokens live + citation chips.

**The 5 required questions → how the system answers them dynamically:**
1. *Why did A get more engagement than B?* → `comparison`: both stats cards + balanced A/B transcript chunks.
2. *Engagement rate of each?* → `stats`: read computed rates directly.
3. *Compare the hooks in first 5 seconds* → `hook`: time-window `start_time<5` from each.
4. *Creator of B + follower count?* → `stats`: structured fields (followers from the profile fetch).
5. *Suggest improvements for B based on A* → `comparison`: A's high-performing chunks + both stats → LLM synthesis.

---

## Frontend

- **Layout:** two `VideoCard`s side-by-side (thumbnail/embed, creator, followers, views, likes,
  comments, **engagement rate**, hashtags, date, duration) + a `ChatPanel`.
- **Streaming:** `lib/sse.ts` consumes the SSE stream, appends tokens live, renders **citation chips**
  ("Video A · 0:03 · chunk 3") that expand to the quoted transcript span.
- **Perf focus (they care about speed, not aesthetics):** virtualize/append messages, no re-render of
  the whole list per token, show a skeleton during ingest. Tailwind for fast, clean styling.

---

## Cost & scale — the "defend on a call" section

**Per-creator economics (1,000 creators/day = 2,000 videos/day):** captions-first keeps most videos
off ASR; ASR overflow → Groq free / local Whisper ≈ **$0**. Embeddings: local BGE **$0**. Vector
storage: negligible. LLM: Gemini Flash free tier / pennies. **Realistic bill ≈ $0–$120/mo**; per
creator **< $0.01–0.10/day**.

**The real bottleneck is data acquisition, not RAG.** LLM + vector + embedding costs scale linearly
and stay cheap. What strains first:
- **What breaks at 10,000 users:** (1) **transcript/metadata extraction** — YouTube IP bans (need
  rotating *residential* proxies, e.g. Webshare) + IG rate limits/login walls (lean on Apify, budget
  ~$5–7/day) + ASR throughput → solve with an **async worker queue** (Cloud Tasks / Celery+Redis) and
  **caching/dedupe by `video_id`**; (2) **vector memory** if you keep everything forever → quantization
  / TTL / Qdrant paid (~$57/GB-mo, still cheap); (3) **LLM rate limits** → batch, multiple keys, or
  paid tier. Acquisition is the wall; everything downstream is linear and cheap.

**Defensible Q&A to rehearse:** *Why Qdrant?* free-tier + metadata filtering + local/prod parity.
*Why this chunk size?* granularity + timestamps for hook queries. *Why BGE not OpenAI?* $0 at scale,
no rate limit. *Why LangGraph not LCEL?* memory + routing + branching. *Why SSE not WebSockets?*
one-way stream, simpler, proxy-friendly. *Biggest scale risk?* data acquisition (bans/rate limits),
mitigated by caching + queue + Apify + proxies.

---

## Repo layout

```
backend/app/
  main.py                # FastAPI: /ingest, /chat (SSE), /health
  models.py              # VideoMeta, Chunk, ChatRequest (pydantic)
  config.py  cache.py
  ingest/  youtube.py  instagram.py  transcripts.py  metrics.py
  rag/     graph.py  router.py  retrieval.py  embeddings.py  vectorstore.py  prompts.py  memory.py
backend/{requirements.txt, Dockerfile, .env.example}
frontend/src/{App.tsx, api.ts, lib/sse.ts, components/{VideoCard,ChatPanel,Message,Citation}.tsx}
frontend/{package.json, vite.config.ts, Dockerfile}
docker-compose.yml       # qdrant + backend + frontend
README.md  .gitignore
```

---

## 5-day execution (commits that tell a story)

- **Day 1 — Skeleton + YouTube ingest.** Scaffold backend/frontend, `docker-compose` w/ Qdrant,
  pydantic models. `yt-dlp` YouTube metadata + captions; engagement-rate calc.
  Commits: `chore: scaffold backend+frontend+qdrant compose` · `feat(ingest): youtube metadata via yt-dlp` ·
  `feat(metrics): engagement rate from likes+comments/views`.
- **Day 2 — Instagram + transcript chain.** Hybrid IG (OSS → Apify fallback) + follower-count profile
  fetch; transcript fallback chain (captions → Groq → faster-whisper) with timestamps; caching.
  Commits: `feat(ingest): instagram reel (instaloader) + apify fallback` · `feat(ingest): follower count via profile scrape` ·
  `feat(transcripts): caption→groq→faster-whisper fallback chain` · `perf(cache): memoize transcripts by video_id`.
- **Day 3 — Embed + store + retrieval.** BGE embeddings, Qdrant upsert with `video_id`/timestamps;
  retrieval fns (balanced per-video, time-window, stats).
  Commits: `feat(rag): bge embeddings + qdrant upsert with metadata` · `feat(rag): balanced + time-window retrieval`.
- **Day 4 — LangGraph + API.** Router, context assembler, generate w/ citations, checkpointer memory,
  FastAPI SSE endpoint.
  Commits: `feat(rag): langgraph router+generate with citations` · `feat(rag): conversation memory via checkpointer` ·
  `feat(api): SSE streaming chat endpoint`.
- **Day 5 — Frontend + deploy + Loom.** Video cards + chat + streaming + citation chips; polish;
  Dockerize; deploy (Cloud Run + Vercel + Qdrant Cloud); README + `.env.example`; record Loom.
  Commits: `feat(ui): side-by-side video cards` · `feat(ui): streaming chat + citation chips` ·
  `docs: README with architecture + tradeoffs + cost analysis` · `chore: dockerfiles + cloud run deploy`.

---

## Verification (end-to-end)

1. `docker-compose up` (Qdrant) → run backend → `POST /ingest` with the two hard-coded URLs → assert
   it returns both `VideoMeta` (all fields) + engagement rates + chunk counts.
2. Open frontend → both cards populate with metadata + engagement rate.
3. Ask all **5 required questions**; verify: tokens **stream**, **citations** show (video + chunk +
   timestamp), and **memory** holds (follow-up "and B?" resolves the antecedent).
4. **Edge cases:** a video with no captions (forces ASR), an IG reel with null views (graceful `N/A`),
   a private/deleted URL (clean error, no crash).
5. **Cost lever proof:** re-ingest same URLs → served from cache instantly (no re-download/re-embed).
6. Record the Loom doing exactly this, start to finish, with two **real** URLs.

---

## Submission (reply template to fill at the end)

```
Project URL   : <deployed Vercel/Cloud Run link>
Project Desc  : <human-written 2–3 lines: what it does + stack + key tradeoffs>
Loom URL      : <full start-to-finish demo>
GitHub Repo   : <clean repo: README, .env.example, story-telling commits>
```

**README must include (this is what gets you the call):** architecture diagram, the trade-off table
above with the *why*, the chunk-size/vector-DB justifications, and the cost/scale ("what breaks at
10k") section — written in your own voice.
