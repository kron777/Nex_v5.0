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


# ── Phase 43: noise-stream regex + echo-loop removal ─────────────────────────

def test_noise_streams_regex_matches_crypto_and_market():
    # internal.* streams are excluded by SQL (WHERE stream NOT LIKE 'internal.%'),
    # not by this regex — so only crypto.* and market.* are its responsibility.
    from theory_x.stage6_fountain.generator import FountainGenerator
    pat = FountainGenerator._SENSE_NOISE_STREAMS
    should_match = [
        "crypto.exchanges", "crypto.coingecko", "crypto.news",
        "market.futures", "CRYPTO.SOMETHING",  # case-insensitive
    ]
    should_not_match = [
        "ai_research.lab_blogs", "emerging_tech.hn",
        "philosophy.aeon", "news.bbc", "computing.tech_news",
    ]
    for s in should_match:
        assert pat.match(s), f"expected match for {s!r}"
    for s in should_not_match:
        assert not pat.match(s), f"expected no match for {s!r}"


def test_no_recent_thoughts_header_in_build_prompt_source():
    import inspect
    from theory_x.stage6_fountain.generator import FountainGenerator
    src = inspect.getsource(FountainGenerator._build_prompt)
    assert "Your recent thoughts" not in src, (
        "_build_prompt still contains 'Your recent thoughts' — echo-loop block not removed"
    )


# ── Phase 44: retrieval source-mix cap ───────────────────────────────────────

def test_retrieval_source_mix_cap_constant():
    from theory_x.stage6_fountain.generator import _OWN_PER_SOURCE_MAX
    assert _OWN_PER_SOURCE_MAX <= 3


def test_retrieval_source_mix_cap_applied():
    """Source-mix logic: no source exceeds _OWN_PER_SOURCE_MAX in the picked list."""
    from theory_x.stage6_fountain.generator import (
        _OWN_CONTENT_SOURCES, _OWN_PER_SOURCE_MAX,
    )
    from collections import defaultdict

    OWN_N = 7
    # Build fake rows: 10 synergized, 5 fountain_insight (all same content)
    fake_rows = [{"id": i, "source": "synergized", "content": f"s{i}",
                  "created_at": 1000 - i, "boost_value": 1.0} for i in range(10)]
    fake_rows += [{"id": 100 + i, "source": "fountain_insight", "content": f"f{i}",
                   "created_at": 900 - i, "boost_value": 1.0} for i in range(5)]

    per_src: dict = defaultdict(int)
    picked = []
    for r in fake_rows:
        src = r["source"]
        if per_src[src] >= _OWN_PER_SOURCE_MAX:
            continue
        picked.append(r)
        per_src[src] += 1
        if len(picked) >= OWN_N:
            break

    for src, count in per_src.items():
        assert count <= _OWN_PER_SOURCE_MAX, (
            f"source {src!r} has {count} slots, exceeds cap {_OWN_PER_SOURCE_MAX}"
        )
    # Both synergized and fountain_insight should be present
    sources_present = {r["source"] for r in picked}
    assert "synergized" in sources_present
    assert "fountain_insight" in sources_present


# ── Phase 45: sense→beliefs path ─────────────────────────────────────────────

def test_extract_sense_title_importable_from_stage1():
    """extract_sense_title lives in stage1 and produces same results as before."""
    from theory_x.stage1_sense.title_extract import extract_sense_title
    import json as _json
    payload = _json.dumps({"title": "Scaling laws for neural language models", "link": "https://x"})
    assert extract_sense_title("ai_research.arxiv", payload) == "Scaling laws for neural language models"
    assert extract_sense_title("any.stream", "") is None
    assert extract_sense_title("any.stream", _json.dumps({"exchange": "kraken"})) is None


def test_extract_sense_summary_delegates_to_stage1():
    """FountainGenerator._extract_sense_summary delegates without behavioural change."""
    import json as _json
    payload = _json.dumps({"title": "Test delegation"})
    result = _extract("some.stream", payload)
    assert result == "Test delegation"


def test_precipitated_from_sense_in_own_content_sources():
    from theory_x.stage6_fountain.generator import _OWN_CONTENT_SOURCES
    assert "precipitated_from_sense" in _OWN_CONTENT_SOURCES


def test_distillation_skips_no_title_payloads():
    """Payloads with no extractable title are skipped."""
    from theory_x.stage1_sense.title_extract import extract_sense_title
    import json as _json
    no_title = _json.dumps({"exchange": "kraken", "prices": {"BTC": 80000}})
    assert extract_sense_title("crypto.exchanges", no_title) is None


def test_distillation_extracts_crypto_titles():
    """Crypto streams with title fields are included (per design: crypto titles yes)."""
    from theory_x.stage1_sense.title_extract import extract_sense_title
    import json as _json
    payload = _json.dumps({"title": "Bitcoin surges past $90k on ETF inflows"})
    result = extract_sense_title("crypto.news", payload)
    assert result == "Bitcoin surges past $90k on ETF inflows"


def test_distillation_logic_cap_and_dedup():
    """Distillation logic: cap at 5/pass, dedup by content."""
    from theory_x.stage1_sense.title_extract import extract_sense_title
    import json as _json

    # Simulate 10 sense rows, all with titles
    rows = [
        {"id": i, "stream": "emerging_tech.hn", "payload": _json.dumps({"title": f"Story {i}"}),
         "timestamp": 1_000_000 + i}
        for i in range(10)
    ]
    seen_content: set[str] = set()
    written: list[str] = []
    PER_PASS_MAX = 5

    for row in rows:
        if len(written) >= PER_PASS_MAX:
            break
        title = extract_sense_title(row["stream"], row["payload"], max_items=1)
        if title is None or title in seen_content:
            continue
        seen_content.add(title)
        written.append(title)

    assert len(written) == 5
    assert written == [f"Story {i}" for i in range(5)]


# ── Phase 46: sense cap=5 override ───────────────────────────────────────────

def test_sense_per_source_cap_override():
    from theory_x.stage6_fountain.generator import (
        _OWN_PER_SOURCE_OVERRIDES,
        _per_source_cap,
    )
    assert _OWN_PER_SOURCE_OVERRIDES.get("precipitated_from_sense") == 5
    assert _per_source_cap("precipitated_from_sense") == 5
    assert _per_source_cap("synergized") == 3
    assert _per_source_cap("fountain_insight") == 3
