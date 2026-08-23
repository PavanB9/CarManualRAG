import json
import re
import threading
import uuid
from datetime import datetime, timezone
from functools import lru_cache
from typing import Any, Dict, List, Optional

import chromadb

from . import config

_registry_lock = threading.Lock()


@lru_cache(maxsize=1)
def get_chroma_client() -> chromadb.ClientAPI:
    return chromadb.PersistentClient(path=str(config.CHROMA_DIR))


def _read_registry() -> List[Dict[str, Any]]:
    if not config.MANUALS_REGISTRY_PATH.exists():
        return []
    with open(config.MANUALS_REGISTRY_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def _write_registry(manuals: List[Dict[str, Any]]) -> None:
    with open(config.MANUALS_REGISTRY_PATH, "w", encoding="utf-8") as f:
        json.dump(manuals, f, indent=2)


def slugify(title: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
    return slug or "manual"


def create_manual_entry(
    title: str,
    filename: str,
    chunk_chars: int,
    chunk_overlap_chars: int,
    experiment: bool = False,
) -> Dict[str, Any]:
    manual_id = f"{slugify(title)}-{uuid.uuid4().hex[:8]}"
    entry = {
        "id": manual_id,
        "title": title,
        "filename": filename,
        "num_pages": 0,
        "num_chunks": 0,
        "chunk_chars": chunk_chars,
        "chunk_overlap_chars": chunk_overlap_chars,
        "embedding_model": config.EMBEDDING_MODEL_ID,
        "status": "processing",
        "progress": 0,
        "error_message": None,
        "experiment": experiment,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    with _registry_lock:
        manuals = _read_registry()
        manuals.append(entry)
        _write_registry(manuals)
    return entry


def update_manual(manual_id: str, **updates: Any) -> None:
    with _registry_lock:
        manuals = _read_registry()
        for m in manuals:
            if m["id"] == manual_id:
                m.update(updates)
                break
        _write_registry(manuals)


def list_manuals() -> List[Dict[str, Any]]:
    return _read_registry()


def get_manual(manual_id: str) -> Optional[Dict[str, Any]]:
    for m in _read_registry():
        if m["id"] == manual_id:
            return m
    return None


def delete_manual(manual_id: str) -> bool:
    with _registry_lock:
        manuals = _read_registry()
        remaining = [m for m in manuals if m["id"] != manual_id]
        found = len(remaining) != len(manuals)
        _write_registry(remaining)
    if found:
        try:
            get_chroma_client().delete_collection(collection_name(manual_id))
        except Exception:
            pass
    return found


def collection_name(manual_id: str) -> str:
    return f"manual_{manual_id.replace('-', '_')}"


def get_or_create_collection(manual_id: str):
    return get_chroma_client().get_or_create_collection(
        name=collection_name(manual_id),
        metadata={"hnsw:space": "cosine"},
    )
