import argparse
import shutil
import sys
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple

import pymupdf as fitz

from . import config, embeddings, store

MIN_EXTRACTED_CHARS = 1000

ProgressFn = Optional[Callable[[int], None]]


def extract_pages(pdf_path: Path) -> List[str]:
    doc = fitz.open(pdf_path)
    try:
        return [page.get_text("text") for page in doc]
    finally:
        doc.close()


def chunk_pages(
    pages: List[str],
    chunk_chars: int = config.DEFAULT_CHUNK_CHARS,
    overlap_chars: int = config.DEFAULT_CHUNK_OVERLAP_CHARS,
) -> List[Dict]:
    """Concatenate pages and slide a char window across them, tracking which
    1-indexed page(s) each chunk spans."""
    full_text = ""
    page_bounds: List[Tuple[int, int, int]] = []  # (start, end, page_num)
    for i, text in enumerate(pages, start=1):
        start = len(full_text)
        full_text += text + "\n"
        page_bounds.append((start, len(full_text), i))

    def pages_for_span(start: int, end: int) -> List[int]:
        return [p for (s, e, p) in page_bounds if s < end and e > start]

    chunks: List[Dict] = []
    n = len(full_text)
    if n == 0:
        return chunks

    start = 0
    step = max(chunk_chars - overlap_chars, 1)
    while start < n:
        end = min(start + chunk_chars, n)
        text = full_text[start:end].strip()
        if text:
            span_pages = pages_for_span(start, end) or [1]
            chunks.append({"text": text, "pages": span_pages})
        if end >= n:
            break
        start += step

    return chunks


def ingest_manual(
    manual_id: str,
    pdf_path: Path,
    chunk_chars: int = config.DEFAULT_CHUNK_CHARS,
    overlap_chars: int = config.DEFAULT_CHUNK_OVERLAP_CHARS,
    on_progress: ProgressFn = None,
) -> None:
    def report(pct: int) -> None:
        store.update_manual(manual_id, progress=pct)
        if on_progress:
            on_progress(pct)

    try:
        report(5)
        pages = extract_pages(pdf_path)
        total_chars = sum(len(p) for p in pages)
        if total_chars < MIN_EXTRACTED_CHARS:
            store.update_manual(
                manual_id,
                status="error",
                error_message=(
                    "Could not extract meaningful text from this PDF. It may be a "
                    "scanned/image-only document, which is not supported."
                ),
            )
            return

        report(20)
        chunks = chunk_pages(pages, chunk_chars, overlap_chars)
        if not chunks:
            store.update_manual(
                manual_id, status="error", error_message="No text chunks produced."
            )
            return

        report(30)
        collection = store.get_or_create_collection(manual_id)

        batch_size = 64
        for i in range(0, len(chunks), batch_size):
            batch = chunks[i : i + batch_size]
            texts = [c["text"] for c in batch]
            vectors = embeddings.embed_passages(texts, batch_size=batch_size)
            ids = [f"{manual_id}-{i + j}" for j in range(len(batch))]
            metadatas = [
                {
                    "manual_id": manual_id,
                    "chunk_index": i + j,
                    "pages": ",".join(str(p) for p in c["pages"]),
                }
                for j, c in enumerate(batch)
            ]
            collection.add(
                ids=ids, embeddings=vectors, documents=texts, metadatas=metadatas
            )
            pct = 30 + int(60 * (i + len(batch)) / len(chunks))
            report(min(pct, 90))

        store.update_manual(
            manual_id,
            status="ready",
            progress=100,
            num_pages=len(pages),
            num_chunks=len(chunks),
        )
    except Exception as exc:  # noqa: BLE001 - surface any failure to the registry
        store.update_manual(manual_id, status="error", error_message=str(exc))
        raise


def sanity_check(manual_id: str, queries: List[str]) -> None:
    collection = store.get_or_create_collection(manual_id)
    for q in queries:
        vector = embeddings.embed_query(q)
        result = collection.query(query_embeddings=[vector], n_results=3)
        print(f"\nQuery: {q!r}")
        docs = result["documents"][0]
        metas = result["metadatas"][0]
        dists = result["distances"][0]
        for doc, meta, dist in zip(docs, metas, dists):
            preview = doc[:160].replace("\n", " ").encode("ascii", "replace").decode()
            print(f"  page(s) {meta['pages']}  dist={dist:.4f}  {preview!r}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest a car manual PDF into Chroma.")
    parser.add_argument("pdf_path", type=Path)
    parser.add_argument("--title", required=True)
    parser.add_argument("--chunk-chars", type=int, default=config.DEFAULT_CHUNK_CHARS)
    parser.add_argument(
        "--overlap-chars", type=int, default=config.DEFAULT_CHUNK_OVERLAP_CHARS
    )
    parser.add_argument("--collection-suffix", default="")
    parser.add_argument(
        "--experiment", action="store_true", help="Flag this ingest as an experiment run"
    )
    parser.add_argument(
        "--sanity-check", action="store_true", help="Run known-fact queries after ingest"
    )
    args = parser.parse_args()

    if not args.pdf_path.exists():
        print(f"File not found: {args.pdf_path}", file=sys.stderr)
        sys.exit(1)

    title = args.title + (f" ({args.collection_suffix})" if args.collection_suffix else "")
    entry = store.create_manual_entry(
        title=title,
        filename=args.pdf_path.name,
        chunk_chars=args.chunk_chars,
        chunk_overlap_chars=args.overlap_chars,
        experiment=args.experiment,
    )
    manual_id = entry["id"]

    dest = config.UPLOADS_DIR / f"{manual_id}.pdf"
    shutil.copy(args.pdf_path, dest)

    print(f"Ingesting {args.pdf_path} as manual_id={manual_id!r} ...")
    ingest_manual(
        manual_id, dest, chunk_chars=args.chunk_chars, overlap_chars=args.overlap_chars
    )

    entry = store.get_manual(manual_id)
    print(f"Status: {entry['status']}")
    if entry["status"] != "ready":
        print(f"Error: {entry.get('error_message')}", file=sys.stderr)
        sys.exit(1)
    print(f"Pages: {entry['num_pages']}  Chunks: {entry['num_chunks']}")

    if args.sanity_check:
        sanity_check(
            manual_id,
            [
                "What is the recommended tire pressure?",
                "What type of engine oil should be used?",
                "What does the engine warning light mean?",
                "How do I pair a phone with the infotainment system?",
            ],
        )


if __name__ == "__main__":
    main()
