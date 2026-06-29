# YojnaSaathi — Project State & Architecture

> **IMPORTANT FOR ANY AI READING THIS:**
> This is the single source of truth for this project.
> Read this entire file before writing a single line of code.
> Check repomix-output.xml for the current file tree and actual code state.
> Never assume — always check what already exists before creating new files.

---

## Project Summary
AI assistant that finds Indian government schemes for any citizen based on
who they are. Multi-turn conversation → extract user profile → semantic
search → show matched schemes. Users can save their profile so they don't
re-answer questions every session.

---

## Tech Stack

### Frontend
- Framework: Next.js 16 (App Router, TypeScript)
- Styling: Tailwind CSS + shadcn/ui components
- Auth: Clerk
- AI streaming: Vercel AI SDK (useChat hook)
- Linting: Biome

### Backend
- Framework: FastAPI (Python 3.11+)
- Database: SQLite + SQLAlchemy + Alembic (migrations)
- Vector DB: ChromaDB (local, persisted to ./chroma_db/)
- LLM: Google Gemini 1.5 Flash
- Embeddings: Google embedding-001
- Orchestration: LangChain
- HTTP client: httpx (async, for scraper)
- Env config: pydantic-settings
- Linting: Ruff

### Data
- Seed: HuggingFace dataset shrijayan/gov_myscheme (723 schemes)
- Live sync: myscheme.gov.in/sitemap.xml (weekly GitHub Actions cron)
- Scheme expiry: soft delete SQLite + hard delete ChromaDB

### Infrastructure
- Frontend deploy: Vercel
- Backend deploy: Railway
- Cron jobs: GitHub Actions (.github/workflows/sync_schemes.yml)

---

## Folder Map

```
yojna-saathi/
├── CLAUDE.md                     ← YOU ARE HERE
├── .cursorrules                  ← tells Cursor: read CLAUDE.md first
├── .windsurfrules                ← tells Windsurf: read CLAUDE.md first
├── repomix.config.json           ← repomix config
├── ruff.toml                     ← Python linting config
├── biome.json                    ← Next.js linting config
│
├── frontend/                     ← Next.js 14 app
│   ├── app/
│   │   ├── layout.tsx            ← ClerkProvider wraps everything here
│   │   ├── page.tsx              ← Landing page
│   │   ├── sign-in/[[...sign-in]]/page.tsx
│   │   ├── sign-up/[[...sign-up]]/page.tsx
│   │   ├── chat/page.tsx         ← MAIN UI — conversation with AI
│   │   ├── profile/page.tsx      ← View + edit saved profile
│   │   ├── notifications/page.tsx
│   │   └── scheme/[id]/page.tsx  ← Full scheme detail
│   ├── components/
│   │   ├── ChatWindow.tsx
│   │   ├── ChatInput.tsx
│   │   ├── SchemeCard.tsx
│   │   ├── ProfileUpdatePrompt.tsx  ← inline "save this?" prompt in chat
│   │   ├── ProfileStrengthBar.tsx
│   │   └── NotificationBadge.tsx
│   ├── lib/
│   │   ├── api.ts                ← ALL fetch() calls live here only
│   │   ├── types.ts              ← TypeScript interfaces
│   │   └── profile-tracker.ts   ← localStorage helpers for tracker object
│   ├── proxy.ts                  ← Clerk: protects /chat /profile /notifications
│   ├── .env.local
│   └── package.json
│
├── backend/                      ← FastAPI Python app
│   ├── main.py                   ← app entry, CORS, router registration
│   ├── config.py                 ← pydantic-settings: all env vars + constants
│   ├── database.py               ← SQLAlchemy engine + get_db() dependency
│   ├── models.py                 ← ALL SQLAlchemy models in one file
│   │
│   ├── routers/
│   │   ├── chat.py               ← POST /api/chat
│   │   ├── profile.py            ← GET/PATCH/DELETE /api/profile
│   │   ├── schemes.py            ← GET /api/schemes, /api/schemes/{id}
│   │   ├── notifications.py      ← GET/PATCH /api/notifications
│   │   └── admin.py              ← POST /api/admin/sync (admin token only)
│   │
│   ├── agent/
│   │   ├── conversation.py       ← main agent loop (the brain)
│   │   ├── profile_extractor.py  ← Gemini call → JSON profile from message
│   │   ├── sufficiency_checker.py ← pure Python: is profile enough to search?
│   │   ├── question_generator.py ← Gemini → next clarifying question
│   │   └── update_suggester.py   ← detects new info → suggests saving
│   │
│   ├── rag/
│   │   ├── retriever.py          ← ChromaDB semantic search
│   │   └── prompts.py            ← ALL prompt templates
│   │
│   ├── notifications/
│   │   └── matcher.py            ← SQL-based user-scheme eligibility matching
│   │
│   ├── scripts/
│   │   ├── ingest_schemes.py     ← one-time seed from HuggingFace
│   │   └── sync_schemes.py       ← weekly diff sync + expiry + notifications
│   │
│   ├── middleware/
│   │   └── auth.py               ← Clerk JWT verification for FastAPI
│   │
│   ├── alembic/                  ← DB migrations (run: alembic upgrade head)
│   ├── tests/
│   ├── chroma_db/                ← gitignored — vector store on disk
│   ├── metadata.db               ← gitignored — SQLite file
│   ├── requirements.txt
│   └── .env
│
└── .github/
    └── workflows/
        └── sync_schemes.yml      ← weekly scheme sync cron (Sunday 2am IST)
```

