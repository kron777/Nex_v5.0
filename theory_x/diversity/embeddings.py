"""Local embedding wrapper — sentence-transformers, cached."""
from __future__ import annotations

import logging
import threading
from typing import Optional

import numpy as np

log = logging.getLogger("theory_x.diversity.embeddings")

_model = None
_model_lock = threading.Lock()
_cache: dict[int, np.ndarray] = {}
_cache_lock = threading.Lock()


def get_model():
    global _model
    with _model_lock:
        if _model is None:
            from sentence_transformers import SentenceTransformer
            log.info("Loading sentence-transformer all-MiniLM-L6-v2 (first use)")
            _model = SentenceTransformer("all-MiniLM-L6-v2")
            log.info("Sentence-transformer loaded")
        return _model


def embed(text: str) -> np.ndarray:
    if not text or not text.strip():
        return np.zeros(384, dtype=np.float32)
    model = get_model()
    return model.encode(text.strip(), convert_to_numpy=True, show_progress_bar=False)


def embed_belief(belief_id: int, content: str) -> np.ndarray:
    with _cache_lock:
        if belief_id in _cache:
            return _cache[belief_id]
    vec = embed(content)
    with _cache_lock:
        _cache[belief_id] = vec
    return vec


def cosine(a: np.ndarray, b: np.ndarray) -> float:
    na = np.linalg.norm(a)
    nb = np.linalg.norm(b)
    if na == 0 or nb == 0:
        return 0.0
    sim = float(np.dot(a, b) / (na * nb))
    return (sim + 1.0) / 2.0


def distance(a: np.ndarray, b: np.ndarray) -> float:
    return 1.0 - cosine(a, b)
