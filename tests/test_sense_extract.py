"""Unit tests for FountainGenerator._extract_sense_summary — Phase 42.

Verifies JSON payload extraction replaces wholesale {/[ rejection with
structured title/headline/name extraction so sense streams reach the
fountain prompt.
"""
from __future__ import annotations

import json
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from tests import _bootstrap  # noqa: F401
from theory_x.stage6_fountain.generator import FountainGenerator

_extract = FountainGenerator._extract_sense_summary


# ── 1. JSON object with top-level title ──────────────────────────────────────

def test_object_with_title():
    payload = json.dumps({"title": "Predictive signals shape memory formation", "link": "https://example.com"})
    result = _extract("neuroscience.arxiv_qbio", payload)
    assert result == "Predictive signals shape memory formation"


# ── 2. JSON array of objects each with title ────────────────────────────────

def test_array_of_titled_objects():
    payload = json.dumps([
        {"title": "First headline"},
        {"title": "Second headline"},
        {"title": "Third headline"},
        {"title": "Fourth headline"},
    ])
    result = _extract("news.bbc", payload)
    assert result == "First headline · Second headline · Third headline"


# ── 3. Nested structure (coins[].name) ──────────────────────────────────────

def test_nested_coins_name():
    payload = json.dumps({"coins": [
        {"id": "bitcoin", "name": "Bitcoin", "current_price": 79000},
        {"id": "ethereum", "name": "Ethereum", "current_price": 2200},
        {"id": "solana", "name": "Solana", "current_price": 93},
        {"id": "tether", "name": "Tether", "current_price": 1},
    ]})
    result = _extract("crypto.coingecko", payload)
    assert result == "Bitcoin · Ethereum · Solana"


# ── 4. Malformed JSON → None ─────────────────────────────────────────────────

def test_malformed_json_returns_none():
    result = _extract("emerging_tech.hn", '{"title": "broken json"')
    assert result is None


# ── 5. Empty payload → None ──────────────────────────────────────────────────

def test_empty_payload_returns_none():
    assert _extract("any.stream", "") is None
    assert _extract("any.stream", "   ") is None


# ── 6. Non-JSON string → returned as-is (truncated if long) ─────────────────

def test_non_json_returned_as_is():
    result = _extract("some.stream", "plain text content")
    assert result == "plain text content"


def test_non_json_long_truncated_at_200():
    long_text = "x" * 300
    result = _extract("some.stream", long_text)
    assert result == "x" * 200


# ── 7. JSON with no title/name/headline/subject → None ──────────────────────

def test_no_recognisable_fields_returns_none():
    payload = json.dumps({"exchange": "kraken", "prices": {"BTCUSDT": 80000}})
    result = _extract("crypto.exchanges", payload)
    assert result is None


# ── 8a. Real fixture — ai_research.lab_blogs ────────────────────────────────

def test_real_fixture_lab_blogs():
    payload = json.dumps({
        "title": "AlphaEvolve: How our Gemini-powered coding agent is scaling impact across fields",
        "link": "https://deepmind.google/blog/alphaevolve-impact/",
        "summary": "Explore how AlphaEvolve drives impact.",
        "published": "Wed, 06 May 2026 10:43:49 +0000",
        "authors": [],
        "tags": [],
    })
    result = _extract("ai_research.lab_blogs", payload)
    assert result == "AlphaEvolve: How our Gemini-powered coding agent is scaling impact across fields"


# ── 8b. Real fixture — emerging_tech.hn ─────────────────────────────────────

def test_real_fixture_hn():
    payload = json.dumps({
        "title": "Docker images are hundreds of MB; a full game engine compiles to 35MB WASM",
        "url": "https://bogomolov.work/blog/",
        "author": "user123",
        "points": 247,
    })
    result = _extract("emerging_tech.hn", payload)
    assert result == "Docker images are hundreds of MB; a full game engine compiles to 35MB WASM"


# ── 8c. Real fixture — philosophy.aeon ──────────────────────────────────────

def test_real_fixture_aeon():
    payload = json.dumps({
        "title": "Beneath our human shallows",
        "link": "https://aeon.co/essays/how-does",
        "summary": "Some philosophical essay.",
    })
    result = _extract("philosophy.aeon", payload)
    assert result == "Beneath our human shallows"


# ── 8d. Real fixture — internal.exchanges (no useful fields) ────────────────

def test_real_fixture_exchanges_no_title():
    payload = json.dumps({
        "exchange": "kraken",
        "prices": {"XETHZUSD": 2259.11, "SOLUSD": 93.61, "XXBTZUSD": 79847.5},
        "fetched_at": 1778604694,
    })
    result = _extract("crypto.exchanges", payload)
    assert result is None


# ── max_items cap ─────────────────────────────────────────────────────────────

def test_max_items_respected():
    payload = json.dumps([{"title": f"Title {i}"} for i in range(10)])
    result = _extract("news.bbc", payload, max_items=2)
    assert result == "Title 0 · Title 1"
