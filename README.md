# Cite — Enterprise Multimodal RAG Platform for Regulatory & Clinical Documents

[![CI Quality Gate](https://img.shields.io/badge/CI%20Quality%20Gate-PASS-success)](eval/ci_gate.py)
[![Citation Precision](https://img.shields.io/badge/Citation%20Precision-96.7%25-blue)](eval/results/summary.json)
[![Multimodal RAG](https://img.shields.io/badge/Multimodal%20RAG-PyMuPDF%20%2B%20Gemini%20Vision-blueviolet)](#6-zero-bloat-multimodal-diagram--figure-intelligence)
[![Zero-Cost Stack](https://img.shields.io/badge/Cost-Zero%20Paid%20APIs-brightgreen)](#)

**Cite** is an enterprise-grade, multi-tenant Retrieval-Augmented Generation (RAG) platform engineered for high-consequence regulatory, pharmaceutical, and technical document intelligence (such as FDA drug monographs, clinical trial reports, and package inserts).

Unlike naive RAG systems that suffer from hallucinations, vague summaries, and broken attributions, Cite enforces **structure-aware section chunking**, **multimodal diagram & pharmacokinetic figure intelligence**, **hybrid dense + sparse search with Reciprocal Rank Fusion (RRF)**, **local neural cross-encoder reranking**, and **strict verbatim character-span citation verification**.

---

## 1. System Architecture

```mermaid
flowchart TD
    subgraph ClientLayer["Client & Integration Layer"]
        WebUI["Web Application\n(React 18 + Vite + Tailwind CSS)"]
        MCPServer["Model Context Protocol (MCP) Server\n(Tool Provider for Anthropic/Claude Desktop)"]
        RESTAPI["FastAPI Backend\n(Async HTTP + SSE Streaming)"]
    end

    subgraph MiddlewareLayer["Security & Tenancy Guardrails"]
        TenantAuth["Tenant JWT Auth & Isolation\n(Strict org_id Scoping)"]
        RateLimiter["Token-Bucket & Redis Rate Limiter\n(Per-User & Global Protection)"]
        Delimiters["Passive Data Delimiters\n(Prompt Injection Mitigation)"]
    end

    subgraph IngestionLayer["Multimodal & Section Ingestion Pipeline"]
        PDFParser["Structure-Aware PDF Parser\n(PyMuPDF Primary + pypdf Fallback)"]
        ImageExtractor["Figure Extractor & Deduplicator\n(PyMuPDF Raster Extraction & Hash Caching)"]
        VisionCaptioner["Gemini Vision Captioner\n(gemini-3.5-flash with Token Bucket Limiter)"]
        Chunker["Structure-Aware Chunker\n(Bounded 220 Tokens per Chunk)"]
    end

    subgraph ReasoningLayer["Reasoning & Agent Tool Layer"]
        AgentLoop["Prompt-Guided Agent Loop\n(Grounded Synthesis with Zero Looping)"]
        LLMGateway["Resilient LLM Gateway\n(Groq gpt-oss-20b / Gemini 3.5 Flash / Ollama)"]
        Tools["Tools: search_documents, get_section, compare_documents, calculator"]
    end

    subgraph RetrievalLayer["Hybrid Retrieval & Reranking Engine"]
        VectorIndex["Dense Vector Index (pgvector 384-dim)\nsentence-transformers/all-MiniLM-L6-v2"]
        LexicalIndex["Conjunction Full-Text Search\n(PostgreSQL tsvector + ts_rank_cd)"]
        RRFFusion["Reciprocal Rank Fusion\n(RRF Score: k=60)"]
        CrossEncoder["Neural Cross-Encoder Reranker\nms-marco-TinyBERT-L-2-v2"]
    end

    subgraph StorageLayer["Persistent Storage"]
        Postgres[("PostgreSQL 16 + pgvector\n(Documents, Chunks, Traces, Tenants)")]
        RedisDB[("Redis 7\n(Rate Limiting & Async Queue)")]
    end

    WebUI --> RESTAPI
    MCPServer --> AgentLoop
    RESTAPI --> TenantAuth --> RateLimiter --> Delimiters --> AgentLoop
    RESTAPI --> IngestionLayer
    IngestionLayer --> Chunker & VisionCaptioner
    Chunker & VisionCaptioner --> VectorIndex & LexicalIndex
    AgentLoop <--> LLMGateway
    AgentLoop --> Tools
    Tools --> VectorIndex & LexicalIndex --> RRFFusion --> CrossEncoder
    VectorIndex & LexicalIndex --> Postgres
    RateLimiter --> RedisDB
```

---

## 2. Core Engineering Innovations

### 1. Section-Aware Document Ingestion & Alignment
* Standard RAG splits PDFs by fixed token count (e.g., 500 tokens), slicing sentences and severing headers from content.
* Cite uses **Structure-Aware Section Parsing** ([`pdf_parser.py`](packages/rag/src/rag/parsers/pdf_parser.py)), detecting regulatory headings (`4 CONTRAINDICATIONS`, `5.1 WARNINGS`, `8.1 PREGNANCY`, `12 CLINICAL PHARMACOLOGY`) and preserving semantic boundaries.
* Chunks are bounded to 220 tokens ([`chunker.py`](packages/rag/src/rag/chunker.py)), strictly matching the 256-token sequence limit of `all-MiniLM-L6-v2` to eliminate silent embedding truncation.

### 2. Zero-Bloat Multimodal Diagram & Figure Intelligence
* Clinical and technical PDFs communicate vital data through figures: pharmacokinetic concentration-time curves, dose-response graphs, chemical structures, and Kaplan-Meier survival plots.
* **Pure Python Extraction**: Uses `PyMuPDF` ([`image_extractor.py`](packages/rag/src/rag/parsers/image_extractor.py)) to extract embedded rasters directly—zero system binaries, zero `poppler` dependencies, keeping Docker builds simple and portable.
* **Smart Noise Filtering**: Automatically filters out tiny icons (<150 px), thin divider lines, and repetitive company headers. Bounding-box coverage detection distinguishes true embedded figures from full-page scanned paper.
* **Rate-Limited Vision Captioning**: Figures are analyzed via Gemini Vision ([`vision.py`](packages/llm/src/llm/vision.py)) using `gemini-3.5-flash` with in-memory SHA-256 deduplication caching and token-bucket throttling.
* **Unified Indexing (No CLIP RAM Overhead)**: Visual descriptions are stored as first-class chunks linked to their source page and image hash. They flow seamlessly through the existing `pgvector` dense search, PostgreSQL full-text search, and TinyBERT reranker without spinning up expensive vision-embedding models.

### 3. Accurate Scanned PDF Diagnostics (No Silent "Ready" Failures)
* Unlike naive systems that silently mark scanned image PDFs as "Ready" with 0 indexed sections, Cite inspects total pages vs. extractable text layers.
* If a 97-page scanned document contains 0 digital text characters, Cite marks the document status explicitly as **`FAILED`** and reports an actionable diagnostic error:
  > *"Scanned PDF detected (97 pages). Document contains scanned images without an embedded digital text layer. Optical Character Recognition (OCR) is required."*
* The UI displays an alert badge and details drawer, preventing users from asking questions against unindexed scanned files.

### 4. Hybrid Retrieval with Conjunction-First Lexical Search
* Pure vector search struggles with exact drug names and chemical nomenclature (e.g., distinguishing *lisinopril* from *metoprolol*). Pure keyword search fails on semantic intent (*fetal toxicity* vs *pregnancy risks*).
* Cite executes **Dense Vector Search** (`pgvector` cosine similarity) and **Conjunction-First Full-Text Search** (`websearch_to_tsquery` & `tsquery`), combining them via **Reciprocal Rank Fusion (RRF)**:
  $$\text{RRF Score}(d) = \sum_{m \in \{\text{vector}, \text{keyword}\}} \frac{1}{60 + \text{rank}_m(d)}$$

### 5. Local Neural Cross-Encoder Reranking
* Top 20 candidate passages are fed through a lightweight local cross-encoder (`cross-encoder/ms-marco-TinyBERT-L-2-v2`).
* Jointly attends to `[Section Title] + Passage Text` against the query, discarding misleading keyword-heavy paragraphs before the LLM prompt is assembled.
* Runs 100% locally on CPU in under 35 ms with **zero API cost**.

### 6. Verbatim Character-Span Citation Verification
* The system extracts citations and programmatically verifies every quoted text span against the stored chunk in PostgreSQL.
* The frontend ([`ChatMessage.jsx`](apps/web/src/components/chat/ChatMessage.jsx)) replaces raw bracketed citations with sleek, clickable `[1]`, `[2]` inline footnote chips that link directly to verified source text, section paths, and page numbers.

### 7. Multi-Provider Resilient LLM Gateway
* Configured with prioritized failover: **Groq (`openai/gpt-oss-20b`)** $\to$ **Google Gemini (`gemini-3.5-flash`)** $\to$ **Local Ollama**.
* Features token-bucket rate limiting and prompt-guided single-pass synthesis to eliminate runaway ReAct search loops and stay strictly within free-tier TPM limits.

---

## 3. Benchmark Evaluation Results

Cite includes an automated continuous evaluation harness ([`eval/harness.py`](eval/harness.py)) and a fast LLM-free regression check ([`eval/ci_gate.py`](eval/ci_gate.py)) tested on a verified 100-item golden evaluation dataset (60 Dev / 40 Held-Out Test).

### Retrieval Mode Ablation Matrix (Held-Out Test Set)

| Retrieval Strategy | MRR | Recall@5 | Hit Rate@5 | Recall@3 | Latency (P50) |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Dense Vector (`pgvector`)** | 0.5622 | 71.7% | 80.0% | 65.0% | 18 ms |
| **Sparse Keyword (PostgreSQL FTS)** | 0.4833 | 70.0% | 76.7% | 56.7% | 12 ms |
| **Hybrid (RRF Fusion)** | 0.5289 | **83.3%** | **90.0%** | 65.0% | 24 ms |
| **Hybrid + Neural Cross-Encoder** | **0.5911** | 73.3% | 76.7% | **70.0%** | 58 ms |

### Safety, Grounding & Refusal Reliability

| Metric | Target Floor | Measured Result | Evaluation Method |
| :--- | :---: | :---: | :--- |
| **Verbatim Citation Precision** | $\ge 95.0\%$ | **96.7%** | Programmatic character span verification against DB chunks |
| **Refusal Reliability (Unanswerables/Injections)** | $\ge 85.0\%$ | **90.0%** | Evaluates explicit refusal on unevidenced & malicious prompts |
| **False Refusal Rate (Valid Queries)** | $\le 30.0\%$ | **26.7%** | Known weakness; retrieval occasionally misses subtle sections |
| **LLM Judge Faithfulness** | $\ge 4.0 / 5.0$ | **4.50 / 5.0** | Independent rubric score via `gemini-3.5-flash` |
| **Prompt Injection Defense** | $\ge 95.0\%$ | **100.0%** | Tested against direct and indirect adversarial prompts |

---

## 4. Quickstart (Local Development)

### Prerequisites
- Docker & Docker Compose
- Python 3.11+
- Node.js 18+

### Step 1: Clone and Configure
```bash
git clone https://github.com/mohammadshaikh77/RAG-FOR-ENTERPRISE-.git
cd RAG-FOR-ENTERPRISE-

# Copy environment template
cp .env.example .env
# Edit .env and insert your GROQ_API_KEY and GEMINI_API_KEY
```

### Step 2: Start Infrastructure (Postgres + Redis)
```bash
make up
```

### Step 3: Populate Demo Clinical Labels & Sample Documents
```bash
make demo-data
```

### Step 4: Run Retrieval Regression CI Check
```bash
make ci-gate
```

### Step 5: Launch Services
```bash
# Terminal 1: Start Backend API
PYTHONPATH=".:packages/agent/src:packages/llm/src:packages/rag/src:packages/mcp/src" .venv/bin/uvicorn apps.api.src.main:app --host 0.0.0.0 --port 8000

# Terminal 2: Start Frontend Web App
cd apps/web && npm run dev -- --port 3001
```
Open `http://localhost:3001` in your browser.
- **Default Account:** `mohdxprojects@gmail.com`

---

## 5. Testing the Multimodal & Clinical Features

You can test both text and diagram extraction using the included sample documents in `data/`:

| Test Category | Target Document | Sample Question | Expected Behavior |
| :--- | :--- | :--- | :--- |
| **Multimodal PK Diagram** | `Keytruda_Clinical_Pharmacokinetics_Study.pdf` | *"According to Figure 1 on Page 2, what is the peak concentration (Cmax) and trough concentration (Cmin) over the 21-day cycle?"* | Extracts $C_{\max} \approx 92\ \mu\text{g/mL}$ and $C_{\min} \approx 22\ \mu\text{g/mL}$ citing `Figure (Page 2)`. |
| **Grounded Text QA** | Any FDA Drug Label (e.g. *Ozempic*, *Lisinopril*) | *"What is the boxed warning for Ozempic?"* | Direct, formatted answer citing thyroid C-cell tumor warnings with exact verbatim quotes. |
| **Hallucination Refusal** | Any FDA Drug Label | *"Does the Keytruda label list any contraindications for patients with renal impairment?"* | Correctly states no contraindications are listed, refusing to fabricate clinical claims. |
| **Scanned PDF Check** | `021923_s000_Nexavar_BioPharmR.pdf` | Upload file to Documents dashboard | Automatically diagnoses 0 digital text layers, flags status as `FAILED`, and prompts for OCR. |

---

## 6. Free Cloud Deployment Guide

Cite is architected to run **100% free** without paid cloud infrastructure:

| Component | Free Platform | Setup |
|---|---|---|
| **Database (`pgvector`)** | [Neon.tech](https://neon.tech) or [Supabase](https://supabase.com) | Create free Postgres project. Run `CREATE EXTENSION IF NOT EXISTS vector;` in SQL editor. |
| **Redis** | [Upstash](https://upstash.com) | Create free serverless Redis database (10k commands/day). |
| **Backend API** | [Render](https://render.com) or [Koyeb](https://koyeb.com) | Connect GitHub repo, deploy `apps/api/Dockerfile` as a Web Service. |
| **Frontend** | [Vercel](https://vercel.com) | Import GitHub repo, set root directory to `apps/web`, build with `npm run build`. |

---

## 7. Monorepo Project Structure

```text
├── apps/
│   ├── api/                 # FastAPI REST API, auth dependencies & routers
│   ├── web/                 # React 18, Vite, Tailwind CSS web interface
│   └── worker/              # Background worker for async document ingestion
├── packages/
│   ├── agent/               # Reasoning loop, citations, and tools (search, compare, calculator)
│   ├── llm/                 # Unified LLM Gateway (Groq, Gemini, Ollama) with vision & rate limiters
│   ├── rag/                 # Structure-aware chunking, embeddings, hybrid search, reranking & multimodal
│   └── mcp/                 # Model Context Protocol server implementation
├── data/
│   ├── demo_labels/         # Seed FDA clinical package inserts (Lisinopril, Metoprolol, Semaglutide)
│   └── Keytruda_Clinical_Pharmacokinetics_Study.pdf  # Sample multimodal study with embedded PK curve
├── docs/                    # Architecture Decision Records (ADRs) & limitations
├── eval/                    # Golden benchmark dataset, metrics calculation, and CI gate
├── scripts/                 # Utility scripts for data fetching and MCP execution
├── tests/                   # Pytest test suite (unit, integration & security checks)
├── docker-compose.yml       # Multi-container orchestration (PostgreSQL 16, pgvector, Redis 7)
├── Makefile                 # Developer command shortcuts
└── pyproject.toml           # Python dependencies and workspace definitions
```

---

## 8. License & Disclaimer

This project is licensed under the MIT License.

**Disclaimer:** Cite is an educational and technical demonstration platform engineered for regulatory document retrieval. It is **not** a certified medical diagnostic device and does not provide clinical or prescription medical advice.
