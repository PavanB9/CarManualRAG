from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from .. import config, llm, rag, store

router = APIRouter(prefix="/api", tags=["query"])


class QueryRequest(BaseModel):
    manual_id: str
    question: str
    top_k: int | None = None


@router.post("/query")
def query(req: QueryRequest):
    entry = store.get_manual(req.manual_id)
    if not entry:
        raise HTTPException(404, "Manual not found.")
    if entry["status"] != "ready":
        raise HTTPException(409, f"Manual is not ready (status: {entry['status']}).")
    if not req.question.strip():
        raise HTTPException(400, "Question cannot be empty.")

    top_k = req.top_k or config.DEFAULT_TOP_K
    try:
        return rag.answer_question(req.manual_id, req.question, top_k=top_k)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(502, llm.translate_llm_error(exc)) from exc
