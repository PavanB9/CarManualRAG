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

MODEL_ID = "claude-sonnet-5"
EMBEDDING_MODEL_ID = "BAAI/bge-small-en-v1.5"
BGE_QUERY_PREFIX = "Represent this sentence for searching relevant passages: "

# ~1 token ≈ 4 chars; defaults chosen to land near 600 tokens per chunk with 100 overlap
DEFAULT_CHUNK_CHARS = 2400
DEFAULT_CHUNK_OVERLAP_CHARS = 400
DEFAULT_TOP_K = 5

MAX_UPLOAD_BYTES = 50 * 1024 * 1024  # 50 MB

ANSWER_MAX_TOKENS = 2048
JUDGE_MAX_TOKENS = 1024

# Sonnet 5 standard pricing, $/million tokens
PRICE_INPUT_PER_MTOK = 3.00
PRICE_OUTPUT_PER_MTOK = 15.00


def calc_cost_usd(input_tokens: int, output_tokens: int) -> float:
    return (input_tokens / 1_000_000) * PRICE_INPUT_PER_MTOK + (
        output_tokens / 1_000_000
    ) * PRICE_OUTPUT_PER_MTOK
