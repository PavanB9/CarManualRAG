# CarManual RAG — Project Plan

## What this is
A RAG (Retrieval-Augmented Generation) system that lets a user ask natural-language
questions about their car and get accurate answers sourced directly from the actual
owner's manual PDF — with page citations — instead of generic/hallucinated AI answers.

Built to be **general-purpose**: a user can upload their own car manual PDF(s) — any
make/model/year, not hardcoded to one vehicle — plus their own API key, so this can be
published on GitHub and run by anyone for their own car(s). Test/dev manual: 2025 BMW
330i owner's manual (PDF, ~300 pages).

The differentiator vs. a basic "chat with PDF" clone: a built-in **eval suite** and
**telemetry dashboard** that measure retrieval accuracy, answer correctness, and
hallucination rate — treating this like a production AI system, not a demo toy.

---

## Test scope
Build and test against a single manual first (2025 BMW 330i, ~300 pages) — this is
enough to build and demo the full pipeline end-to-end. Testing against a second,
different manual is a stretch goal (see below), not a requirement for v1.

## Project isolation — keep everything local to the project folder
Don't install things globally on the machine — keep the project self-contained so it's
portable and anyone cloning the repo gets a clean, reproducible setup.
- [ ] Python dependencies: use a local virtual environment (`venv` or `poetry`) inside
      the project folder, not global `pip install`. Commit a `requirements.txt` (or
      `pyproject.toml`) so anyone can recreate it with one command.
- [ ] Node/frontend dependencies: `npm install` already installs into a local
      `node_modules/` folder by default — just make sure nothing gets installed with
      `-g` (global flag)
- [ ] Chroma vector DB: use its local file-based storage mode, stored inside the
      project folder (e.g. `./data/chroma/`), not a system-wide or hosted instance
- [ ] Uploaded manual PDFs + any generated data: stored inside the project folder
      (e.g. `./data/uploads/`), gitignored so they don't get committed
- [ ] Exception — genuinely system-level tools that aren't part of "your code" (e.g.
      Python itself, Node.js itself, Docker if used) are fine to have installed
      globally like normal dev tools — the local-only rule is for project dependencies
      and data, not the base runtime/tooling itself
- [ ] Add a `.gitignore` covering: venv folder, node_modules, `.env`, `./data/` (or
      wherever uploads/vector data live)

## Multi-manual upload design
Any user should be able to upload one or more of their own car manual PDFs (not just
the pre-loaded 330i one) and query them. This is what makes the tool actually
general-purpose/usable on GitHub by strangers, not a single-car demo.
- [ ] File upload UI (drag-and-drop or file picker) accepting PDF(s)
- [ ] Each uploaded manual gets its own namespace/collection in the vector DB (so a
      Honda manual's chunks never get mixed with a BMW manual's chunks)
- [ ] User picks which uploaded manual(s) to query against (or a "my car" selector once
      more than one is uploaded)
- [ ] Ingestion (chunk + embed + store) runs automatically on upload, with a progress
      indicator since a 300-page PDF will take a bit to process
- [ ] Uploaded PDFs + their vector data should be stored per-user/per-session, not
      globally shared, if this ever gets a real multi-user deployment

## API keys — Bring Your Own Key (BYOK) design
This project is meant to be published on GitHub and run by other people, so it should
NOT hardcode your personal API key anywhere in the code or repo.
- [ ] User enters their own Anthropic API key (and OpenAI key, if using OpenAI embeddings)
      into a settings field in the app UI
- [ ] Store the key **client-side only** — browser localStorage if it's a hosted web app,
      or a local `.env` file (gitignored) if it's run locally — never in a database, never
      committed to the repo, never logged
- [ ] All requests to Claude/OpenAI are made using the user's own key, so each user pays
      for their own usage — you are not on the hook for other people's API costs
- [ ] Add a `.env.example` file to the repo showing what keys are needed, with no real
      values, so anyone cloning the repo knows what to set up
- [ ] README should clearly explain: "bring your own Anthropic API key, get one at
      console.anthropic.com" — standard pattern for open-source AI tools

