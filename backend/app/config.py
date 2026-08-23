from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
PROJECT_ROOT = BACKEND_DIR.parent
DATA_DIR = PROJECT_ROOT / "data"
UPLOADS_DIR = DATA_DIR / "uploads"
CHROMA_DIR = DATA_DIR / "chroma"
EVAL_RUNS_DIR = DATA_DIR / "eval_runs"
MANUALS_REGISTRY_PATH = DATA_DIR / "manuals.json"

for d in (DATA_DIR, UPLOADS_DIR, CHROMA_DIR, EVAL_RUNS_DIR):
    d.mkdir(parents=True, exist_ok=True)

EMBEDDING_MODEL_ID = "BAAI/bge-small-en-v1.5"
BGE_QUERY_PREFIX = "Represent this sentence for searching relevant passages: "

# ~1 token ≈ 4 chars; chunk size and top_k are the eval-selected winners — see
# RESULTS.md for the comparison against chunk~600/800 tokens and top_k 3/6.
DEFAULT_CHUNK_CHARS = 2000
DEFAULT_CHUNK_OVERLAP_CHARS = 330
DEFAULT_TOP_K = 5

MAX_UPLOAD_BYTES = 50 * 1024 * 1024  # 50 MB

ANSWER_MAX_TOKENS = 2048
JUDGE_MAX_TOKENS = 1024

# $/million tokens (input, output), keyed by (provider, model). Edit here if you
# change models or OpenAI updates Luna's promotional pricing.
PRICING: dict[tuple[str, str], tuple[float, float]] = {
    ("openai", "gpt-5.6-luna"): (0.20, 1.20),
    ("anthropic", "claude-sonnet-5"): (3.00, 15.00),
}
DEFAULT_PRICE_PER_MTOK = (1.00, 3.00)  # fallback if model isn't in the table above


def calc_cost_usd(
    provider: str, model: str, input_tokens: int, output_tokens: int
) -> float:
    price_in, price_out = PRICING.get((provider, model), DEFAULT_PRICE_PER_MTOK)
    return (input_tokens / 1_000_000) * price_in + (output_tokens / 1_000_000) * price_out
