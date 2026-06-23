# PassportAI

An AI-powered visa workflow assistant for international students and travellers. PassportAI helps you navigate visa requirements through conversational Q&A, personalised document checklists, policy change alerts, passport scanning, and smart form filling.

---

## Table of Contents

1. [What the app does](#what-the-app-does)
2. [Architecture overview](#architecture-overview)
3. [Prerequisites](#prerequisites)
4. [Quick start — Docker (recommended)](#quick-start--docker-recommended)
5. [Manual setup — local development](#manual-setup--local-development)
6. [Environment variables reference](#environment-variables-reference)
7. [Running with mock vs real AI](#running-with-mock-vs-real-ai)
8. [Database migrations](#database-migrations)
9. [Project structure](#project-structure)
10. [API reference](#api-reference)
11. [Troubleshooting](#troubleshooting)

---

## What the app does

| Feature | Description |
|---|---|
| **Conversational Q&A** | Ask questions about visa requirements; answers are grounded in policy data with confidence scores and source citations |
| **Document Checklist** | Generates a personalised, ordered checklist of required documents for any passport/destination/purpose combination |
| **Policy Change Alerts** | Monitors tracked visa cases on a schedule and alerts you when requirements, fees, or processing times change |
| **Document Scanner** | Upload a passport or national ID image; extracts fields (name, DOB, expiry, etc.) with per-field confidence scores |
| **Smart Form Filler** | Upload a blank visa application form (PDF or DOCX); auto-fills it using scanned passport data |

---

## Architecture overview

```
┌─────────────────┐     ┌──────────────────────────────────┐
│  React Frontend │────▶│  FastAPI Backend  (port 8000)    │
│  (port 3000)    │     │                                  │
└─────────────────┘     │  ┌─────────┐  ┌──────────────┐   │
                        │  │ RAG /   │  │  APScheduler │   │
                        │  │ ChromaDB│  │  (cron jobs) │   │
                        │  └─────────┘  └──────────────┘   │
                        │  ┌──────────────────────────┐    │
                        │  │  Ollama  (LLM + Vision)  │    │
                        │  │  llama3.2  |  llava      │    │
                        │  └──────────────────────────┘    │
                        └────────────┬─────────────────────┘
                                     │
                        ┌────────────▼─────────────────────┐
                        │  PostgreSQL (port 5432)          │
                        │  Redis      (port 6379)          │
                        └──────────────────────────────────┘
```

**All AI is local.** There are no external API keys. The LLM runs via [Ollama](https://ollama.ai) on your own machine.

---

## Prerequisites

You need the following installed before starting. Exact minimum versions are listed — newer versions will work.

### 1. Docker Desktop ≥ 4.x (recommended path)

The easiest way to run everything. Docker Compose starts PostgreSQL, Redis, the FastAPI backend, and the React frontend in one command.

- **Mac:** https://docs.docker.com/desktop/install/mac-install/
- **Windows:** https://docs.docker.com/desktop/install/windows-install/ (requires WSL 2)
- **Linux:** https://docs.docker.com/engine/install/

Verify installation:
```bash
docker --version          # Docker version 24.x.x or higher
docker compose version    # Docker Compose version v2.x.x or higher
```

> **Windows users:** Make sure WSL 2 is enabled and Docker Desktop is set to use the WSL 2 backend. See https://docs.docker.com/desktop/wsl/

---

### 2. Ollama (required for real AI responses)

Ollama runs the language models locally. Without it the app still works using hardcoded mock responses — useful for development, not for a real demo.

**Install:**
- **Mac / Linux:** https://ollama.ai/download
- **Windows:** https://ollama.ai/download (native installer available)

Verify installation:
```bash
ollama --version
```

**Pull the two required models** (do this once; each download is a few GB):
```bash
# Text model — used for Q&A, checklist extraction, change summaries
ollama pull llama3.2

# Vision model — used for passport/ID scanning
ollama pull llava
```

Verify both are available:
```bash
ollama list
# Should show: llama3.2  and  llava
```

> **Note:** `llama3.2` is ~2 GB. `llava` is ~4.5 GB. Make sure you have at least 10 GB of free disk space and 8 GB RAM. For better performance, 16 GB RAM is recommended.

---

### 3. Git

To clone the repository.

- **Mac:** comes pre-installed, or install via `xcode-select --install`
- **Windows:** https://git-scm.com/download/win
- **Linux:** `sudo apt install git` or equivalent

---

### For manual (non-Docker) setup only

If you prefer to run the backend and frontend directly on your machine instead of through Docker, you additionally need:

#### Python 3.12+
- **Mac:** `brew install python@3.12` or https://www.python.org/downloads/
- **Windows / Linux:** https://www.python.org/downloads/

Verify:
```bash
python3 --version   # Python 3.12.x
```

#### Node.js 20+ and npm 10+
- **All platforms:** https://nodejs.org/en/download (choose the LTS version)

Verify:
```bash
node --version   # v20.x.x or higher
npm --version    # 10.x.x or higher
```

#### PostgreSQL 16
Only needed if you want a local Postgres instead of the Docker one.
- **Mac:** `brew install postgresql@16`
- **Windows / Linux:** https://www.postgresql.org/download/

---

## Quick start — Docker (recommended)

This gets the entire stack running in five steps.

### Step 1 — Clone the repository

```bash
git clone <your-repo-url> passportai
cd passportai
```

### Step 2 — Create your `.env` file

```bash
cp .env.example .env
```

Open `.env` and set a secure secret key. Everything else works as-is for local development:

```env
# Generate a secure key with:
# python3 -c "import secrets; print(secrets.token_hex(32))"
SECRET_KEY=replace-this-with-a-real-secret-key

# Leave these as true for now — see "Running with mock vs real AI" below
LLM_MOCK=true
SCRAPER_MOCK=true
```

### Step 3 — Start Ollama

Ollama must be running on your host machine (not inside Docker) before starting the stack.

```bash
# Start the Ollama server
ollama serve
```

Leave this terminal open. On Mac and Windows, Ollama starts automatically after installation and runs in the system tray — you do not need to run `ollama serve` manually in that case.

### Step 4 — Start the full stack

```bash
docker compose up --build
```

The first build takes 3–5 minutes as it installs all Python and Node dependencies. Subsequent starts are fast.

Once you see output like this, everything is running:

```
api_1       | ✅ Database connected
api_1       | ✅ ChromaDB ready (24 chunks indexed)
api_1       | ✅ Change-tracking scheduler started (interval: 24h)
frontend_1  | VITE v5.x.x  ready in 800 ms
frontend_1  |   ➜  Local: http://localhost:3000/
```

### Step 5 — Switch to real AI (optional but recommended for demos)

Edit `.env`:

```env
LLM_MOCK=false
SCRAPER_MOCK=false
OLLAMA_BASE_URL=http://host.docker.internal:11434
```

Then restart the API container:

```bash
docker compose restart api
```

> **Linux users:** `host.docker.internal` does not resolve automatically on Linux. Add this to the `api` service in `docker-compose.yml`:
> ```yaml
> extra_hosts:
>   - "host.docker.internal:host-gateway"
> ```

### Access the app

| Service | URL |
|---|---|
| **Frontend** | http://localhost:3000 |
| **API docs (Swagger)** | http://localhost:8000/docs |
| **pgAdmin** (DB browser) | http://localhost:5050 |

pgAdmin credentials: `admin@passportai.com` / `admin`

Register an account at http://localhost:3000/register and start using the app.

---

## Manual setup — local development

Use this if you prefer to run processes directly without Docker, or if you want faster hot-reload during active development.

### Step 1 — Clone and enter the project

```bash
git clone <your-repo-url> passportai
cd passportai
```

### Step 2 — Start PostgreSQL and Redis

The easiest way is still to use Docker just for the data services:

```bash
docker compose up db redis -d
```

Or if you have PostgreSQL installed locally, create the database manually:

```bash
createdb passportai
createuser passportai --pwprompt   # set password to: passportai
psql -c "GRANT ALL ON DATABASE passportai TO passportai;"
```

### Step 3 — Set up the Python environment

```bash
# Create a virtual environment
python3 -m venv .venv

# Activate it
source .venv/bin/activate        # Mac / Linux
.venv\Scripts\activate           # Windows (Command Prompt)
.venv\Scripts\Activate.ps1       # Windows (PowerShell)

# Install dependencies
pip install -r requirements.txt
```

> **Note:** The first install takes a few minutes because `sentence-transformers` downloads a ~90 MB embedding model.

### Step 4 — Configure environment

```bash
cp .env.example .env
```

Edit `.env` for local development (note `localhost` instead of Docker service names):

```env
DATABASE_URL=postgresql://passportai:passportai@localhost:5432/passportai
REDIS_URL=redis://localhost:6379/0
SECRET_KEY=replace-this-with-a-real-secret-key
OLLAMA_BASE_URL=http://localhost:11434
LLM_MOCK=true
SCRAPER_MOCK=true
```

### Step 5 — Run database migrations

```bash
alembic upgrade head
```

You should see:
```
INFO  [alembic.runtime.migration] Running upgrade -> 37561d152d9a, initial schema
```

### Step 6 — Start Ollama

```bash
ollama serve
```

### Step 7 — Start the backend

```bash
uvicorn app.main:app --reload --port 8000
```

You should see:
```
✅ Database connected
✅ ChromaDB ready (24 chunks indexed)
✅ Change-tracking scheduler started
INFO:     Uvicorn running on http://127.0.0.1:8000
```

### Step 8 — Start the frontend

Open a second terminal:

```bash
cd frontend
npm install
npm run dev
```

The frontend starts at http://localhost:3000 and proxies all `/api` calls to `http://localhost:8000` automatically.

---

## Environment variables reference

All variables live in `.env` at the project root.

| Variable | Default | Description |
|---|---|---|
| `DATABASE_URL` | `postgresql://passportai:passportai@localhost:5432/passportai` | PostgreSQL connection string. Use `db` instead of `localhost` when running inside Docker. |
| `SECRET_KEY` | `dev-secret-key-change-in-production` | JWT signing key. **Always change this.** Generate with `python3 -c "import secrets; print(secrets.token_hex(32))"` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `60` | How long login tokens stay valid. |
| `REDIS_URL` | `redis://redis:6379/0` | Redis connection string. Use `localhost` for local dev, `redis` for Docker. |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Where Ollama is running. Use `http://host.docker.internal:11434` from inside Docker on Mac/Windows. |
| `OLLAMA_MODEL` | `llama3.2` | Text model for Q&A, checklists, and change summaries. |
| `OLLAMA_VISION_MODEL` | `llava` | Vision model for passport scanning. |
| `LLM_MOCK` | `true` | Set to `false` to use real Ollama responses. |
| `CHROMA_PERSIST_DIR` | `./chroma_data` | Where ChromaDB stores the vector index on disk. |
| `CHROMA_COLLECTION_NAME` | `visa_policies` | Name of the ChromaDB collection. |
| `SCRAPER_MOCK` | `true` | Set to `false` to scrape live Wikipedia / embassy pages. |
| `POLICY_REFRESH_INTERVAL_HOURS` | `24` | How often the change-tracking cron job runs. Set to `1` for testing. |

---

## Running with mock vs real AI

The app ships with two mock flags so it runs without any external dependencies.

### Mock mode (default — `LLM_MOCK=true`, `SCRAPER_MOCK=true`)

- All LLM responses return hardcoded, realistic-looking text.
- The scraper returns 11 sample visa policies (Germany, USA, UK, Canada, Schengen).
- Passport scanning returns a sample Pakistani passport extraction.
- The full UI works — Q&A, checklists, alerts, scanner, form filler.
- Good for: development, testing the UI, demos without Ollama installed.

### Real mode (`LLM_MOCK=false`, `SCRAPER_MOCK=false`)

Requires Ollama running with both models pulled (see [Prerequisites](#prerequisites)).

```env
LLM_MOCK=false
SCRAPER_MOCK=false
```

Restart the backend after changing these values. The app will use `llama3.2` for natural language answers and `llava` to extract fields from uploaded passport images.

> **Tip:** You can mix the flags. `LLM_MOCK=false, SCRAPER_MOCK=true` is useful when testing the LLM pipeline without waiting for live scrapes.

---

## Database migrations

Migrations are managed with [Alembic](https://alembic.sqlalchemy.org/). The initial migration creates all seven tables: `users`, `visa_cases`, `checklists`, `checklist_items`, `documents`, `change_alerts`, `rag_interactions`.

**Apply all migrations (run this on first setup):**
```bash
alembic upgrade head
```

**Inside Docker:**
```bash
docker compose exec api alembic upgrade head
```

**Check current migration state:**
```bash
alembic current
```

**Roll back one migration:**
```bash
alembic downgrade -1
```

If you see a migration conflict and want to fully reset (development only — this drops all data):
```bash
alembic downgrade base
alembic upgrade head
```

---

## Project structure

```
passportai/
├── app/
│   ├── core/
│   │   ├── config.py           # All settings, loaded from .env
│   │   └── security.py         # JWT creation/verification, password hashing
│   ├── db/
│   │   ├── base.py             # SQLAlchemy declarative base
│   │   └── session.py          # DB engine and session factory
│   ├── models/                 # SQLAlchemy ORM models
│   │   ├── user.py
│   │   ├── visa_case.py
│   │   ├── checklist.py
│   │   ├── document.py
│   │   ├── change_alert.py
│   │   └── rag_interaction.py
│   ├── schemas/                # Pydantic request/response schemas
│   │   ├── auth.py
│   │   ├── chat.py
│   │   ├── checklist.py
│   │   ├── document.py
│   │   └── change_alert.py
│   ├── endpoints/              # FastAPI route handlers
│   │   ├── router.py           # Mounts all routers
│   │   ├── auth.py             # /auth/register, /auth/login, /auth/me
│   │   ├── chat.py             # /chat
│   │   ├── checklists.py       # /checklists, /visa-cases
│   │   ├── change_alerts.py    # /change-alerts
│   │   ├── documents.py        # /documents/scan, /documents/{id}/fill
│   │   └── rag.py              # /rag/ingest, /rag/search (debug)
│   ├── services/
│   │   ├── llm/
│   │   │   ├── llm_client.py         # Ollama text completion (+ mock)
│   │   │   ├── vision_client.py      # Ollama LLaVA vision (+ mock)
│   │   │   ├── agent.py              # Q&A agent: tool selection, prompting, confidence
│   │   │   ├── tools.py              # Typed RAG tools
│   │   │   └── checklist_extractor.py
│   │   ├── rag/
│   │   │   ├── chroma_client.py      # ChromaDB singleton
│   │   │   ├── chunker.py            # Text → overlapping chunks
│   │   │   ├── ingestion.py          # Scrape → chunk → embed → upsert
│   │   │   └── search.py             # Semantic search with metadata filtering
│   │   ├── scraper/
│   │   │   ├── scraper.py            # Live scraper (Wikipedia + embassy pages)
│   │   │   └── mock_data.py          # 11 sample visa policies
│   │   └── change_tracking/
│   │       ├── snapshot_store.py     # Save/load policy snapshots for diffing
│   │       ├── differ.py             # Text diff + change type classification
│   │       ├── summariser.py         # LLM plain-language change summaries
│   │       └── tracker.py            # Main job: scrape → diff → alert → re-ingest
│   ├── api/deps/
│   │   └── auth.py             # get_current_user FastAPI dependency
│   ├── tasks/
│   │   └── scheduler.py        # APScheduler setup and job registration
│   └── main.py                 # FastAPI app, lifespan (DB, RAG seed, scheduler)
├── alembic/
│   ├── env.py
│   └── versions/
│       └── 37561d152d9a_initial_schema.py
├── frontend/
│   ├── src/
│   │   ├── App.jsx             # Routes + AuthProvider + Toaster
│   │   ├── context/
│   │   │   └── AuthContext.jsx # JWT state, login/logout
│   │   ├── services/
│   │   │   └── api.js          # All API calls (axios)
│   │   ├── components/layout/
│   │   │   └── Layout.jsx      # Sidebar navigation
│   │   └── pages/
│   │       ├── LoginPage.jsx
│   │       ├── RegisterPage.jsx
│   │       ├── ChatPage.jsx
│   │       ├── ChecklistPage.jsx
│   │       ├── AlertsPage.jsx
│   │       └── ScannerPage.jsx
│   ├── index.html
│   ├── package.json
│   ├── vite.config.js          # Dev server + /api proxy to :8000
│   └── tailwind.config.js
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
├── alembic.ini
└── .env.example
```

---

## API reference

Full interactive documentation is at **http://localhost:8000/docs** when the backend is running.

### Authentication

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/v1/auth/register` | Create a new account |
| `POST` | `/api/v1/auth/login` | Log in, receive JWT token |
| `GET` | `/api/v1/auth/me` | Get current user (requires auth) |

### Conversational Q&A

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/v1/chat` | Ask a visa question; returns answer + confidence score + citations |

### Visa Cases

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/v1/visa-cases` | Create a tracked visa case |
| `GET` | `/api/v1/visa-cases` | List your visa cases |
| `GET` | `/api/v1/visa-cases/{id}` | Get a specific case |
| `DELETE` | `/api/v1/visa-cases/{id}` | Delete a case and all associated data |

### Checklists

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/v1/checklists` | Generate a new document checklist |
| `GET` | `/api/v1/checklists` | List all your checklists with items |
| `GET` | `/api/v1/checklists/{id}` | Get one checklist with all items |
| `PATCH` | `/api/v1/checklists/{id}/items/{item_id}` | Mark an item complete or incomplete |

### Change Alerts

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/v1/change-alerts` | List alerts (supports `?unread_only=true` and `?severity=critical`) |
| `GET` | `/api/v1/change-alerts/{id}` | Get a specific alert |
| `PATCH` | `/api/v1/change-alerts/{id}/read` | Mark alert as read or unread |
| `GET` | `/api/v1/change-alerts/visa-cases/{case_id}` | All alerts for one visa case |
| `POST` | `/api/v1/change-alerts/run` | Manually trigger change-tracking for your cases now |

### Documents

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/v1/documents/scan` | Upload passport or national ID; returns extracted fields with confidence scores |
| `POST` | `/api/v1/documents/{id}/fill` | Upload blank visa form (PDF/DOCX); returns filled form |
| `GET` | `/api/v1/documents` | List your documents |
| `GET` | `/api/v1/documents/{id}` | Get document with all extracted fields |
| `GET` | `/api/v1/documents/{id}/download` | Download the filled form file |

### RAG Admin

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/v1/rag/ingest` | Trigger re-ingestion of policy data into ChromaDB |
| `POST` | `/api/v1/rag/search` | Test semantic search directly (debug use) |

---

## Troubleshooting

### `❌ Database connection failed` on startup

The API started before PostgreSQL was ready. This usually self-resolves within a few seconds on the next health-check cycle. If it persists:

```bash
docker compose down
docker compose up --build
```

---

### `Cannot reach Ollama at http://host.docker.internal:11434`

**Mac / Windows:** Make sure Ollama is running. Check the system tray icon, or run `ollama serve` in a terminal.

**Linux:** `host.docker.internal` is not automatically available. Add the following to the `api` service in `docker-compose.yml`, then set `OLLAMA_BASE_URL=http://host.docker.internal:11434` in `.env`:

```yaml
extra_hosts:
  - "host.docker.internal:host-gateway"
```

---

### Initial ChromaDB ingestion is very slow

The first ingestion downloads the `all-MiniLM-L6-v2` sentence-transformer model (~90 MB). This happens once and is cached in the container volume. If you're on a slow connection, start with `SCRAPER_MOCK=true` and the mock data ingests instantly.

---

### `llava` model not found / passport scanning fails with an LLM error

Make sure the vision model was pulled before starting:

```bash
ollama pull llava
ollama list   # llava should appear in the list
```

If `LLM_MOCK=true` in `.env`, scanning works without Ollama and returns a hardcoded sample extraction.

---

### Port already in use

If ports 3000, 8000, 5432, 6379, or 5050 are taken by another process, edit the left side of the port mapping in `docker-compose.yml`:

```yaml
ports:
  - "3001:3000"   # frontend now reachable at http://localhost:3001
```

---

### Alembic: `Target database is not up to date`

```bash
alembic upgrade head
# or inside Docker:
docker compose exec api alembic upgrade head
```

---

### Windows: activation script is blocked by PowerShell

```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
.venv\Scripts\Activate.ps1
```

---

### Frontend shows a blank page

Make sure you are accessing the app through the Vite dev server at `http://localhost:3000`, not through the API port. The Vite proxy handles all `/api` forwarding.

If running with Docker and the frontend container starts but the page is blank, wait a few seconds — Vite's initial build takes a moment on the first load.

---

## Notes

- **File storage:** Uploaded files (passport scans, filled forms) are stored locally under `uploads/` inside the container. For a production deployment, replace `_save_upload()` in `app/services/scanner_service.py` with an S3 or GCS client.
- **Auth tokens:** JWTs are stored in `localStorage`. This is acceptable for a university project. A production app should use `httpOnly` cookies.
- **Privacy:** All LLM inference runs locally via Ollama. No document data or questions are sent to any external service.
- **CORS:** The backend currently allows all origins (`allow_origins=["*"]`). Restrict this to your frontend domain before any public deployment.