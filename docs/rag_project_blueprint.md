# StudyVault — Pre-Coding Blueprint

> **Product:** Multi-user AI study platform — students upload their own PDFs and chat with them
> **Frontend:** Next.js 14 (App Router) + Tailwind CSS
> **Backend:** FastAPI (Python)
> **Auth:** Clerk
> **Vector DB:** ChromaDB (per-user namespaced collections)
> **LLM:** Google Gemini 1.5 Flash
> **Metadata DB:** SQLite + SQLAlchemy
> **File Storage:** Local (`/uploads/`) → upgrade path to AWS S3
> **Author:** Sudarshan | Handpick AI Engineering Intern Interview Project

---

## Table of Contents

1. [Product Vision](#1-product-vision)
2. [Tech Stack Decisions & Why](#2-tech-stack-decisions--why)
3. [System Architecture](#3-system-architecture)
4. [API Design (FastAPI endpoints)](#4-api-design)
5. [Database Design](#5-database-design)
6. [Project Folder Structure](#6-project-folder-structure)
7. [Frontend Architecture (Next.js)](#7-frontend-architecture-nextjs)
8. [Backend Architecture (FastAPI)](#8-backend-architecture-fastapi)
9. [RAG Pipeline Design](#9-rag-pipeline-design)
10. [Authentication Flow](#10-authentication-flow)
11. [Data Flow — Upload + Query](#11-data-flow)
12. [Prompt Engineering Design](#12-prompt-engineering-design)
13. [Error Handling Strategy](#13-error-handling-strategy)
14. [Environment & Configuration](#14-environment--configuration)
15. [Testing Plan](#15-testing-plan)
16. [Known Limitations & Trade-offs](#16-known-limitations--trade-offs)
17. [Build Order (Day-by-Day)](#17-build-order)
18. [Interview Answer Cheatsheet](#18-interview-answer-cheatsheet)

---

## 1. Product Vision

### What You're Building
A multi-user SaaS-style study platform where:
- Each student creates an account
- Uploads their own PDF notes/textbooks
- Asks questions — gets answers sourced from their own documents
- No student can see another student's documents

### Core User Stories
```
As a student, I want to upload my lecture notes as PDFs
  so that I can chat with them instead of re-reading everything.

As a student, I want my documents to be private to me
  so that other students can't access my notes.

As a student, I want to see which page an answer came from
  so that I can verify and read more context.
```

### What It Deliberately Does NOT Do
- Does not search the internet
- Does not use Gemini's general knowledge (only your uploaded docs)
- Does not share documents between users
- Does not support image-heavy or scanned PDFs (text-based PDFs only, v1)
- Does not have real-time collaboration (v1)

Knowing your scope boundaries = you understand product thinking. Say this in your interview.

---

## 2. Tech Stack Decisions & Why

### Frontend: Next.js 14 (App Router) + Tailwind CSS
- **Why Next.js over plain React:** Built-in routing, server components, API routes if needed, easy deployment on Vercel. Industry standard for full-stack React apps.
- **Why App Router:** Newer, supports React Server Components, better data fetching patterns, what companies are adopting now.
- **Why Tailwind:** Fastest way to build clean UI without writing custom CSS files. Utility-first = no class naming headaches.
- **Alternative considered:** Vite + React (no SSR, no routing out of the box), SvelteKit (less industry adoption for interviews).

### Backend: FastAPI (Python)
- **Why FastAPI over Flask:** Automatic OpenAPI docs (`/docs`), built-in async support, type hints via Pydantic, 3× faster than Flask for async workloads. It's what ML teams actually use.
- **Why Python backend:** All your RAG code (LangChain, ChromaDB, Gemini) is Python. Keeping the backend in Python means zero language-switching friction.
- **Why not Next.js API routes for the backend:** You can't run LangChain or ChromaDB in a JS serverless function. Python backend is the only real choice here.
- **Alternative considered:** Django (too heavy, too opinionated for an API), Flask (fine but FastAPI is strictly better for this use case).

### Auth: Clerk
- **Why Clerk:** Free tier handles 10,000 monthly active users. Pre-built React components (login modal, user button). Webhook support. Zero backend auth code needed — Clerk handles JWTs, session management, password hashing, OAuth (Google login) all for you.
- **Why not build auth yourself:** Auth is a security-critical system. Freshers should not build auth from scratch for a portfolio project. Using Clerk shows you know when to use existing tools.
- **Alternative considered:** NextAuth.js (good, more config needed), Supabase Auth (tied to Supabase DB), Firebase Auth (Google lock-in).

### Vector Database: ChromaDB
- **Why ChromaDB:** Runs locally, zero signup, persists to disk, supports collection namespacing (one collection per user).
- **Why not Pinecone:** Pinecone is cloud-only, paid after free tier limits, and overkill for a student project demo.
- **Why not FAISS:** In-memory only — doesn't persist when server restarts. Bad for multi-user.
- **Alternative considered:** Weaviate (self-hosted, heavier), Qdrant (good but extra setup).

### Metadata DB: SQLite + SQLAlchemy
- **Why SQLite:** Perfect for a single-server app. No separate database server to run. Data stored in one file. SQLAlchemy ORM makes it easy to swap to PostgreSQL later (just change connection string).
- **What it stores:** User document metadata (filename, upload date, page count, status) — NOT the actual vectors (those live in ChromaDB).
- **Alternative considered:** PostgreSQL (correct choice for production, overkill for demo), MongoDB (no joins, bad for relational metadata).

### LLM: Google Gemini 1.5 Flash
- **Why Flash over Pro:** Pro is 10× more expensive. Flash is fast, accurate enough for RAG use cases, and has a generous free tier (1M tokens/day).
- **Why Gemini over OpenAI:** No credit card required for free tier. Better for a student project.
- **Alternative considered:** GPT-4o (expensive), Llama 3 local (needs GPU), Mistral (good alternative, similar setup).

---

## 3. System Architecture

```
┌──────────────────────────────────────────────────────────────────────┐
│                        BROWSER (Student)                             │
│                    Next.js 14 — App Router                           │
│                                                                      │
│   /              → Landing page                                      │
│   /sign-in       → Clerk auth                                        │
│   /dashboard     → Upload PDFs, see document list                   │
│   /chat/[docId]  → Chat with a specific document                    │
└────────────────────────────┬─────────────────────────────────────────┘
                             │  HTTP (REST API calls)
                             │  Authorization: Bearer <clerk_jwt>
                             ▼
┌──────────────────────────────────────────────────────────────────────┐
│                      FastAPI Backend (Python)                        │
│                    Running on port 8000                              │
│                                                                      │
│   POST /api/documents/upload    → ingest PDF                        │
│   GET  /api/documents           → list user's docs                  │
│   DELETE /api/documents/{id}    → delete a doc                      │
│   POST /api/chat                → ask a question                    │
│   GET  /api/documents/{id}/status → check ingestion progress        │
└────────┬──────────────────────┬──────────────────────────────────────┘
         │                      │
         ▼                      ▼
┌─────────────────┐   ┌──────────────────────────────────────────────┐
│  SQLite DB      │   │           RAG PIPELINE                       │
│  (metadata.db)  │   │                                              │
│                 │   │  Ingestor:                                   │
│  users table    │   │    PyPDFLoader → TextSplitter → Embeddings   │
│  documents      │   │    → ChromaDB (collection: user_{user_id})   │
│    table        │   │                                              │
│                 │   │  Retriever:                                  │
└─────────────────┘   │    Embed query → ChromaDB similarity search  │
                      │    → Prompt builder → Gemini → Answer        │
                      └──────────────┬───────────────────────────────┘
                                     │
                                     ▼
                      ┌──────────────────────────────┐
                      │  ChromaDB (./chroma_db/)     │
                      │                              │
                      │  Collection: user_abc123     │
                      │  Collection: user_def456     │
                      │  (one per student)           │
                      └──────────────────────────────┘
                                     │
                                     ▼
                      ┌──────────────────────────────┐
                      │  Google Gemini 1.5 Flash API │
                      │  (external — paid per token) │
                      └──────────────────────────────┘
```

### Key Architectural Decisions to Explain in Interview

**1. Why separate frontend and backend?**
Separation of concerns. Frontend only handles UI state and API calls. Backend handles all ML logic, file storage, and database. This lets you scale them independently and deploy them separately (Vercel for frontend, Railway/Render for backend).

**2. Why per-user ChromaDB collections?**
Data isolation. If all users' chunks were in one collection, user A could theoretically retrieve chunks from user B's documents. Namespacing by `user_{clerk_user_id}` guarantees privacy at the vector search layer.

**3. Why SQLite alongside ChromaDB?**
ChromaDB stores vectors — it's not designed to store metadata like "what documents does this user have?" or "what's the status of this upload?" SQLite is a lightweight relational DB for that structured metadata. Two databases for two different types of data.

---

## 4. API Design

FastAPI auto-generates interactive docs at `http://localhost:8000/docs`. This is a huge interview flex — live, clickable API documentation with zero extra work.

### Endpoint Specifications

```
POST   /api/documents/upload
  Auth: Required (Clerk JWT)
  Body: multipart/form-data { file: PDF }
  Response: { document_id, filename, status: "processing" }
  Side effect: triggers background ingestion task

GET    /api/documents
  Auth: Required
  Response: [{ id, filename, page_count, status, created_at }, ...]
  Note: Only returns documents for the authenticated user

GET    /api/documents/{document_id}/status
  Auth: Required
  Response: { status: "processing" | "ready" | "failed", chunk_count }

DELETE /api/documents/{document_id}
  Auth: Required
  Response: { message: "deleted" }
  Side effect: removes from SQLite + deletes ChromaDB embeddings

POST   /api/chat
  Auth: Required
  Body: { document_id: str, question: str }
  Response: {
    answer: str,
    sources: [{ page: int, preview: str }],
    tokens_used: int
  }
```

### Request/Response Example

```json
// POST /api/chat
// Request:
{
  "document_id": "doc_abc123",
  "question": "What is gradient descent?"
}

// Response:
{
  "answer": "Gradient descent is an optimization algorithm that minimizes a loss function by iteratively moving in the direction of steepest descent...",
  "sources": [
    { "page": 3, "preview": "Gradient descent updates weights by subtracting the gradient..." },
    { "page": 7, "preview": "The learning rate controls the step size in gradient descent..." }
  ],
  "tokens_used": 1240
}
```

### HTTP Status Codes You Must Handle

```
200 OK              → success
201 Created         → document uploaded successfully
400 Bad Request     → wrong file type, empty question, etc.
401 Unauthorized    → missing or invalid Clerk JWT
403 Forbidden       → user trying to access another user's document
404 Not Found       → document_id doesn't exist
422 Unprocessable   → FastAPI validation error (wrong body shape)
500 Internal Error  → something broke in the RAG pipeline
```

---

## 5. Database Design

### SQLite Schema (metadata.db)

```sql
-- Documents table
-- Tracks every PDF a user has uploaded
CREATE TABLE documents (
    id          TEXT PRIMARY KEY,     -- UUID, e.g. "doc_abc123"
    user_id     TEXT NOT NULL,        -- Clerk user ID, e.g. "user_2abc..."
    filename    TEXT NOT NULL,        -- Original filename "notes.pdf"
    file_path   TEXT NOT NULL,        -- Where it's stored on disk
    page_count  INTEGER,              -- Populated after ingestion
    chunk_count INTEGER,              -- How many chunks were created
    status      TEXT DEFAULT 'processing',  -- processing | ready | failed
    error_msg   TEXT,                 -- if status=failed, why
    created_at  DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at  DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Index: fast lookup of all documents by a user
CREATE INDEX idx_documents_user_id ON documents(user_id);
```

```python
# SQLAlchemy model (backend/models.py)
from sqlalchemy import Column, String, Integer, DateTime, Text
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime
import uuid

Base = declarative_base()

class Document(Base):
    __tablename__ = "documents"

    id         = Column(String, primary_key=True, default=lambda: f"doc_{uuid.uuid4().hex[:8]}")
    user_id    = Column(String, nullable=False, index=True)
    filename   = Column(String, nullable=False)
    file_path  = Column(String, nullable=False)
    page_count = Column(Integer, nullable=True)
    chunk_count= Column(Integer, nullable=True)
    status     = Column(String, default="processing")
    error_msg  = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
```

### ChromaDB Collections (per-user)

```
ChromaDB collection name: "user_{clerk_user_id}_{document_id}"
Example: "user_2abc123_doc_def456"

Why include document_id in collection name?
→ One user might upload 5 PDFs. When they chat with "ML notes.pdf",
  you only want to search that specific document's chunks,
  not all their other PDFs mixed together.

Each document gets its own ChromaDB collection.
```

### Why Two Databases?

```
SQLite answers: "What documents does user X have? What's their status?"
ChromaDB answers: "Which chunks of document Y are most relevant to this question?"

These are fundamentally different questions requiring different data structures.
SQL = structured relational data with joins, filters, ordering.
ChromaDB = unstructured vector data with similarity search.
```

---

## 6. Project Folder Structure

```
studyvault/
│
├── frontend/                          # Next.js 14 app
│   ├── app/
│   │   ├── layout.tsx                 # Root layout — ClerkProvider goes here
│   │   ├── page.tsx                   # Landing page (/)
│   │   ├── sign-in/[[...sign-in]]/
│   │   │   └── page.tsx               # Clerk sign-in page
│   │   ├── sign-up/[[...sign-up]]/
│   │   │   └── page.tsx               # Clerk sign-up page
│   │   └── dashboard/
│   │       ├── layout.tsx             # Protected layout (redirects if not authed)
│   │       ├── page.tsx               # Document list + upload
│   │       └── chat/[documentId]/
│   │           └── page.tsx           # Chat UI for a specific document
│   │
│   ├── components/
│   │   ├── DocumentUpload.tsx         # PDF upload dropzone
│   │   ├── DocumentCard.tsx           # Card showing one document
│   │   ├── ChatWindow.tsx             # Chat message list
│   │   ├── ChatInput.tsx              # Question input + send button
│   │   ├── SourceCard.tsx             # Shows page reference for an answer
│   │   └── LoadingSpinner.tsx         # Reusable loading state
│   │
│   ├── lib/
│   │   └── api.ts                     # API call functions (fetch wrappers)
│   │
│   ├── middleware.ts                  # Clerk auth middleware — protects /dashboard
│   ├── .env.local                     # NEXT_PUBLIC_CLERK_*, NEXT_PUBLIC_API_URL
│   ├── next.config.js
│   ├── tailwind.config.js
│   └── package.json
│
├── backend/                           # FastAPI Python app
│   ├── main.py                        # FastAPI app entry point, CORS config
│   ├── config.py                      # All env vars + constants
│   ├── models.py                      # SQLAlchemy DB models
│   ├── database.py                    # DB connection + session management
│   │
│   ├── routers/
│   │   ├── documents.py               # /api/documents routes
│   │   └── chat.py                    # /api/chat route
│   │
│   ├── rag/
│   │   ├── ingestor.py                # PDF → chunks → embeddings → ChromaDB
│   │   ├── retriever.py               # query → vector search → Gemini → answer
│   │   └── prompt_template.py         # Prompt string definition
│   │
│   ├── middleware/
│   │   └── auth.py                    # Clerk JWT verification for FastAPI
│   │
│   ├── uploads/                       # PDF files stored here (gitignored)
│   ├── chroma_db/                     # ChromaDB vector files (gitignored)
│   ├── metadata.db                    # SQLite database (gitignored)
│   │
│   ├── tests/
│   │   ├── test_ingestor.py
│   │   ├── test_retriever.py
│   │   └── test_routes.py
│   │
│   ├── requirements.txt
│   └── .env                           # API keys, DB path, etc.
│
└── README.md                          # Setup instructions for both services
```

---

## 7. Frontend Architecture (Next.js)

### Routing Structure

```
/                    Public — landing page, sign in CTA
/sign-in             Clerk's pre-built sign-in UI
/sign-up             Clerk's pre-built sign-up UI
/dashboard           Protected — document list + upload button
/dashboard/chat/[documentId]  Protected — chat with one specific doc
```

### Auth Middleware (`frontend/middleware.ts`)

```typescript
// This file tells Next.js: protect everything under /dashboard
// If user isn't logged in, redirect to /sign-in automatically
import { clerkMiddleware, createRouteMatcher } from '@clerk/nextjs/server'

const isProtectedRoute = createRouteMatcher(['/dashboard(.*)'])

export default clerkMiddleware((auth, req) => {
  if (isProtectedRoute(req)) auth().protect()
})

export const config = {
  matcher: ['/((?!_next|.*\\..*).*)'],
}
```

### API Call Layer (`frontend/lib/api.ts`)

```typescript
// All backend calls go through this file.
// Never write fetch() directly in your components — always call these functions.
// This makes it trivial to change the base URL or add headers in one place.

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

async function fetchWithAuth(url: string, options: RequestInit = {}) {
  // Clerk provides the JWT token
  const { getToken } = await import('@clerk/nextjs/server')
  // On client: use useAuth() hook instead
  
  return fetch(`${API_BASE}${url}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      // Authorization header — FastAPI verifies this
      ...options.headers,
    },
  })
}

export async function uploadDocument(file: File, token: string) {
  const formData = new FormData()
  formData.append('file', file)

  const res = await fetch(`${API_BASE}/api/documents/upload`, {
    method: 'POST',
    headers: { Authorization: `Bearer ${token}` },
    body: formData,  // No Content-Type header for multipart — browser sets it
  })

  if (!res.ok) throw new Error(`Upload failed: ${res.statusText}`)
  return res.json()
}

export async function getDocuments(token: string) {
  const res = await fetch(`${API_BASE}/api/documents`, {
    headers: { Authorization: `Bearer ${token}` },
  })
  if (!res.ok) throw new Error('Failed to fetch documents')
  return res.json()
}

export async function askQuestion(documentId: string, question: string, token: string) {
  const res = await fetch(`${API_BASE}/api/chat`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify({ document_id: documentId, question }),
  })
  if (!res.ok) throw new Error('Chat request failed')
  return res.json()
}

export async function deleteDocument(documentId: string, token: string) {
  const res = await fetch(`${API_BASE}/api/documents/${documentId}`, {
    method: 'DELETE',
    headers: { Authorization: `Bearer ${token}` },
  })
  if (!res.ok) throw new Error('Delete failed')
  return res.json()
}
```

### Key React Patterns to Use

```typescript
// Dashboard page — data fetching pattern
'use client'
import { useAuth } from '@clerk/nextjs'
import { useEffect, useState } from 'react'
import { getDocuments } from '@/lib/api'

export default function DashboardPage() {
  const { getToken } = useAuth()
  const [documents, setDocuments] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    async function loadDocs() {
      const token = await getToken()       // Get Clerk JWT
      const docs = await getDocuments(token)
      setDocuments(docs)
      setLoading(false)
    }
    loadDocs()
  }, [])

  // ...render
}
```

---

## 8. Backend Architecture (FastAPI)

### Entry Point (`backend/main.py`)

```python
# main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers import documents, chat
from database import engine
import models

# Create DB tables on startup
models.Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="StudyVault API",
    description="RAG-powered study assistant backend",
    version="1.0.0"
)

# CORS — allow your Next.js frontend to call this API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # In prod: your Vercel URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register route groups
app.include_router(documents.router, prefix="/api/documents", tags=["documents"])
app.include_router(chat.router, prefix="/api/chat", tags=["chat"])

@app.get("/health")
def health_check():
    return {"status": "ok"}
```

### Auth Middleware (`backend/middleware/auth.py`)

```python
# auth.py
# Verifies the Clerk JWT token on every protected request
# Clerk tokens are standard JWTs — we verify them using Clerk's JWKS endpoint

import httpx
from jose import jwt, JWTError
from fastapi import HTTPException, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from config import CLERK_PUBLISHABLE_KEY

security = HTTPBearer()

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Security(security)
) -> str:
    """
    FastAPI dependency. Use this in any route that requires auth.
    Returns the Clerk user_id (e.g. "user_2abc123...")
    
    Usage:
        @router.get("/documents")
        def list_docs(user_id: str = Depends(get_current_user)):
            ...
    """
    token = credentials.credentials

    try:
        # Fetch Clerk's public keys (cached after first fetch)
        jwks_url = f"https://api.clerk.com/v1/jwks"
        async with httpx.AsyncClient() as client:
            response = await client.get(jwks_url, headers={
                "Authorization": f"Bearer {CLERK_PUBLISHABLE_KEY}"
            })
        jwks = response.json()

        # Decode and verify the JWT
        payload = jwt.decode(token, jwks, algorithms=["RS256"])
        user_id = payload.get("sub")  # "sub" = subject = Clerk user ID

        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid token: no user ID")

        return user_id

    except JWTError as e:
        raise HTTPException(status_code=401, detail=f"Invalid token: {str(e)}")
```

### Documents Router (`backend/routers/documents.py`)

```python
# documents.py
import os
import uuid
import aiofiles
from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from database import get_db
from models import Document
from middleware.auth import get_current_user
from rag.ingestor import ingest_pdf
from config import UPLOAD_DIR

router = APIRouter()

@router.post("/upload", status_code=201)
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user)  # Auth check
):
    # Validate file type
    if not file.filename.endswith(".pdf"):
        raise HTTPException(400, "Only PDF files are supported")

    # Validate file size (10MB max)
    content = await file.read()
    if len(content) > 10 * 1024 * 1024:
        raise HTTPException(400, "File size must be under 10MB")

    # Save to disk
    doc_id = f"doc_{uuid.uuid4().hex[:8]}"
    save_path = os.path.join(UPLOAD_DIR, f"{doc_id}.pdf")
    async with aiofiles.open(save_path, 'wb') as f:
        await f.write(content)

    # Create DB record
    doc = Document(
        id=doc_id,
        user_id=user_id,
        filename=file.filename,
        file_path=save_path,
        status="processing"
    )
    db.add(doc)
    db.commit()

    # Run ingestion in background (don't make user wait)
    background_tasks.add_task(run_ingestion, doc_id, save_path, user_id, db)

    return {"document_id": doc_id, "filename": file.filename, "status": "processing"}


async def run_ingestion(doc_id: str, file_path: str, user_id: str, db: Session):
    """Background task — runs after the API has already responded to the user"""
    doc = db.query(Document).filter(Document.id == doc_id).first()
    try:
        result = ingest_pdf(file_path, user_id, doc_id)
        doc.status = "ready"
        doc.page_count = result["page_count"]
        doc.chunk_count = result["chunk_count"]
    except Exception as e:
        doc.status = "failed"
        doc.error_msg = str(e)
    finally:
        db.commit()


@router.get("/")
def list_documents(
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user)
):
    """Returns only THIS user's documents"""
    docs = db.query(Document).filter(Document.user_id == user_id).all()
    return docs


@router.delete("/{document_id}")
def delete_document(
    document_id: str,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user)
):
    doc = db.query(Document).filter(Document.id == document_id).first()

    if not doc:
        raise HTTPException(404, "Document not found")

    # IMPORTANT: Check ownership — user can only delete their OWN documents
    if doc.user_id != user_id:
        raise HTTPException(403, "You don't have permission to delete this document")

    # TODO: Also delete from ChromaDB
    db.delete(doc)
    db.commit()
    return {"message": "Document deleted"}
```

### Chat Router (`backend/routers/chat.py`)

```python
# chat.py
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from database import get_db
from models import Document
from middleware.auth import get_current_user
from rag.retriever import load_vectorstore, build_qa_chain, answer_question

router = APIRouter()

class ChatRequest(BaseModel):
    document_id: str
    question: str

@router.post("/")
async def chat(
    request: ChatRequest,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user)
):
    # Validate question
    if not request.question.strip():
        raise HTTPException(400, "Question cannot be empty")

    # Fetch document + verify ownership
    doc = db.query(Document).filter(Document.id == request.document_id).first()
    if not doc:
        raise HTTPException(404, "Document not found")
    if doc.user_id != user_id:
        raise HTTPException(403, "Access denied")
    if doc.status != "ready":
        raise HTTPException(400, f"Document is not ready yet (status: {doc.status})")

    # Run RAG pipeline
    try:
        collection_name = f"user_{user_id}_{request.document_id}"
        vectorstore = load_vectorstore(collection_name)
        qa_chain = build_qa_chain(vectorstore)
        result = answer_question(request.question, qa_chain)
        return result
    except Exception as e:
        raise HTTPException(500, f"RAG pipeline error: {str(e)}")
```

---

## 9. RAG Pipeline Design

### Ingestion Pipeline (`backend/rag/ingestor.py`)

```python
# ingestor.py
from langchain_community.document_loaders import PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_community.vectorstores import Chroma
from config import (
    GOOGLE_API_KEY, CHUNK_SIZE, CHUNK_OVERLAP,
    EMBEDDING_MODEL, CHROMA_PERSIST_DIR
)

def ingest_pdf(pdf_path: str, user_id: str, document_id: str) -> dict:
    """
    Full ingestion pipeline for one PDF.

    Args:
        pdf_path:    path to the PDF on disk
        user_id:     Clerk user ID (for collection namespacing)
        document_id: our internal document ID

    Returns:
        { page_count: int, chunk_count: int }
    """
    # Step 1: Load PDF
    loader = PyPDFLoader(pdf_path)
    pages = loader.load()

    # Step 2: Split into chunks
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,          # 500 tokens per chunk
        chunk_overlap=CHUNK_OVERLAP,    # 50 token overlap between chunks
        separators=["\n\n", "\n", ".", " ", ""]
        # Tries to split on paragraph breaks first, then line breaks,
        # then sentence ends, then words — keeps semantic units intact
    )
    chunks = splitter.split_documents(pages)

    # Step 3: Embed + store in ChromaDB
    # Collection is named per-user + per-document for isolation
    collection_name = f"user_{user_id}_{document_id}"

    embeddings = GoogleGenerativeAIEmbeddings(
        model=EMBEDDING_MODEL,
        google_api_key=GOOGLE_API_KEY
    )

    Chroma.from_documents(
        documents=chunks,
        embedding=embeddings,
        persist_directory=CHROMA_PERSIST_DIR,
        collection_name=collection_name
    )

    return {
        "page_count": len(pages),
        "chunk_count": len(chunks)
    }
```

### Retrieval Pipeline (`backend/rag/retriever.py`)

```python
# retriever.py
from langchain_google_genai import GoogleGenerativeAIEmbeddings, ChatGoogleGenerativeAI
from langchain_community.vectorstores import Chroma
from langchain.chains import RetrievalQA
from rag.prompt_template import get_prompt
from config import GOOGLE_API_KEY, TOP_K, EMBEDDING_MODEL, LLM_MODEL, CHROMA_PERSIST_DIR


def load_vectorstore(collection_name: str):
    embeddings = GoogleGenerativeAIEmbeddings(
        model=EMBEDDING_MODEL,
        google_api_key=GOOGLE_API_KEY
    )
    return Chroma(
        persist_directory=CHROMA_PERSIST_DIR,
        embedding_function=embeddings,
        collection_name=collection_name
    )


def build_qa_chain(vectorstore):
    llm = ChatGoogleGenerativeAI(
        model=LLM_MODEL,
        google_api_key=GOOGLE_API_KEY,
        temperature=0.3,        # Low = more factual, less hallucination risk
        max_output_tokens=1024
    )

    retriever = vectorstore.as_retriever(
        search_type="similarity",
        search_kwargs={"k": TOP_K}   # Fetch top 5 most relevant chunks
    )

    return RetrievalQA.from_chain_type(
        llm=llm,
        chain_type="stuff",             # stuff = concatenate chunks into one prompt
        retriever=retriever,
        return_source_documents=True,
        chain_type_kwargs={"prompt": get_prompt()}
    )


def answer_question(question: str, qa_chain) -> dict:
    result = qa_chain({"query": question})

    sources = []
    for doc in result.get("source_documents", []):
        sources.append({
            "page": doc.metadata.get("page", "unknown"),
            "source": doc.metadata.get("source", "unknown"),
            "preview": doc.page_content[:120] + "..."
        })

    return {
        "answer": result["result"],
        "sources": sources
    }
```

---

## 10. Authentication Flow

```
SIGN UP / SIGN IN FLOW:

1. User visits /sign-in
2. Clerk renders pre-built sign-in form (email/password or Google OAuth)
3. User authenticates → Clerk issues a JWT token
4. Token stored in browser (Clerk manages this automatically)
5. User redirected to /dashboard

API CALL FLOW:

1. Frontend: const token = await getToken()  ← from useAuth() hook
2. Frontend: fetch('/api/...', { headers: { Authorization: `Bearer ${token}` }})
3. Backend: FastAPI extracts token from Authorization header
4. Backend: Verifies JWT signature using Clerk's public keys (JWKS)
5. Backend: Extracts user_id from JWT payload ("sub" claim)
6. Backend: Uses user_id to filter data — user only sees their own documents

WHAT NEVER HAPPENS:
- Passwords never touch your backend code
- Session management never touches your backend code
- You never store tokens in your database
- Clerk handles all of this
```

### Setting Up Clerk

```bash
# 1. Go to clerk.com → Create account → Create application
# 2. Choose "Email + Google" as sign-in methods
# 3. Copy your keys to .env files

# frontend/.env.local
NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=pk_test_...
CLERK_SECRET_KEY=sk_test_...
NEXT_PUBLIC_CLERK_SIGN_IN_URL=/sign-in
NEXT_PUBLIC_CLERK_SIGN_UP_URL=/sign-up
NEXT_PUBLIC_CLERK_AFTER_SIGN_IN_URL=/dashboard
NEXT_PUBLIC_CLERK_AFTER_SIGN_UP_URL=/dashboard
NEXT_PUBLIC_API_URL=http://localhost:8000

# backend/.env
CLERK_PUBLISHABLE_KEY=pk_test_...
GOOGLE_API_KEY=AIza...
```

---

## 11. Data Flow

### Upload Flow (step by step)

```
1. Student selects a PDF in the browser
2. Frontend calls uploadDocument(file, token) from lib/api.ts
3. FastAPI receives the file at POST /api/documents/upload
4. FastAPI middleware verifies Clerk JWT → extracts user_id
5. FastAPI saves PDF to uploads/doc_abc123.pdf
6. FastAPI creates Document row in SQLite with status="processing"
7. FastAPI responds immediately: { document_id, status: "processing" }
8. FastAPI runs ingestion as a background task (user doesn't wait)
   8a. PyPDFLoader reads the PDF
   8b. TextSplitter creates ~80 chunks
   8c. Gemini Embeddings API called (one call per chunk = ~80 API calls)
   8d. Chunks + vectors stored in ChromaDB collection "user_{id}_doc_{id}"
   8e. SQLite document status updated to "ready"
9. Frontend polls GET /api/documents/{id}/status every 3 seconds
10. When status = "ready", shows "Chat now" button
```

### Query Flow (step by step)

```
1. Student types question: "What is the difference between BFS and DFS?"
2. Frontend calls askQuestion(documentId, question, token) from lib/api.ts
3. FastAPI receives POST /api/chat
4. FastAPI verifies JWT, checks user owns this document, checks status="ready"
5. RAG pipeline starts:
   5a. Question embedded via Gemini Embeddings API → 768-dim vector
   5b. ChromaDB cosine similarity search → top 5 most relevant chunks
   5c. Prompt built: "Answer from context only. Context: [5 chunks]. Question: [question]"
   5d. Prompt sent to Gemini 1.5 Flash
   5e. Gemini returns answer
6. FastAPI responds: { answer, sources: [{page, preview}] }
7. Frontend renders answer + collapsible source cards
```

---

## 12. Prompt Engineering Design

### The Prompt Template

```python
# backend/rag/prompt_template.py
from langchain.prompts import PromptTemplate

STUDY_ASSISTANT_PROMPT = """
You are a helpful study assistant for students.
Your job is to answer questions using ONLY the student's own uploaded notes.

STRICT RULES:
1. Answer ONLY from the provided context. Do not use outside knowledge.
2. If the answer is not in the context, respond exactly with:
   "I couldn't find this in your notes. The context I searched covered pages: {pages_searched}"
3. Be clear and structured. Use bullet points for lists, numbered steps for processes.
4. At the end of every answer, cite the source page numbers.
5. Never make up information or say "generally" or "typically" — only state what the notes say.

Context from your notes:
{context}

Student's question: {question}

Answer (remember: ONLY from the notes above):
"""

def get_prompt():
    return PromptTemplate(
        template=STUDY_ASSISTANT_PROMPT,
        input_variables=["context", "question"]
    )
```

### Why Each Rule Exists

```
Rule 1 — "ONLY from context"
→ Prevents Gemini from mixing in its training data with your notes.
  Without this, Gemini might answer correctly but from general knowledge,
  not from the student's specific course material.

Rule 2 — Explicit failure mode
→ Prevents hallucination. Better to say "not found" than to make something up.
  This is the most important hallucination guardrail.

Rule 3 — Structure requirement
→ Study material benefits from structure. Bullet points > walls of text.

Rule 4 — Source citation
→ Student can verify. Builds trust. Interviewers love this — it shows
  you thought about explainability and grounding.

Rule 5 — No hedging language
→ "Generally" and "typically" are signals the model is going off-context.
  Banning them forces it to stay grounded.
```

---

## 13. Error Handling Strategy

### Frontend Error Handling

```typescript
// Pattern: try/catch with user-friendly messages
// Never show raw error strings to users

async function handleUpload(file: File) {
  setLoading(true)
  setError(null)

  try {
    const token = await getToken()
    await uploadDocument(file, token)
    setSuccess("Notes uploaded! Processing in the background...")
  } catch (err) {
    // Map technical errors to human-readable messages
    if (err.message.includes("10MB")) {
      setError("File is too large. Please upload a PDF under 10MB.")
    } else if (err.message.includes("401")) {
      setError("Session expired. Please sign in again.")
    } else {
      setError("Upload failed. Please try again.")
    }
  } finally {
    setLoading(false)
  }
}
```

### Backend Error Handling

```python
# FastAPI automatically returns proper JSON error responses
# All HTTPExceptions become { "detail": "your message" } with correct status code

# Known failure points and how to handle them:

# 1. Bad PDF (corrupted, password-protected, scanned)
try:
    pages = loader.load()
    if len(pages) == 0:
        raise ValueError("PDF is empty or unreadable")
except Exception as e:
    raise HTTPException(400, f"Could not read PDF: {str(e)}")

# 2. Gemini API rate limit (429)
# LangChain handles retries automatically with exponential backoff
# But you should catch it and surface a useful error:
except Exception as e:
    if "429" in str(e) or "quota" in str(e).lower():
        raise HTTPException(429, "AI service is busy. Please try again in a moment.")

# 3. ChromaDB collection doesn't exist
# Happens if someone deletes the chroma_db/ folder
except Exception as e:
    if "does not exist" in str(e):
        raise HTTPException(404, "Document index not found. Please re-upload the document.")
```

---

## 14. Environment & Configuration

### `backend/config.py`

```python
import os
from dotenv import load_dotenv

load_dotenv()

# API Keys
GOOGLE_API_KEY       = os.getenv("GOOGLE_API_KEY")
CLERK_PUBLISHABLE_KEY = os.getenv("CLERK_PUBLISHABLE_KEY")

# RAG Settings
CHUNK_SIZE      = 500
CHUNK_OVERLAP   = 50
TOP_K           = 5
EMBEDDING_MODEL = "models/embedding-001"
LLM_MODEL       = "gemini-1.5-flash"
TEMPERATURE     = 0.3

# Storage
UPLOAD_DIR       = "./uploads"
CHROMA_PERSIST_DIR = "./chroma_db"
DATABASE_URL     = "sqlite:///./metadata.db"

# Limits
MAX_FILE_SIZE_MB = 10
```

### `backend/.env.example`

```bash
GOOGLE_API_KEY=your_google_api_key_here
CLERK_PUBLISHABLE_KEY=pk_test_your_key_here
```

### `frontend/.env.local.example`

```bash
NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=pk_test_your_key_here
CLERK_SECRET_KEY=sk_test_your_key_here
NEXT_PUBLIC_CLERK_SIGN_IN_URL=/sign-in
NEXT_PUBLIC_CLERK_SIGN_UP_URL=/sign-up
NEXT_PUBLIC_CLERK_AFTER_SIGN_IN_URL=/dashboard
NEXT_PUBLIC_CLERK_AFTER_SIGN_UP_URL=/dashboard
NEXT_PUBLIC_API_URL=http://localhost:8000
```

---

## 15. Testing Plan

### Backend Tests (`backend/tests/`)

```python
# test_ingestor.py
import pytest
from rag.ingestor import ingest_pdf

def test_ingest_valid_pdf():
    result = ingest_pdf("tests/fixtures/sample.pdf", "test_user", "doc_test")
    assert result["page_count"] > 0
    assert result["chunk_count"] > 0
    assert result["chunk_count"] >= result["page_count"]  # always more chunks than pages

def test_ingest_nonexistent_file():
    with pytest.raises(Exception):
        ingest_pdf("nonexistent.pdf", "user", "doc")

# test_routes.py
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_health_check():
    res = client.get("/health")
    assert res.status_code == 200
    assert res.json() == {"status": "ok"}

def test_upload_requires_auth():
    # Without an Authorization header, should get 403
    res = client.post("/api/documents/upload")
    assert res.status_code in [401, 403, 422]

def test_chat_empty_question():
    # Mocked auth for this test
    res = client.post("/api/chat",
        json={"document_id": "doc_123", "question": ""},
        headers={"Authorization": "Bearer fake_token"}
    )
    assert res.status_code in [400, 401]  # 400 if auth passes, 401 if not
```

---

## 16. Known Limitations & Trade-offs

These are your "if I had more time" and "I made a deliberate trade-off" points for the interview.

| Limitation | Why It Exists | Production Fix |
|---|---|---|
| No streaming responses | RetrievalQA doesn't stream easily | LangChain callbacks + SSE (Server-Sent Events) |
| Scanned PDFs fail | PyPDFLoader needs text-layer PDFs | Add Tesseract OCR or AWS Textract |
| Background tasks not persistent | If server restarts, in-flight ingestion jobs are lost | Use Celery + Redis task queue |
| Local file storage | PDF files lost if server restarts or redeploys | AWS S3 or Cloudflare R2 |
| SQLite not production-ready | No concurrent writes at scale | PostgreSQL with connection pooling |
| No re-ingestion on duplicate upload | Same PDF uploaded twice doubles the chunks | Hash file content, check before ingesting |
| ChromaDB on local disk | Lost on server restart/redeploy | Managed vector DB (Pinecone, Qdrant Cloud) |
| No answer quality evaluation | Can't tell if Gemini is giving good answers | Add LLM-as-judge evaluation layer |
| 10MB file size limit | Keeps API fast and prevents abuse | Increase limit + chunked upload for large files |
| Polling for status | Wastes API calls | Replace with WebSockets for real-time status |

---

## 17. Build Order

### Day 1 — Foundation
```
Morning:
  □ Create folder structure (frontend/ and backend/)
  □ Set up Python venv, install backend dependencies
  □ Set up Next.js: npx create-next-app@latest frontend
  □ Get Gemini API key, test one raw API call in Python
  □ Get Clerk account, note your keys

Afternoon:
  □ Build config.py
  □ Build ingestor.py — test it on a sample PDF in Python (no FastAPI yet)
  □ Verify chunks are stored in ChromaDB
```

### Day 2 — Backend API
```
Morning:
  □ Build main.py, database.py, models.py
  □ Run FastAPI: uvicorn main:app --reload
  □ Open http://localhost:8000/docs — verify it shows your endpoints

Afternoon:
  □ Build documents.py router (upload + list + delete)
  □ Build retriever.py + chat.py router
  □ Test all endpoints via FastAPI's built-in /docs UI (no frontend needed yet)
```

### Day 3 — Frontend
```
Morning:
  □ Install Clerk in Next.js, wrap layout with ClerkProvider
  □ Test sign-in/sign-up flow works (Clerk pre-built UI)
  □ Build /dashboard page: document list + upload button
  □ Wire upload to backend API

Afternoon:
  □ Build /dashboard/chat/[documentId] page
  □ Wire chat input to backend /api/chat
  □ Display answer + source cards
  □ Polish: loading states, error messages, empty states
```

### Day 4 — Polish + Demo Prep
```
  □ Test full flow end-to-end with a real PDF
  □ Write README (setup instructions for both services)
  □ Add error handling for edge cases
  □ Push to GitHub with clean commit history
  □ Deploy: Vercel (frontend) + Railway or Render (backend)
  □ Practice explaining the architecture out loud
```

---

## 18. Interview Answer Cheatsheet

### Q: Walk me through your system architecture.
**A:** The app has two services. A Next.js frontend handles the UI and auth via Clerk — when a user is logged in, every API call includes a Clerk JWT token in the Authorization header. A FastAPI backend receives those calls, verifies the token, and runs the RAG pipeline. I chose FastAPI because all my ML code — LangChain, ChromaDB, Gemini — is Python. The backend stores file metadata in SQLite and vectors in ChromaDB, with one ChromaDB collection per user per document for complete data isolation.

### Q: Why FastAPI and not Next.js API routes?
**A:** You can't run LangChain or ChromaDB in a JavaScript serverless function. The ML stack only exists in Python. FastAPI was the clear choice — it also gives you automatic OpenAPI docs, type validation via Pydantic, and native async support which matters for a multi-user app.

### Q: How do you ensure one user can't access another user's documents?
**A:** Three layers. First, every API endpoint calls `Depends(get_current_user)` which verifies the Clerk JWT and returns a user_id. Second, every SQLite query filters by that user_id — you literally can't get another user's document from the DB. Third, ChromaDB collections are namespaced as `user_{user_id}_{doc_id}` — even if you somehow knew another user's collection name, the vector search only returns chunks from that collection.

### Q: Why do you use two databases — SQLite and ChromaDB?
**A:** They solve different problems. SQLite answers structured relational questions: "What documents does this user have? What's the status of this upload? When was it created?" ChromaDB answers semantic questions: "Which text chunks from this document are most similar in meaning to this question?" You can't do vector similarity search efficiently in SQL, and you can't do joins and filters efficiently in a vector database. Each database is used for what it's designed for.

### Q: Why did you use background tasks for PDF ingestion?
**A:** Ingesting a PDF makes one embedding API call per chunk — a 20-page PDF creates ~80 chunks, so 80 API calls. That takes 10–30 seconds. If I processed it synchronously, the user would stare at a loading screen. With FastAPI's BackgroundTasks, I respond immediately with "processing" status and run the ingestion after the response is sent. The frontend polls for status and shows a "ready" state when ingestion completes.

### Q: What would you improve with more time?
**A:** Replace polling with WebSockets for real-time ingestion status. Replace background tasks with Celery + Redis for persistent job queues (currently a server restart loses in-progress jobs). Add hybrid retrieval — combining semantic search with BM25 keyword search — for better precision on technical terms. And move file storage to S3 so PDFs persist across server restarts.

---

*StudyVault | RAG-powered multi-user study assistant | Handpick AI Engineering Intern*
