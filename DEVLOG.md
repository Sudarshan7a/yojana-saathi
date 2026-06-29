# Dev Log

## Session 1 — 2026-06-28 — Cursor
### Completed
- ✅ Created CLAUDE.md with full architecture, task log, design rules
- ✅ Created .cursorrules and .windsurfrules
- ✅ Created repomix.config.json, ruff.toml, biome.json
- ✅ Added pnpm rule to all three files
- ✅ Added git branch + conventional commit rules to all three files
- ✅ Installed codegraph globally (npm install -g @optave/codegraph v3.15.0)

### In Progress
- 🔴 Nothing half-done — clean stopping point

### Bugs / Notes
- codegraph not on PATH yet in Cursor shell — needs fresh terminal or IDE restart
- codegraph install used npm (correct — global tool, not project dependency)
- pnpm rule applies to frontend/ project packages only

### Next Session Starts With
Create feature branch and commit config files, then initialize Next.js:
1. git checkout -b chore/project-setup
2. git add . → git commit -m "chore(config): add CLAUDE.md, linting config, git workflow rules"
3. cd frontend → pnpm create next-app@latest .
   Answer: TypeScript=Yes, ESLint=No, Tailwind=Yes, src/=No, AppRouter=Yes, alias=No
4. cd .. → codegraph build → codegraph watch

---

## Session 2 — 2026-06-29 — Windsurf
### Completed
- ✅ Created feature branch chore/project-setup
- ✅ Committed config files (CLAUDE.md, linting configs, git workflow rules)
- ✅ Initialized Next.js 14 in frontend/ (TypeScript, Tailwind, App Router, no ESLint)
- ✅ Added CodeGraph integration rules to .cursorrules and .windsurfrules
- ✅ Installed Clerk CLI globally and initialized Clerk authentication
- ✅ Installed @clerk/nextjs with proxy.ts, sign-in/sign-up pages, and ClerkProvider
- ✅ Fixed proxy.ts matcher to include '/__clerk/:path*' for Clerk auto-proxy
- ✅ Created backend/config.py with pydantic-settings (RAG constants, sync settings, etc.)
- ✅ Created backend/database.py with SQLAlchemy engine and session management
- ✅ Created backend/models.py with all 5 models (Scheme, UserProfile, Conversation, Message, Notification)
- ✅ Created backend/main.py with FastAPI app, CORS, health check, and DB initialization
- ✅ Created backend/.env.example and backend/.env with real API keys
- ✅ Replaced PyJWT with official clerk-backend-api SDK in requirements.txt
- ✅ Set up Python 3.12 virtual environment in backend/
- ✅ Installed all backend dependencies from requirements.txt
- ✅ Backend server running successfully on http://127.0.0.1:8000
- ✅ Health check endpoint /health working with schemes_count
- ✅ API docs available at /docs

### In Progress
- 🔴 Nothing half-done — clean stopping point

### Bugs / Notes
- Python is accessed via `py` command on Windows, not `python`
- Clerk authentication fully integrated in frontend with proper middleware
- All sensitive fields in UserProfile model marked and documented
- Database tables auto-created on startup via SQLAlchemy Base.metadata.create_all()

### Next Session Starts With
Create Clerk JWT verification middleware for backend:
1. Create backend/middleware/auth.py with Clerk JWT verification using clerk-backend-api
2. Create dependency function get_current_user() for protected routes
3. Test auth middleware with a protected endpoint

---

## Session 3 - 2026-06-29 - Codex
### Completed
- All backend routers done: schemes, profile, notifications, and admin
- Schemes router exposes public list, detail, categories, and states endpoints
- Profile router exposes authenticated get, update, tracker, and delete endpoints
- Notifications router exposes authenticated list, read, read-all, and unread-count endpoints
- Admin router exposes token-protected manual sync trigger endpoint

### In Progress
- Nothing half-done - clean stopping point

### Next Session Starts With
Agent files:
1. Start with `agent/profile_extractor.py`

---

## Session 4 - 2026-06-29 - Codex
### Completed
- Added RAG prompt templates for profile extraction, question generation, and result generation
- Added ChromaDB retriever with Google embeddings and semantic scheme search
- Added agent package with profile extractor, sufficiency checker, question generator, update suggester, and conversation manager
- Added chat router and wired the full conversation pipeline into FastAPI
- Added HuggingFace ingestion script for scheme metadata + vector storage
- Restarted backend and verified `/docs` loads with no import errors
- Replaced deprecated `langchain-community` embeddings with `langchain-huggingface`
- Switched RAG pipeline to local `sentence-transformers` embeddings
- Rebuilt and validated ChromaDB with 3397 embedded schemes and searchable semantic batches

### In Progress
- Nothing half-done - clean stopping point

### Bugs / Notes
- `multiprocess.resource_tracker` still emits a shutdown-time warning after ingestion, but the full 68-batch embed completes successfully
- Uvicorn startup was clean after wiring the AI brain files

### Next Session Starts With
1. Merge backend changes to `main`
2. Start frontend chat UI and connect it to the live backend
