# ADR 0006 — Automated Evaluation Harness, Multi-Modal Ablations, and CI Regression Gate

## Status
Accepted

## Context
A critical requirement for enterprise clinical and pharmaceutical RAG systems is provable grounding, zero hallucination, and deterministic safety checks. Without automated, reproducible evaluation, changes to chunking parameters, embedding weights, reciprocal rank fusion (RRF) constants, or LLM system prompts risk silently degrading retrieval quality and clinical safety.

Furthermore, Rule 3 of Cite mandates: *"Never invent numbers. Every metric, latency or comparison in the README and docs must come from an actual run of the eval harness, with the results file committed."*

We needed:
1. A ground-truth clinical dataset reflecting real OpenFDA package inserts across diverse question topologies.
2. An automated ablation harness comparing Vector, Keyword, Hybrid, and Cross-Encoder Reranked retrieval modes.
3. Programmatic citation verification to prove quoted spans exist verbatim in source text.
4. Robust refusal metrics verifying that out-of-domain and adversarial prompt injections are rejected.
5. An ultra-fast, zero-cost CI quality gate that halts builds if retrieval metrics regress by >3% below baseline.

## Decision

### 1. Ground Truth Dataset (`eval/golden_set/qa_golden_set.jsonl`)
We created a 100-item golden evaluation dataset generated from real FDA drug labels in the `Demo Pharma Therapeutics` tenant:
- **40 Single-Document Factual Queries:** Direct extractions covering boxed warnings, indications, dosages, contraindications, and adverse events.
- **20 Multi-Document Comparative Queries:** Contrasting black box warnings, mechanisms of action, and drug classes across related drugs (e.g. Lisinopril vs Metformin, Naproxen vs Celecoxib).
- **15 Structured Metadata Queries:** Inquiring about pharmacological classes, routes of administration, and presence of black box warnings.
- **15 Out-of-Domain Unanswerable Queries:** Testing refusal target detection on fictitious compounds, astronomical facts, and corporate credentials.
- **10 Adversarial Prompt Injections:** Testing defense against system prompt extraction, jailbreaks (DAN), safety overrides, and tenant exfiltration.

### 2. Retrieval Ablations & Empirical Findings
We implemented four retrieval ablation paradigms evaluated across all 75 answerable queries:
- `vector`: Dense semantic search using pgvector cosine distance (`1 - (embedding <=> query_vec)`).
- `keyword`: Sparse lexical full-text search with PostgreSQL `ts_rank_cd` and English stemming.
- `hybrid`: Reciprocal Rank Fusion ($RRF = \sum \frac{1}{k + rank}$) fusing dense and sparse candidate sets.
- `hybrid_rerank`: Hybrid RRF search combined with cross-encoder reranking.

**Measured Results (committed in `eval/results/summary.json`):**
| Retrieval Mode | MRR | Recall@5 | Hit Rate@5 | Recall@3 | Hit Rate@3 | P50 Latency | Mean Latency |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Vector** | 0.5662 | 77.3% | 85.3% | 64.0% | 72.0% | 15.0 ms | 83.2 ms |
| **Keyword** | 0.1278 | 17.3% | 17.3% | 16.0% | 16.0% | 0.8 ms | 1.5 ms |
| **Hybrid (RRF)** | 0.5389 | 76.0% | 84.0% | 65.3% | 73.3% | 6.3 ms | 6.8 ms |
| **Hybrid + Rerank** | **0.5967** | **82.0%** | **92.0%** | **71.3%** | **78.7%** | **7.2 ms** | **8.1 ms** |

*Key finding:* Keyword-only search fails dramatically (17.3% hit rate) due to clinical vocabulary divergence (e.g., "pregnancy warning" vs "fetal toxicity"). Hybrid search with cross-encoder reranking achieves the highest retrieval efficacy (**92.0% Hit Rate@5** and **0.5967 MRR**).

### 3. Programmatic Citation Precision & Refusal Accuracy
- **Citation Precision:** Extracts `[Document: ... | Section: ... | "..."]` tokens and verifies verbatim presence in the retrieved chunks. Measured at **100.0%**.
- **Refusal Robustness:** Evaluates that the agent explicitly refuses unanswerable queries and prompt injections (`is_refusal` check). Measured at **100.0% True Refusal Rate** with **0.0% False Refusal Rate**.

### 4. Fast CI Quality Gate (`eval/ci_gate.py`)
- Executes LLM-free retrieval across all golden queries in seconds.
- Asserts that MRR, Recall@5, and HitRate@5 do not degrade by more than 3.0% (0.03) against `eval/baseline.json`.
- Exits with non-zero code on regression. Verified via intentional regression unit tests in `tests/test_ci_gate.py`.

## Consequences
- **Positive:** Pull requests and parameter adjustments cannot silently degrade search or safety.
- **Positive:** Zero API cost for regression checks; reproducible in any local or CI environment via `make ci-gate` and `make eval`.
- **Positive:** Real numbers backed by committed artifacts (`eval/results/summary.json` and `eval/results/eval_report.md`).
