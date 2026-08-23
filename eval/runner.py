import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from app import config, llm, rag, store  # noqa: E402

import judge  # noqa: E402

TESTSET_PATH = Path(__file__).resolve().parent / "testset.json"


def load_testset(limit: int | None = None):
    with open(TESTSET_PATH, "r", encoding="utf-8") as f:
        questions = json.load(f)
    return questions[:limit] if limit else questions


def pick_manual_id(manual_id: str | None) -> str:
    if manual_id:
        return manual_id
    manuals = [m for m in store.list_manuals() if m["status"] == "ready"]
    if not manuals:
        raise SystemExit("No ready manuals found. Ingest one first.")
    return manuals[0]["id"]


def run(manual_id: str, top_k: int, label: str | None, limit: int | None) -> dict:
    questions = load_testset(limit)
    provider = llm.get_provider()
    model = llm.get_model_id(provider)

    rows = []
    for i, q in enumerate(questions, start=1):
        print(f"[{i}/{len(questions)}] {q['id']}: {q['question'][:70]}")
        result = rag.answer_question(manual_id, q["question"], top_k=top_k)

        source_pages = set(q.get("source_pages", []))
        retrieved_pages = set(result["retrieved_pages"])
        is_out_of_manual = q["category"] == "out_of_manual"
        retrieval_hit = (
            None if is_out_of_manual else bool(source_pages & retrieved_pages)
        )

        correctness = judge.judge_correctness(
            q["question"], q["correct_answer"], result["answer"]
        )
        faithfulness = judge.judge_faithfulness(result["answer"], result["chunks"])

        rows.append(
            {
                "id": q["id"],
                "question": q["question"],
                "category": q["category"],
                "correct_answer": q["correct_answer"],
                "source_pages": sorted(source_pages),
                "generated_answer": result["answer"],
                "retrieval_hit": retrieval_hit,
                "retrieved_pages": sorted(retrieved_pages),
                "not_found": result["not_found"],
                "correctness": correctness["score"],
                "correctness_reasoning": correctness["reasoning"],
                "faithful": faithfulness["faithful"],
                "faithfulness_issues": faithfulness["issues"],
                "latency_ms": result["latency_ms"],
                "query_cost_usd": result["cost_usd"],
                "judge_cost_usd": correctness["cost_usd"] + faithfulness["cost_usd"],
            }
        )

    answerable = [r for r in rows if r["retrieval_hit"] is not None]
    out_of_manual = [r for r in rows if r["retrieval_hit"] is None]

    aggregates = {
        "num_questions": len(rows),
        "retrieval_hit_rate": (
            sum(1 for r in answerable if r["retrieval_hit"]) / len(answerable)
            if answerable
            else None
        ),
        "mean_correctness": sum(r["correctness"] for r in rows) / len(rows),
        "faithfulness_rate": sum(1 for r in rows if r["faithful"]) / len(rows),
        "refusal_accuracy": (
            sum(1 for r in out_of_manual if r["not_found"]) / len(out_of_manual)
            if out_of_manual
            else None
        ),
        "mean_latency_ms": sum(r["latency_ms"] for r in rows) / len(rows),
        "mean_query_cost_usd": sum(r["query_cost_usd"] for r in rows) / len(rows),
        "mean_judge_cost_usd": sum(r["judge_cost_usd"] for r in rows) / len(rows),
        "total_cost_usd": sum(r["query_cost_usd"] + r["judge_cost_usd"] for r in rows),
    }

    manual = store.get_manual(manual_id)
    run_data = {
        "label": label,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "config": {
            "manual_id": manual_id,
            "manual_title": manual["title"] if manual else manual_id,
            "top_k": top_k,
            "chunk_chars": manual.get("chunk_chars") if manual else None,
            "chunk_overlap_chars": manual.get("chunk_overlap_chars") if manual else None,
            "provider": provider,
            "model": model,
            "embedding_model": config.EMBEDDING_MODEL_ID,
        },
        "aggregates": aggregates,
        "questions": rows,
    }
    return run_data


def print_summary(run_data: dict) -> None:
    agg = run_data["aggregates"]
    print("\n=== Summary ===")
    print(f"Questions:          {agg['num_questions']}")
    hit = agg["retrieval_hit_rate"]
    print(f"Retrieval hit rate: {hit:.1%}" if hit is not None else "Retrieval hit rate: n/a")
    print(f"Mean correctness:   {agg['mean_correctness']:.2f} (0-1 scale)")
    print(f"Faithfulness rate:  {agg['faithfulness_rate']:.1%}")
    ref = agg["refusal_accuracy"]
    print(f"Refusal accuracy:   {ref:.1%}" if ref is not None else "Refusal accuracy:   n/a")
    print(f"Mean latency:       {agg['mean_latency_ms']:.0f} ms")
    print(f"Mean query cost:    ${agg['mean_query_cost_usd']:.5f}")
    print(f"Mean judge cost:    ${agg['mean_judge_cost_usd']:.5f}")
    print(f"Total run cost:     ${agg['total_cost_usd']:.4f}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the eval test set against the RAG pipeline.")
    parser.add_argument("--manual-id", default=None)
    parser.add_argument("--top-k", type=int, default=config.DEFAULT_TOP_K)
    parser.add_argument("--label", default=None)
    parser.add_argument("--limit", type=int, default=None)
    args = parser.parse_args()

    manual_id = pick_manual_id(args.manual_id)
    start = time.time()
    run_data = run(manual_id, args.top_k, args.label, args.limit)
    print(f"\nRun completed in {time.time() - start:.1f}s")
    print_summary(run_data)

    config.EVAL_RUNS_DIR.mkdir(parents=True, exist_ok=True)
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_path = config.EVAL_RUNS_DIR / f"{run_id}.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(run_data, f, indent=2)
    print(f"\nSaved to {out_path}")


if __name__ == "__main__":
    main()
