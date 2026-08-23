# Eval Results

All runs use the same 40-question test set (`eval/testset.json`), built from the real
text of the 2025 BMW 330i owner's manual, against `gpt-5.6-luna` for both generation
and judging. Full run JSON lives in `data/eval_runs/` (gitignored — reproduce with
`python eval/runner.py`).

## Runs

| Label | Chunk size | top_k | Retrieval hit | Correctness | Faithfulness | Refusal acc. | Avg cost/query | Run cost |
|---|---|---|---|---|---|---|---|---|
| baseline-chunk2400-topk5 | ~600 tok (2400 chars) | 5 | 97.2% | 0.94 | 95.0% | 100% | $0.00068 | $0.0598 |
| **chunk500-topk5 (winner)** | **~500 tok (2000 chars)** | **5** | **100%** | **0.95** | **100%** | **100%** | **$0.00058** | **$0.0515** |
| chunk800-topk5 | ~800 tok (3200 chars) | 5 | 100% | 0.90 | 92.5% | 100% | $0.00086 | $0.0739 |
| chunk500-topk3 | ~500 tok | 3 | 100% | 0.94 | 97.5% | 100% | $0.00040 | $0.0372 |
| chunk500-topk6 | ~500 tok | 6 | 100% | 0.95 | 92.5% | 100% | $0.00069 | $0.0605 |

Retrieval hit rate and refusal accuracy exclude/include, respectively, the 4
deliberately out-of-manual questions in the test set (refusal accuracy = correctly
saying "not found" on those 4).

## What changed, and why

**Chunk size 2400 → 2000 chars (~600 → ~500 tokens) improved every metric and cut
cost.** Smaller chunks fixed two concrete failures present at baseline:
- `ss-02` ("How many seat belts does the vehicle have?") went from a flat refusal
  ("I couldn't find this in the manual") to the correct answer. At 2400 chars the
  fact was diluted inside a larger chunk dominated by unrelated seat-belt-usage
  text; at 2000 chars the answer-bearing sentence became a larger fraction of its
  chunk and won retrieval more reliably.
- `wl-08` (Emergency Stop Assistant) stopped tripping the faithfulness judge — the
  smaller chunk kept the icon-meaning sentence intact without adjacent text the
  judge could read as unsupported extrapolation.

**Chunk size 2400 → 3200 chars (~800 tokens) made things worse**, not better:
correctness dropped to 0.90 and faithfulness to 92.5%, the worst of any config
tested, while cost per query went *up* (more tokens sent to the model per chunk).
Bigger chunks pull in more surrounding noise — tables and unrelated adjacent
sections — which both increases hallucination risk and costs more. The intuition
that "more context = safer" did not hold here.

**top_k: 5 beat both 3 and 6, on the winning chunk size.** top_k=3 is 28% cheaper
per query but drops faithfulness from 100% to 97.5% (occasionally missing a needed
excerpt). top_k=6 doesn't improve correctness over top_k=5 and actively hurts
faithfulness (92.5%) by handing the model more chances to pick up an adjacent-but-
irrelevant fact — the same "more context isn't free" pattern as the chunk-size
experiment. top_k=5 is the sweet spot for this manual.

## Known limitation the eval suite caught (and didn't fix)

**`tw-05`** ("What is the cold tire pressure for the standard 225/45 R18 95Y XL
tires...?") fails in every configuration tested (correctness 0.0). The manual's
tire-pressure table is extracted by PyMuPDF as a long run of numbers with the
column headers ("Pressure specifications in bar/PSI" / "...with cold tires")
stated once at the top and never repeated per row. The model consistently answers
with a real number from the table — just the wrong row/column — so the
faithfulness judge doesn't flag it as fabrication, but the correctness judge
correctly flags it as wrong. This is a genuine, reproducible weakness of naive
text-based chunking on tabular PDF content, not a prompt or retrieval-top_k issue:
none of the 5 configurations tested fix it. A real fix would need table-aware
extraction (e.g. detecting table regions and serializing each row with its headers
inline) — out of scope for this pass, but exactly the kind of failure this eval
suite exists to surface before it reaches a user relying on it for a safety-relevant
spec.

## Final configuration

The app's default ingestion config (`backend/app/config.py`) is set to the winning
values: `DEFAULT_CHUNK_CHARS=2000`, `DEFAULT_CHUNK_OVERLAP_CHARS=330`,
`DEFAULT_TOP_K=5`.