---

## Database Models (SQLite via SQLAlchemy)

```
schemes          → id, name, eligibility, benefits, category, state,
                   status (active/inactive), tags (JSON), source_url,
                   last_synced_at

user_profiles    → user_id (Clerk), name, age, gender, state, area,
                   caste_category*, annual_income*, has_disability*,
                   occupation, is_student, goals (JSON),
                   profile_strength (0-100)
                   (* = sensitive, never returned in API response)

conversations    → id, user_id, created_at
messages         → id, conversation_id, role, content, created_at

notifications    → id, user_id, scheme_id, message, type,
                   is_read, is_cancelled, created_at
```

---

## Key API Endpoints

```
POST  /api/chat               ← main endpoint, runs agent loop
GET   /api/profile            ← returns {non_sensitive, tracker}
PATCH /api/profile            ← update profile fields
GET   /api/profile/tracker    ← booleans only {age:true, income:false...}
GET   /api/schemes            ← list with filters
GET   /api/schemes/{id}       ← full scheme detail
GET   /api/notifications      ← user's notifications
PATCH /api/notifications/{id}/read
GET   /health                 ← {status, schemes_count, last_sync}
```

---

## Critical Design Rules
> These are non-negotiable. Every AI reading this must follow them.

1. **Sensitive fields** (caste_category, annual_income, has_disability, bpl_card,
   is_pregnant) are NEVER returned in any API response. Only their boolean
   presence appears in the profile_tracker object.

2. **profile_tracker** is a dict of `{field_name: bool}` — true means the value
   IS stored in DB, false means not collected yet. Frontend stores this in
   localStorage. It never contains actual values.

3. **ChromaDB collection name** = "india_schemes" (single shared collection,
   all users search the same scheme pool).

4. **Scheme expiry** = soft delete in SQLite (status="inactive") + hard delete
   vectors from ChromaDB. Both must happen together.

5. **Chroma metadata** for every embedded scheme must include `scheme_id`, so
   expiry jobs can safely delete vectors with `where={"scheme_id": scheme.id}`.

6. **All API calls** from frontend go through `frontend/lib/api.ts` only.
   Never write fetch() directly in components.

7. **Auth** on every backend endpoint uses `Depends(get_current_user)` which
   verifies Clerk JWT and returns user_id string.

8. **No Aadhaar, PAN, bank details, or exact address** are ever stored.
   Enforce this in the Pydantic models.

9. **Clerk route protection** in the frontend lives in `frontend/proxy.ts`.
   `clerkMiddleware()` leaves routes public by default, so use
   `createRouteMatcher()` and only call `auth.protect()` for the intended
   protected routes.

---

## Code Style & Constraints

- Always use pnpm for frontend package management, never npm or yarn
- Git: create feature branch before starting each new feature
- Git: commit after every completed file using conventional commits
  format: type(scope): description
  types: feat, fix, chore, docs, refactor, test
- Git: never commit .env, chroma_db/, metadata.db, repomix-output.xml

---

## Environment Variables

### backend/.env
```
GOOGLE_API_KEY=
CLERK_SECRET_KEY=
ADMIN_TOKEN=
RESEND_API_KEY=          # placeholder for v2 email notifications
```

