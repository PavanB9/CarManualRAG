# CarManualRAG

Ask natural-language questions about your car and get answers sourced directly from
your own owner's manual PDF — with page citations you can click to see the actual
page — instead of generic or hallucinated AI answers.

Upload any car manual PDF, ask questions in a chat UI, and click a
citation to see the exact manual page the answer came from. Built with a real eval
suite (retrieval accuracy, answer correctness, faithfulness) and a telemetry
dashboard, so this is measured, not just demoed — see [RESULTS.md](RESULTS.md) for
the tuning experiments and their numbers.

Manuals are full of vehicle-specific detail — exact warning-light meanings, fluid
specs, reset procedures, feature toggles buried five menus deep — that a web search
or a general-purpose AI won't know, because it's specific to your make, model,
year, and trim and was never on the open web to begin with. This answers those
niche questions straight from the document that actually has them, with a page
reference so you can double-check it yourself.

## How it works

1. **Ingest**: a PDF is parsed page-by-page (PyMuPDF), chunked with overlap, embedded
   locally (`fastembed` / `BAAI/bge-small-en-v1.5` — no API cost, no cloud call), and
   stored in a local Chroma vector DB, one collection per manual.
2. **Query**: a question is embedded and matched against the manual's chunks; the
   top-k excerpts and the question are sent to an LLM with a system prompt that
   requires it to answer only from the excerpts, cite page numbers, and say "I
   couldn't find this in the manual" rather than guess.
3. **Eval**: a 40-question test set (grounded in the actual manual text, with known
   correct answers and source pages) runs through the same pipeline automatically.
   An LLM judge scores answer correctness and faithfulness (does the answer contain
   any claim not supported by the retrieved excerpts — important for car-safety
   info); results are saved per run so you can compare configurations over time.

## Bring your own API key

This is meant to be cloned and run by anyone with their own key — no API costs are
on me, and no key is ever committed, logged, or sent anywhere but the provider you
choose.

Two providers are supported, selected via `LLM_PROVIDER` in `.env`:

