# Contributing to SmartClassroom

Thanks for your interest in contributing. This document covers everything you need to get started — from setting up your dev environment to submitting a pull request.

---

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Project Structure](#project-structure)
- [Development Setup](#development-setup)
- [Running Services Locally](#running-services-locally)
- [Making Changes](#making-changes)
- [Coding Standards](#coding-standards)
- [Submitting a Pull Request](#submitting-a-pull-request)
- [Reporting Bugs](#reporting-bugs)
- [Suggesting Features](#suggesting-features)

---

## Code of Conduct

Be respectful, constructive, and collaborative. We welcome contributors of all experience levels.

---

## Project Structure

```
SmartClassroom/
├── backend-service/     # FastAPI REST API (Python)
├── ai-service/          # Face recognition service (Python + PyTorch)
├── frontend/            # Browser UI (Vanilla JS + HTML + CSS)
├── db/                  # MySQL schema and Dockerfile
├── Time-table-scheduler/ # Timetable service (Java/Spring Boot)
└── docker-compose.yml   # Orchestration
```

Each service is independently deployable. Changes to one service should not require changes to others unless the API contract changes.

---

## Development Setup

### Prerequisites

- [Docker Desktop](https://www.docker.com/products/docker-desktop/)
- Python 3.11+ (for local backend/AI service development)
- Node.js (optional, only if you add a build step to the frontend)
- Git

### 1. Fork and clone

```bash
git clone https://github.com/your-org/SmartClassroom.git
cd SmartClassroom
```

### 2. Create a feature branch

```bash
git checkout -b feature/your-feature-name
# or for bugfixes:
git checkout -b fix/short-description
```

### 3. Set up environment

```bash
cp .env.example .env
# Edit .env if you need custom DB credentials or ports
```

### 4. Start the full stack

```bash
docker compose up -d --build
```

---

## Running Services Locally

For faster iteration, you can run individual services outside Docker while keeping the rest containerized.

### Backend Service

```bash
cd backend-service
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # macOS/Linux

pip install -r requirements.txt

# Set env vars pointing to local DB
set DB_HOST=localhost
set DB_PORT=3307
set DB_USER=root
set DB_PASSWORD=root
set DB_NAME=smart_classroom

uvicorn app.main:app --reload --port 8001
```

### AI Service

```bash
cd ai-service
python -m venv venv
venv\Scripts\activate

pip install -r requirements.txt

set DB_HOST=localhost
set DB_PORT=3307
set TORCH_DEVICE=cpu

uvicorn app.main:app --reload --port 8002
```

> Note: First run downloads FaceNet model weights (~100MB). This is cached after the first download.

### Frontend

The frontend is static HTML/JS/CSS — just open `frontend/public/index.html` in a browser, or serve it with any static file server:

```bash
cd frontend/public
python -m http.server 8080
```

> The frontend proxies `/api/backend/*` and `/api/ai/*` via Nginx in Docker. For local dev, you may need to update the fetch URLs in `app.js` to point directly to `localhost:8001` and `localhost:8002`.

---

## Making Changes

### Backend (`backend-service/`)

- All endpoints live in `app/main.py`
- DB connection logic is in `app/db/session.py`
- Schema initialization is in `app/db/init_db.py`
- Config/settings in `app/core/config.py`

When adding a new endpoint:
1. Add the route to `app/main.py`
2. Add a Pydantic model for request/response if needed
3. Use `get_connection()` for DB access and always close cursor + connection in a `finally` block or after use
4. Test via http://localhost:8001/docs

### AI Service (`ai-service/`)

- Endpoints in `app/main.py`
- Face detection + embedding logic in `app/services/face_engine.py`
- Embedding storage in `app/services/db_embedding_store.py`
- Settings in `app/core/settings.py`
- Response schemas in `app/schemas/contracts.py`

When modifying the recognition pipeline:
1. Keep `FaceEngine` stateless — it should only do detection and embedding
2. Storage concerns belong in `DBEmbeddingStore`
3. The `_cache` in `DBEmbeddingStore` is invalidated on every write — keep this behavior

### Frontend (`frontend/public/`)

- All logic is in `app.js` (no build step, no framework)
- Styles in `styles.css`
- Keep JS vanilla — do not introduce npm dependencies or bundlers without discussion
- Use `async/await` consistently, avoid raw `.then()` chains
- Canvas overlay drawing functions are in the `drawMatchesOverlay` / `drawHud` section

### Database (`db/`)

- Schema is in `init.sql`
- If you add a table or column, update `init.sql` with `CREATE TABLE IF NOT EXISTS` or `ALTER TABLE IF NOT EXISTS` so it's idempotent
- Add appropriate indexes for any columns used in `WHERE` or `JOIN` clauses
- Foreign keys should use `ON DELETE CASCADE` or `ON DELETE SET NULL` — never leave orphaned rows

---

## Coding Standards

### Python

- Follow [PEP 8](https://peps.python.org/pep-0008/)
- Use type hints on all function signatures
- Use `from __future__ import annotations` for forward references
- Prefer `f-strings` over `.format()` or `%`
- Keep functions focused — if a function does more than one thing, split it
- Close DB cursors and connections explicitly (no context manager currently used — match existing style)

### JavaScript

- Use `const` by default, `let` only when reassignment is needed, never `var`
- Use `async/await` for all async operations
- Keep DOM queries at the top of the file (already established pattern)
- Event listeners go at the bottom, grouped by feature section
- No external libraries — keep it dependency-free

### SQL

- Table and column names in `snake_case`
- All tables need a primary key
- Use `VARCHAR(64)` for IDs, `BIGINT AUTO_INCREMENT` for surrogate keys
- Always add indexes on foreign key columns

### Git Commits

Use clear, imperative commit messages:

```
feat: add batch face enrollment endpoint
fix: close DB cursor in session end handler
docs: update API reference in README
refactor: extract face verification into helper function
```

Prefix options: `feat`, `fix`, `docs`, `refactor`, `test`, `chore`

---

## Submitting a Pull Request

1. Make sure your branch is up to date with `main`:
   ```bash
   git fetch origin
   git rebase origin/main
   ```

2. Run the full stack and manually test your changes:
   ```bash
   docker compose up -d --build
   ```

3. Check service health:
   ```bash
   docker compose ps
   ```

4. Push your branch:
   ```bash
   git push -u origin feature/your-feature-name
   ```

5. Open a pull request against `main` with:
   - A clear title (under 70 characters)
   - Description of what changed and why
   - Steps to test the change
   - Any API contract changes called out explicitly

6. Address review feedback — keep the conversation constructive

---

## Reporting Bugs

Open a GitHub issue with:

- A short, descriptive title
- Steps to reproduce
- Expected behavior vs actual behavior
- Relevant logs (`docker logs backend`, `docker logs ai_service`, browser console)
- Your OS and Docker version

---

## Suggesting Features

Open a GitHub issue with the `enhancement` label. Include:

- The problem you're trying to solve
- Your proposed solution
- Any alternatives you considered
- Whether you're willing to implement it

---

## Common Gotchas

**AI service takes a long time to start on first run**
The FaceNet model weights are downloaded on first startup. This is normal. The `/health` endpoint responds immediately even while the model loads.

**Face not detected**
Ensure good lighting and that the face is clearly visible and not too far from the camera. The MTCNN detector requires a reasonably sized face in the frame.

**DB connection refused when running outside Docker**
The DB container maps to `localhost:3307` (not 3306) to avoid conflicts with local MySQL installs. Set `DB_PORT=3307` when running services locally.

**Camera not working in browser**
WebRTC `getUserMedia` requires either `localhost` or HTTPS. It will not work on plain HTTP with a non-localhost hostname.

**`cursor.is_connected()` error**
`is_connected()` is a method on the connection object, not the cursor. Use `connection.is_connected()` or simply check `if cursor:` for cursor validity.
