# Cite — Known Limitations and System Boundaries

This document records the architectural boundaries, operational constraints, and known trade-offs of the Cite document question-answering platform.

---

## 1. Retrieval & Answer Quality

- **Retrieval Coverage & False Refusals:** On our held-out test set, Cite refused 26.7% of valid questions (8 out of 30). This is primarily caused by retrieval misses where the relevant text section was not within the top retrieved chunks, leading the model to accurately state that the document context did not contain enough evidence.
- **Chunking Boundaries:** Fixed-size chunking can sometimes split connected context across chunk boundaries, impacting retrieval recall for questions that require reasoning across long passages.
- **Reranking Overhead:** Adding cross-encoder reranking provides marginal MRR improvement on our benchmark but adds ~40ms of latency per query. On small datasets, confidence intervals between hybrid retrieval and reranked retrieval overlap significantly.

---

## 2. Model Dependency & Rate Limits

- **LLM Provider Availability:** Cite supports both Groq and Gemini APIs, with local fallback for testing. Cloud LLM providers are subject to upstream rate limits and transient 429 errors.
- **Token Quotas:** On high-throughput workloads, free and standard API tiers may exhaust request or token quotas, requiring rate limiting and bounded backoff.
- **Model Decoupling in Evaluation:** Automated evaluation metrics scored by an LLM judge are useful for regression testing but remain sensitive to prompt variations and judge model subjectivity.

---

## 3. Guardrails & Safety Boundaries

- **Pattern-Based PII Redaction:** PII redaction uses regular expressions for common patterns (emails, phone numbers, standard ID formats). While fast and zero-cost, regex pattern matching does not identify contextual personal identifiers like unstructured names or locations.
- **Prompt Injection Detection:** Chunk and input scanning relies on known injection signatures and prompt delimiters. While effective against direct injection attempts in our regression test set, heuristic pattern matching is not an absolute security guarantee and can potentially be bypassed by novel or obfuscated adversarial prompts.
- **Human Review Queue:** Items flagged for low confidence, unexpected refusal, or suspected injection require review. Without reviewer triage, unreviewed items will remain pending.

---

## 4. Ingestion & Documents

- **Text Extraction:** Ingestion currently parses digital text from PDFs, HTML, and plain text files. Scanned documents or image-only PDFs without an embedded text layer require optical character recognition (OCR) before ingestion.
- **Single-Language Focus:** Full-text search leverages PostgreSQL English text search (`tsvector`/`tsquery`). Documents in other languages require appropriate text search configuration.
