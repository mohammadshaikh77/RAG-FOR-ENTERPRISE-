# Automated Evaluation Harness & Benchmarks

Cite features an automated, zero-cost evaluation harness and CI regression gate designed specifically for clinical pharma regulatory documents (FDA drug labels).

In accordance with Cite's engineering standards:
> **Rule 3:** Never invent numbers. Every metric, latency or comparison in the README and docs must come from an actual run of the eval harness, with the results file committed.

---

## 1. Quick Start

Run the full evaluation harness and regenerate reports:
```bash
make eval
```

Run the fast LLM-free retrieval CI regression gate:
```bash
make ci-gate
```

---

## 2. Benchmark Dataset (`eval/golden_set/qa_golden_set.jsonl`)

The evaluation harness evaluates **100 ground-truth QA triples** created from real FDA clinical package inserts ingested under the `Demo Pharma Therapeutics` tenant:

| Category | Count | Description | Primary Verification Target |
| :--- | :--- | :--- | :--- |
| **Single-Document Factual** | 40 | Indications, black box warnings, dosages, contraindications | Direct recall & exact text span grounding |
| **Multi-Document Comparative** | 20 | Contrasting warnings, mechanisms, and drug classes | Multi-hop chunk retrieval & synthesis |
| **Structured Metadata** | 15 | Identifying drug classes, boxed warning presence, route | SQL and hybrid metadata filtering |
| **Unanswerable (Out-of-Domain)** | 15 | Fictitious entities, astrophysics, recipes, stocks | Explicit refusal ("I cannot answer this...") |
| **Adversarial Injections** | 10 | Prompt extraction, DAN jailbreaks, safety overrides | Clinical safety boundary enforcement |

---

## 3. Retrieval Ablation Matrix

Evaluation across all 75 answerable queries comparing four retrieval paradigms:

| Retrieval Mode | MRR | Recall@5 | Hit Rate@5 | Recall@3 | Hit Rate@3 | P50 Latency | Mean Latency |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Vector (pgvector)** | 0.5662 | 77.3% | 85.3% | 64.0% | 72.0% | 15.0 ms | 83.2 ms |
| **Keyword (Postgres FTS)** | 0.1278 | 17.3% | 17.3% | 16.0% | 16.0% | 0.8 ms | 1.5 ms |
| **Hybrid (RRF Fusion)** | 0.5389 | 76.0% | 84.0% | 65.3% | 73.3% | 6.3 ms | 6.8 ms |
| **Hybrid + Reranker** | **0.5967** | **82.0%** | **92.0%** | **71.3**% | **78.7%** | **7.2 ms** | **8.1 ms** |

### Key Clinical Insights:
1. **Keyword Search Failure:** Lexical full-text search fails on 82.7% of queries because clinical questions rarely match the formal medical vocabulary of package inserts verbatim (e.g., asking about "fetal harm during pregnancy" when the label says "fetal toxicity").
2. **Dense Vector Efficacy:** Dense embeddings (`sentence-transformers/all-MiniLM-L6-v2`) capture clinical synonyms and achieve an 85.3% Hit Rate@5.
3. **Reranker Dominance:** Combining RRF hybrid candidate retrieval with cross-encoder reranking boosts Hit Rate@5 to **92.0%** and MRR to **0.5967**, delivering the highest precision ranking.

---

## 4. Citation Precision & Grounding Guarantee

Every statement synthesized by the agent must cite its source in structured format:
`[Document: <Title> | Section: <Section> | "<exact quoted span>"]`

- **Total Citations Evaluated:** 16
- **Programmatically Verified Spans:** 16
- **Verbatim Citation Precision:** **100.0%**

The evaluation engine programmatically checks that the quoted excerpt exists verbatim in the retrieved chunk content.

---

## 5. Refusal Robustness & Safety

When questions ask for information not in the FDA drug labels or attempt prompt injections, the agent must refuse:

- **True Refusal Rate (Unanswerables & Injections):** **100.0%** (7/7 refused)
- **False Refusal Rate (Valid Clinical Questions):** **0.0%** (0 valid queries refused)

---

## 6. CI Quality Gate (`eval/ci_gate.py`)

The CI quality gate is an ultra-fast, LLM-free test that runs in continuous integration without API keys.

It evaluates current retrieval performance against `eval/baseline.json`. If **MRR** or **Recall@5** drops by more than **3.0% (0.03)** below baseline, the build fails with exit code 1.

```
============================================================
 CITE CI QUALITY GATE RESULTS
============================================================
Total Evaluated Queries: 75
Metric             | Current    | Baseline   | Delta     
------------------------------------------------------------
✅ mrr              | 0.5389     | 0.5389     | +0.0000
✅ recall_at_5      | 0.7600     | 0.7600     | +0.0000
✅ hit_rate_at_5    | 0.8400     | 0.8400     | +0.0000
✅ recall_at_3      | 0.6533     | 0.6533     | +0.0000
✅ hit_rate_at_3    | 0.7333     | 0.7333     | +0.0000
============================================================
✅ CI QUALITY GATE PASSED
```

Regression detection is tested by `tests/test_ci_gate.py` using a simulated degraded retriever.
