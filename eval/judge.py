import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, List

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from app import config, llm  # noqa: E402

_JSON_BLOCK_RE = re.compile(r"\{.*\}", re.DOTALL)

CORRECTNESS_SYSTEM = """You are grading an AI assistant's answer to a question about a \
car owner's manual. Compare the generated answer to the known-correct reference answer.

Score:
- 1.0 = fully correct, matches the key facts in the reference answer
- 0.5 = partially correct (right idea but missing/wrong detail, or hedges when it \
shouldn't)
- 0.0 = wrong, or the assistant said it couldn't find the answer when the reference \
answer shows it should have been findable

Respond with ONLY a JSON object, no other text: {"score": <0|0.5|1>, "reasoning": "<one \
concise sentence>"}"""

FAITHFULNESS_SYSTEM = """You are checking an AI assistant's answer for faithfulness to \
the source material it was given. You will see the manual excerpts the assistant had \
access to, and the answer it produced.

List any factual claims in the answer that are NOT supported by the excerpts (fabricated \
or extrapolated beyond what the excerpts state). If the answer correctly says it couldn't \
find the information, that is faithful (no unsupported claims).

Respond with ONLY a JSON object, no other text: {"faithful": <true|false>, "issues": \
[<short strings, empty list if none>]}"""


def _extract_json(text: str) -> Dict[str, Any]:
    match = _JSON_BLOCK_RE.search(text)
    if not match:
        raise ValueError(f"Judge did not return JSON: {text!r}")
    return json.loads(match.group(0))


def judge_correctness(
    question: str, correct_answer: str, generated_answer: str
) -> Dict[str, Any]:
    user_prompt = (
        f"Question: {question}\n\n"
        f"Reference (correct) answer: {correct_answer}\n\n"
        f"Generated answer: {generated_answer}"
    )
    result = llm.generate(CORRECTNESS_SYSTEM, user_prompt, config.JUDGE_MAX_TOKENS)
    cost = config.calc_cost_usd(
        result.provider, result.model, result.input_tokens, result.output_tokens
    )
    try:
        parsed = _extract_json(result.text)
        return {
            "score": float(parsed["score"]),
            "reasoning": str(parsed.get("reasoning", "")),
            "cost_usd": cost,
        }
    except (ValueError, KeyError, TypeError):
        return {
            "score": 0.0,
            "reasoning": f"Judge output unparseable: {result.text[:200]!r}",
            "cost_usd": cost,
        }


def judge_faithfulness(
    generated_answer: str, retrieved_chunks: List[Dict[str, Any]]
) -> Dict[str, Any]:
    excerpts = "\n\n".join(
        f"[Excerpt {i} — page {c['pages']}]\n{c['text']}"
        for i, c in enumerate(retrieved_chunks, start=1)
    )
    user_prompt = f"Manual excerpts:\n\n{excerpts}\n\nAssistant's answer: {generated_answer}"
    result = llm.generate(FAITHFULNESS_SYSTEM, user_prompt, config.JUDGE_MAX_TOKENS)
    cost = config.calc_cost_usd(
        result.provider, result.model, result.input_tokens, result.output_tokens
    )
    try:
        parsed = _extract_json(result.text)
        return {
            "faithful": bool(parsed["faithful"]),
            "issues": list(parsed.get("issues", [])),
            "cost_usd": cost,
        }
    except (ValueError, KeyError, TypeError):
        return {
            "faithful": False,
            "issues": [f"Judge output unparseable: {result.text[:200]!r}"],
            "cost_usd": cost,
        }
