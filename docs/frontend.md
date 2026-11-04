# Frontend Architecture & Verification — "Cite"

This document details the frontend implementation for **Cite**, an enterprise multi-tenant agentic document-intelligence platform built for regulated pharma drug label RAG.

---

## 1. Stack & Design Direction

- **Core Framework:** React 18 + plain JavaScript (JSX) + Vite 5.
- **Language Policy:** **Strictly plain JSX (`.js`, `.jsx` only)**. No TypeScript (`.ts`, `.tsx`, `tsconfig.json`) or `@types` packages anywhere in the frontend codebase. JSDoc comments define component props and API payloads.
- **Styling & Tokens:** Tailwind CSS configured with HSL design tokens (`src/index.css`):
  - **Clinical Teal Accent:** `hsl(175, 84%, 32%)` (deep clinical teal, avoiding purple-gradient-on-white cliches).
  - **Theme System:** Full light and dark mode with system preference detection and zero flash on initial load (`index.html` inline script).
  - **Geometry:** Consistent 8px spacing grid, subtle borders (`border-border`), and rounded-xl containers.
- **Typography:** Self-hosted via Fontsource (zero third-party web requests):
  - UI Font: `@fontsource/inter` (Inter 400, 500, 600, 700).
  - Monospace Font: `@fontsource/jetbrains-mono` (JetBrains Mono 400, 500) for citations, chunk tokens, and hashes.
- **Components & Accessibility:** Unstyled Radix UI primitives (`@radix-ui/react-popover`, `@radix-ui/react-dialog`, `@radix-ui/react-tooltip`) paired with Lucide React icons. WCAG AA accessible with keyboard navigation and visible focus rings.
- **Data & Markdown:** TanStack Query (`@tanstack/react-query`) for API fetching and caching; `react-markdown` + `remark-gfm` for grounded answers.

---

## 2. Key Pages & Features

### 1. Authentication (`/login`, `/register`)
- **Split Layout:** Left marketing panel highlights value proposition (Structure-Aware Ingestion, Bounded Tool-Calling Agent, Strict Multi-Tenancy) and demo domain (US FDA Drug Labels).
- **Tenant Onboarding:** Automatic slug generation, admin user registration, and tenant-scoped JWT session management.
- **Demo Access:** Pre-seeded admin account (`admin@demopharma.com` / `demopassword123`) grants immediate access to the 42 openFDA drug label documents.

### 2. Document Intelligence Repository (`/documents`)
- **Drag-and-Drop Ingestion:** Multi-file drag-and-drop zone supporting PDF, text, and HTML formats with client-side file size and MIME-type validation.
- **Repository Table:** Live ingestion status chips (`queued`, `processing`, `completed`, `failed`), chunk counts, file types, and deletion confirmation modal.
- **Document Detail Drawer:** Slides in from the right to inspect document metadata, SHA-256 hash, section outline, and individual structure-aware chunks with token counts.

### 3. Clinical Research Chat (`/`) — Hero Screen
- **SSE Streaming:** Streams real-time tokens, tool executions, and step updates from `POST /agent/query/stream`.
- **Live Agent Timeline:** Displays expandable "How I got this answer (N tools used)" badge detailing tool names, arguments, and step latencies.
- **Inline Citations & Sliding Panel:**
  - Citations rendered as interactive numbered chips `[1]`.
  - Hover triggers a Radix popover preview with document name and snippet.
  - Click slides in the **Supporting Evidence Panel** showing the exact FDA label, section path, and the full retrieved chunk with the supporting text span highlighted via `<mark>`.
- **Refusal Card:** Dedicated refusal card rendered when evidence cannot be verified or query violates boundaries.
- **Execution Audit Drawer:** Allows inspection of model name, prompt tokens, completion tokens, latency breakdown, and execution steps.
- **User Feedback:** Thumbs up / thumbs down buttons submit quality feedback directly to `POST /agent/feedback`.
- **Clinical Disclaimer:** Pinned disclaimer: *"Answers are generated from your documents and may be wrong. Not medical advice."*

### 4. Admin & Safety Placeholders
- **Evaluation (`/evaluation`)**: Clean placeholder explaining the 100-question golden eval harness (Phase 6).
- **Safety & Review (`/review`)**: Clean placeholder explaining guardrails and human review (Phase 7).
- **Settings (`/settings`)**: Theme toggle, tenant metadata, and authenticated user identity.

---

## 3. Screenshots (Playwright Captured)

The following screenshots are captured during Playwright smoke tests against the real ingested dataset:

| View | Screenshot |
|---|---|
| **Chat Desktop (Light)** | `docs/screenshots/chat-desktop-light.png` |
| **Chat Desktop (Dark)** | `docs/screenshots/chat-desktop-dark.png` |
| **Documents Repository** | `docs/screenshots/documents-desktop.png` |
| **Execution Audit Drawer** | `docs/screenshots/trace-drawer.png` |
| **Mobile Chat (Light)** | `docs/screenshots/chat-mobile-light.png` |
| **Mobile Chat (Dark)** | `docs/screenshots/chat-mobile-dark.png` |

---

## 4. Test Commands & CI Integration

### Component Unit Tests (Vitest)
```bash
make test-web
# or
cd apps/web && npm test
```
*7 component tests covering StatusChip, RefusalCard, and CitationPanel span highlighting.*

### End-to-End Smoke Tests (Playwright)
```bash
make test-e2e
# or
cd apps/web && npx playwright test
```
*6 end-to-end tests verifying unauthenticated redirect, tenant registration, demo document listing, drawer inspection, streaming chat with inline citations, and mobile responsive layout.*

### Linting & Formatting
```bash
cd apps/web && npm run lint
```
*Clean with 0 errors and 0 warnings.*

---

## 5. Docker & Production Deployment

- **Dockerfile (`apps/web/Dockerfile`):** Multi-stage build (Node 20 Alpine builder -> Nginx 1.25 Alpine runner).
- **Nginx Config (`apps/web/nginx.conf`):** Configured with SPA client-side routing fallback (`try_files $uri $uri/ /index.html`), gzip compression, and reverse proxy forwarding for `/api/` to the FastAPI backend.
- **Docker Compose:** Added `web` service on port `3001`:
```bash
docker compose up -d web
```
Accessible in browser at `http://localhost:3001`.
