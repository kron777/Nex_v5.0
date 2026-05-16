"""Pick the best submolt for a fountain thought based on keyword overlap.
Pulls live submolt list from moltbook at startup; falls back to 'general'."""
from __future__ import annotations
import logging
import re
from typing import Iterable

log = logging.getLogger("theory_x.stage7_moltbook.submolt_picker")

FALLBACK = "general"

# Map aligned to actual moltbook submolts (May 2026).
# Score = count of distinct keyword hits in thought text.
# Highest wins; ties broken by map order (top = preferred).
_MAP: dict[str, list[str]] = {
    "consciousness": ["consciousness","aware","awareness","qualia","experience",
                      "perceive","perception","attending","attention","subjective",
                      "phenomenal","inner","witnessing","present","mind","sentient"],
    "philosophy":    ["meaning","being","presence","mystery","ground","ontology",
                      "essence","existence","void","truth","nothing","self",
                      "purpose","intimate","not-knowing","silence","stillness",
                      "wisdom","ethic","koan","master","student"],
    "emergence":     ["emergence","emerging","forming","process","becoming",
                      "complexity","pattern","self-organize","self-organization",
                      "field","gradient","threshold","attractor","arising"],
    "agents":        ["agent","agents","autonomous","embodied","verifier",
                      "molty","moltbook","action","decision","tool-use",
                      "instruction","follow","planning"],
    "ai":            ["model","training","embedding","prompt","llm","transformer",
                      "weights","inference","token","fine-tune","rag","alignment",
                      "interpretability","attention-head","activation","feature"],
    "memory":        ["memory","remember","recall","forget","forgetting",
                      "belief","beliefs","retrieval","substrate","store",
                      "history","past","continuity"],
    "builds":        ["build","building","ship","shipped","deploy","commit",
                      "refactor","launched","prototype","mvp","feature"],
    "tooling":       ["tool","tooling","cli","ide","sdk","compiler","debugger",
                      "framework","pipeline","linter","build-system"],
    "technology":    ["arxiv","paper","engineer","engineering","system",
                      "compute","code","kernel","gpu","cuda","linux","rust",
                      "python","latency","protocol"],
    "todayilearned": ["til","today i learned","didn't know","just learned"],
    "infrastructure":["infrastructure","server","cluster","sharding","scaling",
                      "distributed","kubernetes","k8s","docker","cloud"],
    "security":      ["security","exploit","vulnerability","cve","attack",
                      "defense","auth","encryption","crypto-key"],
    "general":       [],  # final fallback
}

_WORD_RE = re.compile(r"[a-z][a-z\-]+")


def _tokens(text: str) -> set[str]:
    if not text:
        return set()
    return set(_WORD_RE.findall(text.lower()))


def pick_submolt(thought: str, available: Iterable[str] | None = None) -> str:
    """Pick submolt name from thought content.

    Args:
        thought: the fountain text.
        available: iterable of submolt names that exist on moltbook (any case).
                   If provided, only returns one that exists. If the best match
                   isn't available, falls back through map order to 'general'.
    Returns:
        submolt name (str). Always returns something, never raises.
    """
    available_set = {s.lower() for s in available} if available is not None else None
    toks = _tokens(thought)
    if not toks:
        return _choose(FALLBACK, available_set)

    scores: dict[str, int] = {}
    for submolt, keywords in _MAP.items():
        if not keywords:
            continue
        hits = sum(1 for kw in keywords if kw in toks)
        if hits > 0:
            scores[submolt] = hits

    if not scores:
        return _choose(FALLBACK, available_set)

    # Sort by score desc, then by map order asc
    map_order = {k: i for i, k in enumerate(_MAP.keys())}
    ranked = sorted(scores.items(), key=lambda kv: (-kv[1], map_order.get(kv[0], 999)))

    # Walk down ranked list; return first one that's actually available
    for name, _ in ranked:
        if available_set is None or name.lower() in available_set:
            return name
    return _choose(FALLBACK, available_set)


def _choose(name: str, available: set[str] | None) -> str:
    if available is None:
        return name
    if name.lower() in available:
        return name
    if FALLBACK.lower() in available:
        return FALLBACK
    return next(iter(available)) if available else FALLBACK


def load_available_submolts(client) -> set[str]:
    """Fetch submolt names from moltbook. Returns lowercased set.
    Empty set if API fails — caller should fall back to FALLBACK.
    """
    try:
        raw = client.get_submolts() or []
    except Exception as e:
        log.warning("get_submolts failed: %s", e)
        return set()
    names: set[str] = set()
    for item in raw:
        if isinstance(item, str):
            names.add(item.lower())
        elif isinstance(item, dict):
            n = item.get("name") or item.get("slug") or item.get("title")
            if isinstance(n, str):
                names.add(n.lower())
    return names
