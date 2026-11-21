"""Domain knowledge for the demonstration cycle.

This is the ONE place where LLM/human reasoning seeds the engine: the idea is
decomposed into top-level obligations, and each gets a *reconciliation signature*
— a read-only pattern that proves whether a real mechanism exists. The engine
then expands, reconciles against the actual tree, assesses and prioritises
deterministically. Seeds are proposals; the tree is the authority (RDO §22).

Test case: WHATS_NEXT.md §3b / GENIUS_SCORE_v2.md §7 — "deploy the genius
auto-tagger and its consumers." Chosen because the priority doc is from May 2026,
so reconciliation against HEAD is the whole point.
"""
from __future__ import annotations

from typing import Dict, List, Tuple

from .model import ANTI_REQUIREMENT, NECESSARY, Obligation
from .reconcile import Signature


def genius_tagger_idea() -> Tuple[str, List[str], List[Obligation], Dict[str, List[Signature]]]:
    objective = ("Deploy the calibrated genius v2 score as an auto-tagger and its "
                 "consumers (WHATS_NEXT.md §3b / GENIUS_SCORE_v2.md §7a-7e + consumers).")
    assumptions = [
        "WHATS_NEXT.md (last updated 2026-05) reflects current state",
        "the v2 score is calibrated and must not be re-fit",
        "consumers (retrieval bias, fountain prompt context) are not yet built "
        "(per tagger.py docstring)",
    ]
    seeds = [
        Obligation("genius_tags", "genius_tags output table (§7a)", "persistence",
                   rationale="auto-tagger needs a place to write scores"),
        Obligation("genius_tagger", "genius tagger daemon (§7b/§7c)", "daemon",
                   rationale="score every fountain fire continuously"),
        Obligation("genius_api", "/api/genius/recent + HUD panel (§7d/§7e)", "api",
                   rationale="surface recent tags"),
        Obligation("genius_score", "calibrated v2 score", "score",
                   rationale="the signal being deployed"),
        Obligation("genius_consumer_fountain", "fountain prompt reads recent tags (consumer B)",
                   "consumer", rationale="bias generation toward striking material"),
        Obligation("genius_consumer_retrieval", "retrieval favours high-score fires (consumer A)",
                   "consumer", rationale="weight fetch/selection by genius score"),
        Obligation("genius_runtime_verification", "observe tagger+consumers firing at runtime",
                   "runtime_verification", classification=NECESSARY,
                   rationale="source existence does not prove runtime behaviour"),
        # anti-requirements (deliberately NOT to be built)
        Obligation("anti_second_score", "do not build a second genius score", "anti_requirement",
                   classification=ANTI_REQUIREMENT,
                   rationale="v2 is calibrated (97.1% training acc, GENIUS_SCORE_v2.md); a "
                             "competing score would duplicate and could de-calibrate"),
        Obligation("anti_duplicate_tags_store", "do not create a second tags store",
                   "anti_requirement", classification=ANTI_REQUIREMENT,
                   rationale="genius_tags already persists in conversations.db; a second store "
                             "would fragment provenance"),
    ]
    signatures: Dict[str, List[Signature]] = {
        "genius_tags": [
            Signature(r"CREATE TABLE IF NOT EXISTS genius_tags", "substrate/init_db.py",
                      "genius_tags table DDL (§7a)")],
        "genius_tagger": [
            Signature(r"class GeniusTagger", "theory_x/genius", "GeniusTagger daemon (§7b)"),
            Signature(r"Wiring genius tagger", "run.py", "boot wiring (§7c)")],
        "genius_api": [
            Signature(r"api/genius/recent", "gui/server.py", "/api/genius/recent route (§7d)"),
            Signature(r"def overview", "theory_x/genius/panel.py", "HUD panel (§7e)")],
        "genius_score": [
            Signature(r"WEIGHTS_PATH|def .*score", "theory_x/genius/score_v2.py", "v2 score module"),
            Signature(r"genius_score_weights", None, "fitted weights file")],
        "genius_consumer_fountain": [
            Signature(r"FROM genius_tags", "theory_x/stage6_fountain/generator.py",
                      "generation reads genius_tags (consumer B)")],
        "genius_consumer_retrieval": [
            Signature(r"genius.{0,40}(focus_num|branch_temp|_retrieve_context|retriev).{0,40}weight"
                      r"|retriev.{0,40}genius.{0,20}(score|weight|boost)",
                      "theory_x/stage6_fountain",
                      "retrieval/fetch weighted by genius score (consumer A)")],
    }
    return objective, assumptions, seeds, signatures
