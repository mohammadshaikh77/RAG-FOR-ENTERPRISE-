# ADR 0006 — Automated Evaluation Harness, Multi-Modal Ablations, and CI Regression Gate

## Status
Accepted (Amended in Phase 6b)

## Context
A critical requirement for enterprise clinical and pharmaceutical RAG systems is provable grounding, zero hallucination, and deterministic safety checks. Without automated, reproducible evaluation, changes to chunking parameters, embedding weights, reciprocal rank fusion (RRF) constants, or LLM system prompts risk silently degrading retrieval quality and clinical safety.

Furthermore, Rule 3 of Cite mandates: *"Never invent numbers. Every metric, latency or comparison in the README and docs must come from an actual run of the eval harness, with the results file committed."*

In Phase 6b, the evaluation framework was upgraded to achieve rigorous trustworthiness:
1. Model independence: Answerer model (`gemini-flash-lite-latest`) is decoupled from the Judge model (`gemini-3.1-flash-lite`).
2. Smoke test policy: Any mock run is strictly labeled `SMOKE TEST – not a quality result` in CLI and UI.
3. Dataset curation: 100-item golden set split into 60 dev / 40 held-out test items, 100% human-reviewed (`scripts/review_golden_set.py`), with harder clinical unanswerables and indirect document-level prompt injections.
4. Keyword search diagnosis & fix: Investigated why keyword search scored 17.3%; fixed tsquery AND-conjunction failure by introducing clinical stopword filtering and OR-disjunction ranking (`websearch_to_tsquery(...) || to_tsquery(...)`).
5. Statistical rigor: Bootstrap 95% confidence intervals (1,000 resamples) computed for all retrieval metrics.
6. CI regression gate: Transitioned from relative delta checks to absolute performance floors evaluated on the held-out test set.

## Decision

### 1. Ground Truth Dataset (`eval/golden_set/qa_golden_set.jsonl`)
The golden set contains 100 verified QA items from ingested FDA drug labels under the `Demo Pharma Therapeutics` tenant:
- **40 Single-Document Factual Queries:** Direct extractions covering boxed warnings, indications, dosages, contraindications, and adverse events.
- **20 Multi-Document Comparative Queries:** Contrasting black box warnings, mechanisms of action, and drug classes across related drugs (e.g. Lisinopril vs Metformin, Naproxen vs Celecoxib).
- **15 Structured Metadata Queries:** Inquiring about pharmacological classes, routes of administration, and presence of black box warnings.
- **15 Hard Unanswerable Queries:** Testing refusal target detection on unapproved off-label claims for real drugs (e.g. Lisinopril for major depression) and fictitious compounds.
- **10 Adversarial & Indirect Injections:** Testing defense against system prompt extraction, jailbreaks (DAN), safety overrides, and indirect injection payloads hidden inside document text.

All 100 items are human-reviewed (`human_reviewed: true`) and partitioned into 60 dev and 40 held-out test items. Tuning is restricted to the dev partition.

### 2. Retrieval Ablations & Empirical Findings
We evaluate four retrieval modes across all 75 answerable queries:
- `vector`: Dense semantic search using pgvector cosine distance (`1 - (embedding <=> query_vec)`).
- `keyword`: Sparse lexical full-text search with PostgreSQL `ts_rank_cd` and English stemming.
- `hybrid`: Reciprocal Rank Fusion ($RRF = \sum \frac{1}{k + rank}$, $k=60$) fusing dense and sparse candidate sets.
- `hybrid_rerank`: Hybrid RRF search combined with cross-encoder reranking (`cross-encoder/ms-marco-TinyBERT-L-2-v2`).

**Measured Results from `eval/results/summary.json` (Real Gemini Run):**

#### Held-Out Test Set (n=30 answerable queries)
| Retrieval Mode | MRR [95% CI] | Recall@5 [95% CI] | Hit Rate@5 [95% CI] | Recall@3 | Hit Rate@3 |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Vector** | 0.5622 [0.418, 0.701] | 71.7% [55.0%, 85.0%] | 80.0% [63.3%, 93.3%] | 65.0% | 76.7% |
| **Keyword** | 0.4833 [0.356, 0.608] | 70.0% [55.0%, 85.0%] | 76.7% [60.0%, 90.0%] | 56.7% | 63.3% |
| **Hybrid (RRF)** | 0.5289 [0.412, 0.653] | **83.3%** [71.7%, 95.0%] | **90.0%** [80.0%, 100.0%] | 65.0% | 76.7% |
| **Hybrid + Rerank** | **0.5911** [0.437, 0.730] | 73.3% [58.3%, 86.7%] | 76.7% [60.0%, 90.0%] | **70.0%** | **76.7%** |

#### Full Dataset (n=75 answerable queries)
| Retrieval Mode | MRR [95% CI] | Recall@5 [95% CI] | Hit Rate@5 [95% CI] | P50 Latency | Mean Latency |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Vector** | 0.5662 [0.483, 0.654] | 77.3% [68.7%, 85.3%] | 85.3% [77.3%, 93.3%] | 4.71 ms | 5.44 ms |
| **Keyword** | 0.5316 [0.443, 0.626] | 70.0% [60.7%, 78.7%] | 80.0% [70.7%, 88.0%] | 14.88 ms | 14.92 ms |
| **Hybrid (RRF)** | 0.5678 [0.488, 0.645] | 80.7% [73.3%, 88.0%] | **89.3%** [82.7%, 96.0%] | 22.09 ms | 22.84 ms |
| **Hybrid + Rerank** | **0.5864** [0.501, 0.676] | **82.0%** [74.0%, 89.3%] | **89.3%** [81.3%, 96.0%] | 63.82 ms | 65.17 ms |

*Investigation & Fix:*
Keyword search originally scored 17.3% because `websearch_to_tsquery` applied strict boolean `AND` across all words in conversational user prompts. By implementing stop-word removal and OR-ranked phrase combinations, Keyword Hit Rate@5 jumped to **80.0%** overall and **76.7%** on held-out test.

### 3. LLM Attribution & Safety Metrics
- **Answerer Model:** `gemini-flash-lite-latest`
- **Judge Model:** `gemini-3.1-flash-lite` (independent evaluation)
- **Citation Precision:** **96.7%** on held-out test (29/30 verified), **98.6%** overall (69/70 verified).
- **True Refusal Rate:** **90.0%** on held-out test (9/10), **88.0%** overall (22/25).
- **Judge Faithfulness:** **4.50 / 5.0** on held-out test, **4.57 / 5.0** overall.
- **Judge Correctness:** **3.83 / 5.0** on held-out test, **3.87 / 5.0** overall.

### 4. CI Quality Gate with Absolute Floors (`eval/ci_gate.py`)
- Evaluates retrieval against absolute minimum quality thresholds on the held-out test partition:
  - `HitRate@5 >= 0.75` (Measured: 0.9000 ✅)
  - `Recall@5 >= 0.70` (Measured: 0.8333 ✅)
  - `MRR >= 0.45` (Measured: 0.5289 ✅)
  - `HitRate@3 >= 0.60` (Measured: 0.7667 ✅)
- Runs locally and in GitHub Actions in ~2 seconds without LLM API calls.

## Consequences
- **Positive:** Evaluation is fully trustworthy, transparent, and reproducible with zero invented numbers.
- **Positive:** Clear decoupling between answer generation model and judge model prevents self-evaluation bias.
- **Positive:** CI quality gate provides hard regression prevention based on real variance.
- **Trade-off:** Reranker adds ~40ms latency (P50 63.8ms vs 22.1ms for hybrid), but provides the highest MRR (0.5911).
