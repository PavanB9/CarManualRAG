import json
import re

from fastapi import APIRouter, HTTPException

from .. import config

router = APIRouter(prefix="/api/eval", tags=["eval"])

_RUN_ID_RE = re.compile(r"^[A-Za-z0-9_-]+$")


def _run_files():
    return sorted(config.EVAL_RUNS_DIR.glob("*.json"))


@router.get("/runs")
def list_runs():
    runs = []
    for path in _run_files():
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        runs.append(
            {
                "id": path.stem,
                "label": data.get("label"),
                "timestamp": data.get("timestamp"),
                "config": data.get("config"),
                "aggregates": data.get("aggregates"),
            }
        )
    return runs


@router.get("/runs/{run_id}")
def get_run(run_id: str):
    if not _RUN_ID_RE.match(run_id):
        raise HTTPException(404, "Eval run not found.")
    path = config.EVAL_RUNS_DIR / f"{run_id}.json"
    if not path.exists():
        raise HTTPException(404, "Eval run not found.")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)
