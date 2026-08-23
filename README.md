# CarManualRAG

Ask natural-language questions about your car and get answers sourced directly from
your own owner's manual PDF — with page citations you can click to see the actual
page — instead of generic or hallucinated AI answers.

Upload any car manual PDF (not just BMW), ask questions in a chat UI, and click a
citation to see the exact manual page the answer came from. Built with a real eval
suite (retrieval accuracy, answer correctness, faithfulness) and a telemetry
dashboard, so this is measured, not just demoed — see [RESULTS.md](RESULTS.md) for
the tuning experiments and their numbers.

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

FastAPI · PyMuPDF · fastembed (`bge-small-en-v1.5`, local) · Chroma (local,
file-based) · OpenAI / Anthropic (BYOK) · React + Vite + Tailwind + Recharts
