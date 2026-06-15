# Self-Healing Multi-Agent Tax Filing System

Architecture-first scaffold for a local, Ollama-only tax document processing
and reporting platform.

## Status

The initial end-to-end implementation is available. It includes local
OCR/vision extraction, deterministic 2025 tax calculations, confidence-based
verification, bounded remediation, LangGraph orchestration, persistence,
React UI, and ReportLab PDF generation.

## Planned Stack

- FastAPI
- React
- PostgreSQL
- ChromaDB
- LangGraph
- Ollama
- Tesseract OCR
- ReportLab

## Planned Models

- `llama3.2-vision:latest` for document understanding
- `qwen2.5-coder:7b` for constrained local assistance

No OpenAI, Gemini, or Claude API dependency is planned.

## Documents

- [System architecture](docs/architecture.md)
- [Project structure](docs/project-structure.md)

## Run Locally

Ollama must be running with:

```powershell
ollama pull llama3.2-vision:latest
ollama pull qwen2.5-coder:7b
```

Start the backend:

```powershell
cd backend
py -m pip install -r requirements.txt
py -m uvicorn app.main:app --reload --port 8000
```

Start the frontend:

```powershell
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173`. API documentation is available at
`http://localhost:8000/docs`.

The default database is SQLite for immediate development. Copy
`backend/.env.example` to `backend/.env` and run `docker compose up -d` to use
PostgreSQL. ChromaDB can run embedded at the configured path; the compose file
also provides a standalone Chroma service for later deployment.

## Important Scope

The installed deterministic rules cover US federal tax year 2025. State tax is
currently modeled as a configurable flat rate because state-specific rule
packs have not yet been supplied. The generated status is `ready_for_filing`;
the system does not transmit returns to IRS or state e-file APIs.