### frontend/.env.local
```
NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=
CLERK_SECRET_KEY=
NEXT_PUBLIC_CLERK_SIGN_IN_URL=/sign-in
NEXT_PUBLIC_CLERK_SIGN_UP_URL=/sign-up
NEXT_PUBLIC_CLERK_AFTER_SIGN_IN_URL=/chat
NEXT_PUBLIC_CLERK_AFTER_SIGN_UP_URL=/chat
NEXT_PUBLIC_API_URL=http://localhost:8000
```

Note: keep `NEXT_PUBLIC_CLERK_SIGN_IN_URL=/sign-in` explicitly set. There is a
known Clerk + Next.js 16 `proxy.ts` issue in monorepo/workspace setups where
`auth.protect()` can redirect back to the current page if the sign-in URL is
not available in the proxy runtime environment.

---

## Active Task Log
> AI: Update this section after every work session before the user switches IDE.
> Check off completed items with [x]. Add new items discovered during work.

### Foundation
- [ ] Create root folder structure (yojna-saathi/)
- [ ] Create CLAUDE.md (this file)
- [ ] Create .cursorrules and .windsurfrules
- [ ] Create repomix.config.json
- [ ] Create ruff.toml
- [ ] Create biome.json

### Backend — Setup
- [ ] Initialize FastAPI project in backend/
- [ ] Create requirements.txt with all dependencies
- [ ] Create backend/.env and backend/.env.example
- [ ] Set up config.py with pydantic-settings
- [ ] Set up database.py with SQLAlchemy engine
- [ ] Create all models in models.py
- [ ] Set up Alembic for migrations (alembic init alembic/)
- [ ] Run first migration: alembic revision --autogenerate -m "initial"
- [ ] Create main.py with CORS and router registration
- [ ] Test: uvicorn main:app --reload → /docs loads

### Backend — Auth
- [ ] Create middleware/auth.py (Clerk JWT verification)
- [ ] Test: hit a protected route without token → 401

### Backend — RAG Data Pipeline
- [ ] Install HuggingFace datasets library
- [ ] Download and explore shrijayan/gov_myscheme dataset
- [ ] Write ingest_schemes.py (load → tag → embed → ChromaDB + SQLite)
- [ ] Test: run on 50 schemes first
- [ ] Verify ChromaDB search: query "woman farmer Karnataka SC" → relevant schemes
- [ ] Run full ingestion (all 723 schemes)

### Backend — Agent
- [ ] Create agent/profile_extractor.py (Gemini → JSON)
- [ ] Test: pass a message → verify valid JSON returned
- [ ] Create agent/sufficiency_checker.py (pure Python logic)
- [ ] Test: various profile states → correct true/false
- [ ] Create agent/question_generator.py
- [ ] Create agent/update_suggester.py
- [ ] Create agent/conversation.py (main loop)
- [ ] Test: full conversation flow in Python (no API yet)

### Backend — Routers
- [ ] Create routers/chat.py (POST /api/chat)
- [ ] Create routers/profile.py (GET/PATCH/DELETE)
- [ ] Create routers/schemes.py (GET list + detail)
- [ ] Create routers/notifications.py
- [ ] Create routers/admin.py
- [ ] Test ALL endpoints via /docs UI

### Backend — Sync System
- [ ] Create scripts/sync_schemes.py (sitemap diff + expiry)
- [ ] Test: run sync → verify new schemes detected
- [ ] Test: expire a scheme → verify removed from ChromaDB
- [ ] Create notifications/matcher.py (SQL-based bulk eligibility)
- [ ] Test: add dummy scheme → verify notifications created
- [ ] Create .github/workflows/sync_schemes.yml
- [ ] Use current GitHub Actions majors in the workflow: `actions/checkout@v7`
      and `actions/setup-python@v6` (fallback only if runner compatibility
      forces it)

### Frontend — Setup
- [ ] pnpm create next-app@latest frontend (TypeScript, Tailwind, App Router)
- [ ] Install Clerk: pnpm add @clerk/nextjs
- [ ] Install shadcn/ui: pnpm dlx shadcn@latest init
- [ ] During shadcn init, choose the Next.js template and the default Radix-based primitives
- [ ] Install Vercel AI SDK: pnpm add ai
- [ ] Set up frontend/.env.local
- [ ] Create proxy.ts (Clerk route protection with createRouteMatcher)
- [ ] In `proxy.ts`, explicitly use `createRouteMatcher(['/chat(.*)', '/profile(.*)', '/notifications(.*)'])`
      and call `await auth.protect()` only for those routes
