# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

A RAG system: upload a car owner's manual PDF, ask questions, get answers grounded
in the manual with clickable page citations. Includes a real eval suite (retrieval
hit rate, LLM-judged correctness, LLM-judged faithfulness) and a telemetry
dashboard — see `RESULTS.md` for the chunk-size/top-k tuning experiments and their
numbers, and `README.md` for the user-facing setup/usage guide.

## Commands

Backend (from `backend/`, using the project-root `.venv`):
```bash
../.venv/Scripts/python.exe -m uvicorn app.main:app --reload   # Windows
../.venv/bin/python -m uvicorn app.main:app --reload            # macOS/Linux
```

Frontend (from `frontend/`): `npm run dev` (dev server on :5173, proxies `/api` to
:8000), `npm run build` (`tsc -b && vite build` — this is the type-check), `npm run
lint` (oxlint). No test suite exists in either half of the app.

Ingest a manual from the CLI (from `backend/`), bypassing the upload endpoint —
useful for testing chunk-size variants without going through the UI:
```bash
../.venv/Scripts/python.exe -m app.ingest <pdf_path> --title "..." \
  [--chunk-chars N] [--overlap-chars N] [--collection-suffix name] [--experiment] \
  [--sanity-check]   # runs a few known-fact queries against the ingested manual
```

Run the eval suite (from project root):
```bash
.venv/Scripts/python.exe eval/runner.py [--manual-id ID] [--top-k N] [--label "..."] [--limit N]
```
Omitting `--manual-id` uses the first `ready` manual in the registry. Runs are
saved to `data/eval_runs/<timestamp>.json` and appear in the app's Dashboard tab.

## Architecture

**Provider-agnostic LLM layer** (`backend/app/llm.py`): `LLM_PROVIDER` env var
(`openai` or `anthropic`) selects the backend; `llm.generate(system, prompt,
max_tokens)` returns a uniform `GenerationResult` (text + usage + provider + model)
regardless of which provider answered. Both `rag.py` and `eval/judge.py` call this
one function — neither has provider-specific branches. Pricing is a
`(provider, model) -> (price_in, price_out)` table in `config.py`, so cost
calculation also stays provider-agnostic. When adding a new provider, add a
`_generate_<provider>()` function following the existing two, wire it into
`generate()`'s dispatch, and add its pricing row.

**Ingestion pipeline** (`backend/app/ingest.py`): PDF → per-page text (PyMuPDF) →
char-based sliding-window chunking that's page-aware (each chunk records which
manual page(s) it spans, via a char-offset → page-number map built during
extraction — this is what makes citations possible later) → batched local
embedding (`fastembed`, `bge-small-en-v1.5`, no API call) → one Chroma collection
per manual (`store.get_or_create_collection`). Ingestion runs as a FastAPI
`BackgroundTask` on upload; progress (0-100) and status (`processing`/`ready`/
`error`) are written to the manual's registry entry as it goes, which is what the
frontend polls to drive the progress bar.

**Manual registry** (`backend/app/store.py`): not a database — a flat JSON file at
`data/manuals.json`, guarded by a `threading.Lock` for concurrent read/write during
background ingestion. `store.py` is the only module that touches this file or the
Chroma client directly; everything else goes through its functions.

**RAG query** (`backend/app/rag.py`): `answer_question()` retrieves top-k chunks,
builds a prompt with a system prompt that requires the model to answer only from
the excerpts, cite pages inline as `[p. N]`, and say exactly "I couldn't find this
in the manual" when it can't answer — that exact phrase is the `NOT_FOUND_MARKER`
regex-matched elsewhere (eval refusal-accuracy scoring, frontend not-found
handling), so don't change the wording without updating both. The response
distinguishes `cited_pages` (parsed from `[p. N]` in the answer text) from
`retrieved_pages` (pages of the chunks that were retrieved) — the eval suite's
retrieval-hit-rate metric uses `retrieved_pages`, not what the model chose to cite.

**Eval suite** (`eval/`): `testset.json` is hand-curated against the actual 330i
manual text (every `correct_answer`/`source_pages` pair was verified against the
real PDF, not generated) — if you regenerate or extend it for a different manual,
verify facts against the manual's extracted text the same way, not from general
car knowledge. `judge.py` prompts the active LLM provider to return a JSON verdict
and regex-extracts the first `{...}` block from the response (providers sometimes
wrap JSON in prose despite instructions). `runner.py` imports `backend/app` modules
directly rather than going through HTTP, so it can run without the FastAPI server
up. Out-of-manual test questions (`category: "out_of_manual"`) are scored
separately as `refusal_accuracy` rather than folded into `retrieval_hit_rate`,
since there's no source page to hit.

**Frontend** (`frontend/src/`): three tabs (Chat/Manuals/Dashboard) as plain
`useState` in `App.tsx` — no router library. `api.ts` is a thin fetch wrapper over
the backend; `types.ts` mirrors the backend's response shapes by hand (no shared
schema/codegen between the two). The dev server proxies `/api` to `localhost:8000`
(`vite.config.ts`), so CORS only matters for non-Vite-proxied access.

**Data isolation**: everything under `data/` (uploads, Chroma DB, eval run history,
the manuals registry) is gitignored, as are all `*.pdf` files anywhere in the repo
— the bundled BMW manual PDF at the repo root is local-only, never committed.
`backend/app/config.py` is the single source of truth for default chunk
size/overlap/top-k and file-system paths; its current defaults were chosen by the
eval suite itself (see `RESULTS.md`) rather than picked upfront.
