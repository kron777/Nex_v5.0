"""Stage 5 (RDO v1.3 §16) — pathway SPECIFICATION tests (RDO side; no theory_x import).

Verifies the RDO's selection and specification of the first belief-to-mechanism pathway. The REAL
mechanism is verified separately, in isolation, by
`tests/test_belief_confidence_retrieval_pathway.py`.
"""
import os

from rdo import pathway


def test_selected_pathway_is_confidence_to_retrieval():
    s = pathway.select_pathway(".")
    assert "confidence" in s["selected"] and "retrieval" in s["selected"]
    sel = next(c for c in s["candidates"] if c["selected"])
    assert sel["risk"] == "low" and sel["reversibility"] == "high"


def test_belief_boost_is_excluded_as_a_candidate():
    s = pathway.select_pathway(".")
    boost = next(c for c in s["candidates"] if c["mechanism"] == "belief_boost")
    assert boost["selected"] is False and boost["suitability_as_first_slice"] == "excluded"
    assert "do NOT build" in boost["why"] or "decision-INERT" in boost["why"]
    assert boost["pathway"] in s["excluded"]
    # the exclusion is evidence-backed from the source
    assert boost.get("evidence") and ("INERT" in boost["evidence"][0] or "do NOT build" in boost["evidence"][0])


def test_causal_proposition_is_precise_and_evidenced():
    cp = pathway.select_pathway(".")["causal_proposition"]
    for k in ("belief_information", "mechanism", "relationship", "rule_eligibility",
              "rule_score", "observable_consequence", "evidence"):
        assert k in cp
    assert "confidence>=0.15" in cp["rule_eligibility"]
    assert "confidence" in cp["rule_score"]
    # evidence cites the real retrieval source
    assert any("retrieval.py" in e for e in cp["evidence"])


def test_baseline_success_failure_and_inconclusive_defined():
    s = pathway.select_pathway(".")
    assert s["baseline"] and "0.10" in s["baseline"]
    assert s["success_if"] and s["unsuccessful_if"]
    # unknowns kept unknown: live behaviour is explicitly inconclusive
    assert "LIVE" in s["inconclusive_because"] and "UNKNOWN" in s["inconclusive_because"]


def test_rollback_and_runtime_gate_are_host_only_and_unperformed():
    s = pathway.select_pathway(".")
    assert "nothing to roll back" in s["rollback"]
    gate = s["runtime_observation_gate"]
    assert "host-only" in gate["status"] and "NOT performed" in gate["status"]
    assert "approval" in gate["requires"]


def test_pathway_spec_module_is_nex_runtime_independent():
    # the RDO specification must not import theory_x/substrate (RDO independence invariant)
    src = open(os.path.join(os.path.dirname(pathway.__file__), "pathway.py"), encoding="utf-8").read()
    assert "import theory_x" not in src and "from theory_x" not in src
    assert "import substrate" not in src and "from substrate" not in src
