import re
import time
from typing import Any, Dict, List, Optional

from . import config, embeddings, llm, store

SYSTEM_PROMPT = """You are an assistant that answers questions about a car using ONLY \
the manual excerpts provided below. This information may be safety-critical, so accuracy \
matters more than being helpful.

Rules:
- Answer using ONLY facts stated in the provided excerpts. Do not use outside knowledge \
about cars in general, and do not guess or extrapolate.
- Whenever you state a fact from an excerpt, cite the page it came from inline like \
[p. 142]. If a fact spans multiple pages, cite each, e.g. [p. 142] [p. 143].
- If the excerpts do not contain enough information to answer the question, respond with \
exactly: "I couldn't find this in the manual." Do not attempt a partial or best-guess \
answer in that case.
- Be concise and direct."""

CITATION_RE = re.compile(r"\[p\.\s*(\d+)\]")
NOT_FOUND_MARKER = "couldn't find this in the manual"


def _build_user_prompt(question: str, chunks: List[Dict[str, Any]]) -> str:
    excerpt_blocks = []
    for i, c in enumerate(chunks, start=1):
        excerpt_blocks.append(f"[Excerpt {i} — page {c['pages']}]\n{c['text']}")
    excerpts = "\n\n".join(excerpt_blocks)
    return f"Manual excerpts:\n\n{excerpts}\n\nQuestion: {question}"


def retrieve(manual_id: str, question: str, top_k: int) -> List[Dict[str, Any]]:
    collection = store.get_or_create_collection(manual_id)
    vector = embeddings.embed_query(question)
    result = collection.query(query_embeddings=[vector], n_results=top_k)
    chunks = []
    docs = result["documents"][0]
    metas = result["metadatas"][0]
    dists = result["distances"][0]
    for doc, meta, dist in zip(docs, metas, dists):
        chunks.append(
            {
                "text": doc,
                "pages": meta["pages"],
                "distance": dist,
            }
        )
    return chunks


def _parse_pages(pages_field: str) -> List[int]:
    return [int(p) for p in pages_field.split(",") if p.strip().isdigit()]


def answer_question(
    manual_id: str, question: str, top_k: int = config.DEFAULT_TOP_K
) -> Dict[str, Any]:
    chunks = retrieve(manual_id, question, top_k)
    user_prompt = _build_user_prompt(question, chunks)

    start = time.perf_counter()
    result = llm.generate(SYSTEM_PROMPT, user_prompt, config.ANSWER_MAX_TOKENS)
    latency_ms = int((time.perf_counter() - start) * 1000)

    answer_text = result.text
    cited_pages = sorted({int(p) for p in CITATION_RE.findall(answer_text)})
    retrieved_pages: List[int] = sorted(
        {p for c in chunks for p in _parse_pages(c["pages"])}
    )
    not_found = NOT_FOUND_MARKER in answer_text.lower()

    usage = {"input_tokens": result.input_tokens, "output_tokens": result.output_tokens}
    cost_usd = config.calc_cost_usd(
        result.provider, result.model, usage["input_tokens"], usage["output_tokens"]
    )

    return {
        "answer": answer_text,
        "cited_pages": cited_pages,
        "retrieved_pages": retrieved_pages,
        "chunks": chunks,
        "latency_ms": latency_ms,
        "usage": usage,
        "cost_usd": cost_usd,
        "not_found": not_found,
        "provider": result.provider,
        "model": result.model,
    }