- [ ] Test: /chat redirects to /sign-in when not logged in

### Frontend — Pages
- [ ] Landing page (app/page.tsx) — hero + "Find My Schemes" CTA
- [ ] Sign-in page (Clerk pre-built)
- [ ] Sign-up page (Clerk pre-built)
- [ ] Chat page (app/chat/page.tsx) — MAIN EXPERIENCE
- [ ] Profile page (app/profile/page.tsx)
- [ ] Notifications page (app/notifications/page.tsx)
- [ ] Scheme detail page (app/scheme/[id]/page.tsx)

### Frontend — Components
- [ ] ChatWindow.tsx
- [ ] ChatInput.tsx
- [ ] SchemeCard.tsx
- [ ] ProfileUpdatePrompt.tsx (inline save suggestion)
- [ ] ProfileStrengthBar.tsx
- [ ] NotificationBadge.tsx
- [ ] ProfileEditor.tsx (edit individual fields)

### Frontend — API Layer
- [ ] Create lib/api.ts with all fetch wrappers
- [ ] Create lib/types.ts with all TypeScript interfaces
- [ ] Create lib/profile-tracker.ts (localStorage helpers)

### End-to-End Testing
- [ ] Full flow: sign up → chat → AI asks questions → profile saved
- [ ] Full flow: return visit → AI recognises profile → shows schemes directly
- [ ] Full flow: new scheme sync → notification created → user sees badge
- [ ] Full flow: scheme expires → removed from search + notification cancelled

### Deployment
- [ ] Deploy frontend to Vercel
- [ ] Deploy backend to Railway (with persistent volume for chroma_db/)
- [ ] Set all env vars in Vercel + Railway dashboards
- [ ] Test production URL end-to-end
- [ ] Enable GitHub Actions sync workflow (prefer `actions/checkout@v6`
      and `actions/setup-python@v6`)

---

## Current Next Step
> AI: Update this to ONE clear sentence before the user switches IDE.

**NOT STARTED YET — Begin with: Create root folder structure and all config files
(CLAUDE.md is done, now create .cursorrules, .windsurfrules, repomix.config.json,
ruff.toml, biome.json), then initialize the backend FastAPI project.**

---

## Handoff Protocol
> Run this EVERY TIME before switching IDE or ending a session.

```
Step 1: In terminal, run:
  repomix

Step 2: Tell the current AI:
  "Update the Active Task Log in CLAUDE.md — check off everything we completed,
   add any new tasks discovered, and update Current Next Step to one sentence."

Step 3: Open next IDE, attach repomix-output.xml, type:
  "Read CLAUDE.md first. Then check the repo layout in repomix-output.xml.
   Pick up exactly from Current Next Step. Don't recreate files that already exist."
```

---

## Common Mistakes to Avoid
> AI: Read this before writing any code.

- DO NOT create a new file if it already exists — check repomix-output.xml first
- DO NOT put fetch() calls directly in React components — use lib/api.ts
- DO NOT return sensitive fields (caste, income, disability) in API responses
- DO NOT use `requests` library in Python — use `httpx` (async)
- DO NOT put all backend code in main.py — use the routers/ structure
- DO NOT skip the Clerk JWT check on any route that touches user data
- DO NOT assume `clerkMiddleware()` protects routes by itself — it does not
- DO NOT use `middleware.ts` for this Next.js 16 Clerk setup — use `proxy.ts`
- DO NOT store Aadhaar, PAN, or bank details anywhere in the codebase
- DO NOT embed the full scheme text — embed only eligibility + benefits sections
- DO NOT use a per-user ChromaDB collection — all schemes share "india_schemes"

---

## Scheme Categories (for reference)
```
Agriculture, Rural & Environment
Banking, Financial Services & Insurance
Business & Entrepreneurship
Education & Learning
Health & Wellness
Housing & Shelter
Science, IT & Communications
Skills & Employment
Social Welfare & Empowerment
Transport & Infrastructure
Women and Child
```

## Goal → Category Map
```
buy_ev          → Transport & Infrastructure
buy_home        → Housing & Shelter
start_business  → Business & Entrepreneurship
get_scholarship → Education & Learning
get_insurance   → Banking, Financial Services & Insurance
farm_support    → Agriculture, Rural & Environment
labour_welfare  → Social Welfare & Empowerment
health_coverage → Health & Wellness
```