- **OpenAI** (`LLM_PROVIDER=openai`, default) — get a key at
  [platform.openai.com/api-keys](https://platform.openai.com/api-keys). Model:
  `gpt-5.6-luna` by default (`OPENAI_MODEL` in `.env`).
- **Anthropic** (`LLM_PROVIDER=anthropic`) — get a key at
  [console.anthropic.com](https://console.anthropic.com). Model: `claude-sonnet-5`
  by default (`ANTHROPIC_MODEL` in `.env`).

Embeddings always run locally (no embedding-provider key needed).

## Run with Docker

The fastest way to run this — no local Python/Node setup needed. The manual
two-terminal setup below still works exactly as-is if you'd rather run it that way.

Requires [Docker](https://docs.docker.com/get-docker/) with Compose v2.

```bash
# 1. Configure your API key (same .env as the manual setup)
cp .env.example .env
# edit .env and add your OPENAI_API_KEY (or switch LLM_PROVIDER=anthropic and add
# ANTHROPIC_API_KEY)

# 2. Build and run both services
docker compose up --build
```

Open http://localhost:3000 (the frontend, served by nginx and proxying `/api` to
the backend). The backend API is also reachable directly at
http://localhost:8000 (e.g. http://localhost:8000/docs).

- **Data persists on your machine**: `./data/` is bind-mounted into the backend
  container, so uploads, the Chroma vector DB, and eval run history live in the
  same `data/` folder the manual setup uses — nothing is lost on
  `docker compose down` or a rebuild.
- **The local embedding model** (~130 MB, first run only) is cached in a named
  Docker volume, not `data/`, so it downloads once and survives restarts.
- **API keys are never baked into the image** — they're passed at container
  startup from `.env` via `env_file`.
- Run the eval suite inside the running backend container:
  ```bash
  docker compose exec backend python /app/eval/runner.py --label "docker"
  ```
- Stop everything with `docker compose down` (add `-v` to also drop the cached
  embedding model; your `data/` folder is untouched either way).

## Setup

Requires Python 3.11+ and Node 18+. Everything installs into the project folder —
nothing is installed globally, and `.env`/`data/`/PDFs are gitignored.

```bash
# 1. Backend: create a local venv and install dependencies
python -m venv .venv
# Windows:
.venv\Scripts\pip install -r backend/requirements.txt
# macOS/Linux:
.venv/bin/pip install -r backend/requirements.txt

# 2. Configure your API key
cp .env.example .env
# edit .env and add your OPENAI_API_KEY (or switch LLM_PROVIDER=anthropic and add
# ANTHROPIC_API_KEY)

# 3. Frontend dependencies
cd frontend && npm install && cd ..
```

## Running it

Two terminals, from the project root:

```bash
# Backend (from backend/)
cd backend
../.venv/Scripts/python.exe -m uvicorn app.main:app --reload   # Windows
# ../.venv/bin/python -m uvicorn app.main:app --reload          # macOS/Linux

# Frontend (from frontend/), in a second terminal
cd frontend
npm run dev
```

Open http://localhost:5173. First run downloads the local embedding model
(~130 MB, one-time).

### Uploading a manual

Go to the **Manuals** tab, drag and drop (or pick) a PDF. Ingestion runs in the
background with a progress bar — a ~300-400 page manual takes 1-3 minutes on CPU.
Once it's `ready`, it appears in the **Chat** tab's manual selector.

### Asking questions

Pick a manual in **Chat**, ask a question. Cited page numbers appear as clickable
chips under the answer — click one to see the actual manual page rendered as an
image. Each answer shows latency, cost, and which provider/model answered it.

## Running the eval suite

```bash
python eval/runner.py --manual-id <id> --label "my-run"
```

- `--manual-id` — omit to use the first ready manual
- `--top-k` — override retrieval top-k (default from `backend/app/config.py`)
- `--limit N` — cheap smoke run over the first N questions
- `--label` — name shown in the dashboard's run list

Runs are saved to `data/eval_runs/` and show up in the app's **Dashboard** tab
(trend chart across runs, per-run stat tiles, a sortable per-question table that
flags retrieval misses / low correctness / faithfulness issues). The test set
(`eval/testset.json`) is specific to the bundled BMW 330i manual — swap in your own
questions if you ingest a different manual.

See [RESULTS.md](RESULTS.md) for the chunk-size and top-k tuning results this
project's own eval suite produced, including a real failure mode it caught (tabular
PDF content) that tuning alone doesn't fix.

## Project structure

```
backend/app/       FastAPI app: ingestion, retrieval+generation, LLM provider layer
eval/               Test set, LLM-judge, run harness
frontend/src/       React chat UI, manuals upload, eval dashboard
data/                Local-only: uploads, Chroma vector DB, eval run history (gitignored)
```

## Tech stack

![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white)
![PyMuPDF](https://img.shields.io/badge/PyMuPDF-5C2D91?style=for-the-badge)
![fastembed](https://img.shields.io/badge/fastembed-4B8BBE?style=for-the-badge)
![Chroma](https://img.shields.io/badge/Chroma-FF6F00?style=for-the-badge)
![OpenAI](https://img.shields.io/badge/OpenAI-412991?style=for-the-badge&logo=openai&logoColor=white)
![Anthropic](https://img.shields.io/badge/Anthropic-D97757?style=for-the-badge&logo=anthropic&logoColor=white)

![React](https://img.shields.io/badge/React-20232A?style=for-the-badge&logo=react&logoColor=61DAFB)
![Vite](https://img.shields.io/badge/Vite-646CFF?style=for-the-badge&logo=vite&logoColor=white)
![Tailwind CSS](https://img.shields.io/badge/Tailwind%20CSS-06B6D4?style=for-the-badge&logo=tailwindcss&logoColor=white)
![Recharts](https://img.shields.io/badge/Recharts-22B5BF?style=for-the-badge)

Embeddings: `bge-small-en-v1.5` (local). Vector store: Chroma (local, file-based). LLM: OpenAI or Anthropic, bring your own key.

Built with:

![Claude Code](https://img.shields.io/badge/Claude%20Code-D97757?style=for-the-badge&logo=claude&logoColor=white)
