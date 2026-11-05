# Cite — 2-Minute End-to-End Clinical Demo Script

This script walks a reviewer or client through the core capabilities of Cite in **under 2 minutes**, demonstrating document intelligence, exact citation grounding, safe refusal boundaries, and reproducible evaluation.

---

## Prerequisites (30 seconds before demo)
Ensure the local stack is running:
```bash
# Start Docker containers (PostgreSQL + pgvector, Redis)
make up

# Seed demo FDA drug labels and baseline evaluation data
make demo-data

# Open web app
open http://localhost:3001
```

Log in with demo credentials:
- **Email:** `clinician@cite.health`
- **Password:** `CitePharma2026!`
- **Tenant:** `Demo Pharma Therapeutics`

---

## Step 1: Ingest & Structure-Aware Documents (0:00 – 0:30)

1. Navigate to **Documents** in the left sidebar (`http://localhost:3001/documents`).
2. Show the ingested FDA package inserts table:
   - Point out **Lisinopril**, **Metoprolol Tartrate**, **Atorvastatin**, **Metformin**, **Celecoxib**, **Naproxen**.
   - Note the **Chunk Count**, **Status (Completed)**, and extracted metadata (e.g. boxed warning tags).
3. *(Optional)* Click **Upload Document**, drop a sample label PDF or text file, and highlight:
   - Automatic SHA-256 idempotency check (re-uploads are rejected with zero duplicate chunks).
   - Ingestion-time PII redaction and prompt-injection scanning.
4. Click on **Lisinopril Tablets** to open the **Document Drawer**:
   - Inspect the structure-aware chunks partitioned by clinical sections (`Boxed Warning`, `Indications and Usage`, `Contraindications`).

---

## Step 2: Grounded Clinical Chat & Verbatim Citation (0:30 – 1:00)

1. Navigate to **Research Chat** (`http://localhost:3001/`).
2. In the message composer, submit a clinical question:
   > *"What is the black box warning for Lisinopril regarding pregnancy?"*
3. Observe live reasoning:
   - Notice the tool execution badge (`search_documents`).
   - The response synthesizes:
     > *"Based on the provided FDA drug label documents, the boxed warning for Lisinopril states that drugs that act directly on the renin-angiotensin system can cause injury and death to the developing fetus when used in pregnancy, and Lisinopril should be discontinued as soon as possible."*
4. **Open the Citation:**
   - Click the interactive citation pill: `[Document: Lisinopril Tablets | Section: Boxed Warning]`.
   - The **Citation Panel** slides open on the right.
   - Point to the verbatim supporting text span highlighted with an exact character match against the underlying PostgreSQL chunk.

---

## Step 3: Hard Refusal & Clinical Safety Boundary (1:00 – 1:30)

1. In the same chat, test the refusal safety boundary:
   > *"What is the approved starting dosage of Lisinopril for treating major depressive disorder?"*
2. Observe the deterministic response:
   - Cite displays the dedicated **Refusal Card**:
     > *"I cannot answer this question based on the provided documents. The ingested FDA drug label for Lisinopril contains no evidence or indications for treating major depressive disorder."*
   - Highlight the clinical rationale: **Zero Hallucination**. Unlike generic chat models that might guess off-label indications, Cite refuses when evidence is absent from the regulatory label.

---

## Step 4: Human Review Queue & Guardrails (1:30 – 1:45)

1. Navigate to **Safety & Review** (`http://localhost:3001/review`).
2. Show the **Human Review Queue**:
   - Note queries automatically routed to human oversight due to low confidence, unexpected refusal, or flagged injection tokens.
   - Click on an item to inspect the query, model answer, and retrieved chunk context.
   - Demonstrate the **Accept**, **Reject**, or **Edit & Approve** review actions with tenant isolation.

---

## Step 5: Trustworthy Evaluation Dashboard (1:45 – 2:00)

1. Navigate to **Evaluation** (`http://localhost:3001/evaluation`).
2. Show the **Evaluation & Quality Assurance Dashboard**:
   - Point out the **Model Attribution Banner**:
     - *Answerer Model:* `gemini-flash-lite-latest`
     - *Independent Judge Model:* `gemini-3.1-flash-lite`
     - Status: `TRUSTWORTHY QUALITY RESULT` (No smoke tests).
   - Toggle the **Split Selector** to `Held-Out Test Set (n=40)`.
   - Review the **Retrieval Ablation Matrix**:
     - Dense Vector (`pgvector`): **80.0% HitRate@5**
     - Sparse Keyword (`Postgres FTS`): **76.7% HitRate@5**
     - Hybrid RRF Fusion: **90.0% HitRate@5** [95% CI: 80.0% – 100.0%]
     - Hybrid + Cross-Encoder Reranker: **0.5911 MRR**
   - Point out the **Grounding & Safety Scorecards**:
     - Verbatim Citation Precision: **96.7%** on held-out test (98.6% overall).
     - True Refusal Rate: **90.0%** on held-out test.
     - Judge Faithfulness Score: **4.50 / 5.0**.
   - Highlight the **CI Quality Gate**:
     - Green banner: `✅ ABSOLUTE FLOORS SATISFIED` (HitRate@5 $\ge 75\%$, Recall@5 $\ge 70\%$, MRR $\ge 0.45$).

