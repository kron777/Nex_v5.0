"""RDO Stage 5 (v1.3 §16) — first belief-to-mechanism pathway: ISOLATED verification.

Pathway:  belief.confidence  ->  world-model BeliefRetriever  ->  eligibility + relevance ordering.
  eligibility: tier<=6 AND paused=0 AND (locked=1 OR confidence>=0.15)   [theory_x/stage3_world_model/retrieval.py:164]
  relevance:   score = keyword_overlap_fraction * confidence             [theory_x/stage3_world_model/retrieval.py:218]

This exercises the REAL BeliefRetriever against an ISOLATED temp SQLite fixture built from the
REAL belief schema (substrate/schema/beliefs.sql). It writes only to the throwaway fixture — never
to any live NEX database, and it changes no NEX state, config, flag or experiment. It is falsifiable
(baseline, in-fixture intervention, negatives, failure conditions). It verifies the DOCUMENTED
CONTRACT in isolation; it is NOT live-runtime verification (that is host-only, NEX in standby).
"""
import pathlib
import sqlite3
import uuid

import pytest

_SCHEMA = pathlib.Path("substrate/schema/beliefs.sql").read_text(encoding="utf-8")
_COLS = ["content", "tier", "confidence", "created_at", "source", "locked", "paused", "branch_id"]


def _fixture_db(tmp_path, beliefs):
    """Build a throwaway DB from the REAL belief schema and seed test beliefs (writable connection,
    then closed). The retriever reads it read-only."""
    path = str(tmp_path / f"beliefs_{uuid.uuid4().hex}.db")
    con = sqlite3.connect(path)
    con.executescript(_SCHEMA)
    for b in beliefs:
        row = {"source": "test", "locked": 0, "paused": 0, "branch_id": None, "created_at": 0, **b}
        con.execute(f"INSERT INTO beliefs ({','.join(_COLS)}) VALUES ({','.join('?' * len(_COLS))})",
                    [row[c] for c in _COLS])
    con.commit()
    con.close()
    return path


@pytest.fixture
def retrieve_from(tmp_path):
    from substrate import Reader
    from theory_x.stage3_world_model.retrieval import BeliefRetriever

    def run(beliefs, query, **kw):
        retr = BeliefRetriever(Reader(_fixture_db(tmp_path, beliefs)))
        return [dict(r) for r in retr.retrieve(query, **kw)]
    return run


_Q = "alpha beta gamma"
def _match(conf, **kw):           # a belief whose content matches the query, at a given confidence
    return {"content": "alpha beta gamma delta", "tier": 1, "confidence": conf, **kw}


# ---------------------------- baseline (no intervention) ----------------------------

def test_baseline_below_threshold_is_not_retrieved(retrieve_from):
    # BASELINE: a relevant belief below the confidence floor (0.15), not locked, is NOT eligible.
    out = retrieve_from([_match(0.10)], _Q)
    assert out == [], "baseline: a 0.10-confidence belief must be below the eligibility floor"


# ------------------------- intervention (in-fixture, reversible) --------------------

def test_raising_confidence_admits_the_belief(retrieve_from):
    # INTERVENTION (isolated fixture only): the same belief at 0.50 crosses the floor and is retrieved.
    out = retrieve_from([_match(0.50)], _Q)
    assert len(out) == 1 and out[0]["content"].startswith("alpha beta gamma")


def test_confidence_multiplies_relevance_ordering(retrieve_from):
    # two equally keyword-matching beliefs: the higher-confidence one ranks first (confidence multiplies)
    out = retrieve_from([_match(0.30, source="low"), _match(0.90, source="high")], _Q)
    assert len(out) == 2 and out[0]["source"] == "high" and out[1]["source"] == "low"


# ------------------------ negative / failure conditions -----------------------------

def test_locked_belief_overrides_the_floor(retrieve_from):
    # a LOCKED belief below the floor is still eligible (locked=1 OR confidence>=0.15)
    out = retrieve_from([_match(0.05, locked=1)], _Q)
    assert len(out) == 1


def test_paused_belief_is_never_retrieved(retrieve_from):
    out = retrieve_from([_match(0.95, paused=1)], _Q)
    assert out == []


def test_tier_above_six_is_excluded(retrieve_from):
    out = retrieve_from([_match(0.95, tier=7)], _Q)
    assert out == []


def test_no_keyword_overlap_is_not_scored(retrieve_from):
    # an eligible, high-confidence belief that shares no tokens with the query is not returned
    out = retrieve_from([{"content": "entirely unrelated content", "tier": 1, "confidence": 0.95}], _Q)
    assert out == []


def test_empty_query_returns_eligible_without_scoring(retrieve_from):
    # failure/edge: an empty query has no tokens -> the retriever returns the eligible rows unscored
    # (retrieval.py:201). Documented behaviour, asserted so a future change is caught.
    out = retrieve_from([_match(0.50)], "")
    assert len(out) == 1


# ------------------------------- read-only guarantee --------------------------------

def test_fixture_is_isolated_not_a_live_db(tmp_path, retrieve_from):
    # the retriever only ever reads the throwaway fixture path under tmp_path; no live DB is touched
    from substrate import Reader
    from theory_x.stage3_world_model.retrieval import BeliefRetriever
    path = _fixture_db(tmp_path, [_match(0.50)])
    retr = BeliefRetriever(Reader(path))
    assert str(tmp_path) in retr._reader.db_path and retr._reader.db_path.endswith(".db")
    retr.retrieve(_Q)   # read-only; no exception, no writes