## Tech stack
- **Backend**: Python, FastAPI
- **PDF parsing**: PyMuPDF (fitz) — handles text + can extract page images for diagrams
- **Chunking**: split by section/page, ~500-800 tokens per chunk, with overlap
- **Embeddings**: OpenAI `text-embedding-3-small` or a local model (e.g. `bge-small`) if
  you want zero API cost during dev
- **Vector DB**: Chroma (local, zero-setup, file-based — good for a portfolio project)
- **Generation**: Claude API (Sonnet)
- **Frontend**: React + Tailwind — chat interface + eval dashboard
- **Eval judging**: Claude API as an automated grader against your test set

---

## Build phases

### Phase 1 — Core ingestion pipeline
- [ ] Script to load a PDF, extract text per page (keep page numbers attached to chunks)
- [ ] Chunk the text (with overlap so context isn't cut mid-sentence)
- [ ] Generate embeddings for each chunk
- [ ] Store chunks + embeddings + page metadata in Chroma
- [ ] Sanity check: manually query a few known facts and confirm the right chunk retrieves

### Phase 2 — Retrieval + generation (basic RAG loop)
- [ ] API endpoint: takes a question, embeds it, retrieves top-k relevant chunks
- [ ] Pass retrieved chunks + question to Claude with a system prompt that enforces:
      "only answer using the provided manual excerpts, cite the page number, say
      'not found in manual' if the answer isn't in the retrieved context"
- [ ] Return answer + source page numbers + (optionally) the raw chunk text

### Phase 3 — Frontend chat UI
- [ ] Simple chat interface — ask a question, see the answer + cited page(s)
- [ ] Click a citation to see the actual manual page (render as image via PyMuPDF)
- [ ] Car selector (even if only one manual is loaded for now, structure it as if more
      could be added later — this matters for the "general-purpose" story)

### Phase 4 — Eval suite (the differentiator — don't skip this)
- [ ] Build a test set: 30-50 real questions about the 330i with known correct answers
      pulled directly from the manual (e.g. tire pressure spec, oil type, warning light
      meanings, infotainment steps, maintenance intervals)
- [ ] Script that runs the full test set through your RAG pipeline automatically
- [ ] Metrics to compute per question:
      - **Retrieval hit rate**: did the correct page get retrieved at all?
      - **Answer correctness**: use Claude as a judge — compare generated answer to the
        known-correct answer, score match
      - **Faithfulness**: does the answer contain any claim NOT supported by the
        retrieved chunks? (critical for car safety info — flag this explicitly)
      - **Latency** and **cost per query**
- [ ] Store eval run results (timestamp, scores, config used) so you can compare runs

### Phase 5 — Telemetry dashboard
- [ ] Dashboard page showing: eval score trend over time, per-question breakdown (which
      questions fail), average latency, average cost per query
- [ ] This turns "I built a RAG chatbot" into "I built and *measured* a RAG system"

### Phase 6 — Iterate using your own evals
- [ ] Try at least 2 variations and show the eval score change, e.g.:
      - chunk size 500 vs 800 tokens
      - top-k = 3 vs top-k = 6 retrieved chunks
      - adding hybrid search (keyword + vector) vs vector-only
- [ ] Document the before/after numbers — this becomes your strongest resume bullet

---

## Stretch goals (only after core + evals are solid)
- [ ] Support multiple manuals, let user pick car make/model/year
- [ ] Extract and show actual diagrams/images from the manual, not just text
- [ ] Voice input for hands-free "under the hood" use case
- [ ] Confidence score shown to user (low confidence = "I'm not fully sure, check page X")

---

## Resume bullet target
"Built a RAG pipeline over 300-page technical manuals with automated evals (retrieval
accuracy, answer correctness, faithfulness) and a live telemetry dashboard; improved
answer accuracy from X% to Y% by tuning chunking and retrieval strategy."
→ Fill in real X/Y numbers once evals are running — that's the whole point.

---

## Notes for Claude Code
- Start with Phase 1-2 only, get a working end-to-end query before touching the frontend
- Use the 2025 330i manual PDF as the first test document
- Keep the eval test set as a separate JSON/CSV file (question, correct_answer, source_page)
  so it's reusable across iterations
- Prioritize the "faithfulness" metric carefully — this is what makes the eval story
  compelling for a car-safety-relevant use case
