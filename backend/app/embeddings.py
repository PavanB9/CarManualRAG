from functools import lru_cache
from typing import List

from fastembed import TextEmbedding

from . import config


@lru_cache(maxsize=1)
def _model() -> TextEmbedding:
    return TextEmbedding(model_name=config.EMBEDDING_MODEL_ID)


def embed_passages(texts: List[str], batch_size: int = 64) -> List[List[float]]:
    if not texts:
        return []
    vectors = _model().embed(texts, batch_size=batch_size)
    return [v.tolist() for v in vectors]


def embed_query(text: str) -> List[float]:
    vectors = list(_model().query_embed(text))
    return vectors[0].tolist()
