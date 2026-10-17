"""Prompt token budget (D-B).

The chat turn concatenates ~13 faculty blocks with no token accounting; when the
assembled prompt exceeds the model's context window, llama.cpp truncates from the
FRONT, so the identity / self-narrative block is the first thing silently lost and
what she receives reads as amnesia with no error anywhere. This module trims from
the BACK instead -- lowest-priority faculties first -- with a visible marker, so a
cut is loud rather than silent.

PURE and INERT. Nothing here runs on its own; a caller must invoke apply_budget(),
and even then is_enabled() is False unless BOTH:
    NEX5_PROMPT_BUDGET=on   AND   NEX5_PROMPT_CTX=<the model's context window>
The default NEX5_PROMPT_CTX=0 means "unset": the budget stays off rather than
guessing a ceiling, because guessing high and truncating from the front is the
exact failure this module exists to prevent. The context window is a server-side
setting on whatever serves NEX5_VOICE_URL (llama.cpp -c / ollama num_ctx / vLLM
--max-model-len); it is not knowable from the repo, hence the flag.

Priorities and weights are Beam's D-B spec. Weights sum to 0.90; the unspent 0.10
is reserve for fixed framing, tool definitions and the assistant turn, so a full
set of blocks at their caps never trims on every build.
"""
from __future__ import annotations

import logging
import math
from typing import Optional

log = logging.getLogger("nex5.prompt_budget")

# Highest priority first. cap = max(200, floor(ceiling * weight)).
FACULTY_WEIGHTS: list[tuple[str, float]] = [
    ("identity", 0.25),      # identity / self-narrative
    ("affect", 0.18),        # affect / interoception
    ("problem", 0.16),       # active problem
    ("conversation", 0.13),  # recent conversation
    ("beliefs", 0.10),       # retrieved beliefs
    ("peripheral", 0.08),    # everything else
]
_ORDER = {name: i for i, (name, _) in enumerate(FACULTY_WEIGHTS)}
_WEIGHT = dict(FACULTY_WEIGHTS)
_MIN_CAP = 200
_CTX_FRACTION = 0.70
MARKER = " [...trimmed]"  # ASCII, one leading space, appended once per cut block


def est_tokens(s: str) -> int:
    """Conservative char/4 token estimate (ceil). No tokenizer dependency."""
    return (len(s) + 3) // 4


def ceiling_for(num_ctx: int) -> int:
    """Usable prompt budget = 70% of the context window; 0 when ctx unset."""
    return int(math.floor(_CTX_FRACTION * num_ctx)) if num_ctx and num_ctx > 0 else 0


def cap_for(faculty: str, ceiling: int) -> int:
    w = _WEIGHT.get(faculty, _WEIGHT["peripheral"])
    return max(_MIN_CAP, int(math.floor(ceiling * w)))


def _truncate(text: str, budget_tokens: int) -> str:
    """Trim text to <= budget_tokens, at the last sentence boundary when one sits
    reasonably deep, else a hard cut; append MARKER. Phase-2 / per-cap truncation."""
    if est_tokens(text) <= budget_tokens:
        return text
    max_chars = max(0, budget_tokens * 4 - len(MARKER))
    head = text[:max_chars]
    cut = max(head.rfind(". "), head.rfind("! "), head.rfind("? "),
              head.rfind(".\n"), head.rfind("!\n"), head.rfind("?\n"))
    if cut > max_chars // 2:  # a boundary exists deep enough to be worth keeping
        head = head[:cut + 1]
    return head.rstrip() + MARKER


def is_enabled(env: Optional[dict] = None) -> tuple[bool, int]:
    """(enabled, num_ctx). Enabled only when the flag is on AND ctx is set > 0."""
    import nex_config
    on = nex_config.get_str("NEX5_PROMPT_BUDGET", "off", env).strip().lower() == "on"
    ctx = nex_config.get_int("NEX5_PROMPT_CTX", 0, env)
    return (on and ctx > 0), ctx


def apply_budget(blocks, num_ctx: int):
    """Trim labelled prompt blocks to fit the ceiling derived from num_ctx.

    blocks: ordered list of (faculty, text), HIGHEST priority first. An unknown
    faculty is treated as 'peripheral'. Returns (kept_blocks, report). When the
    ceiling is 0 (ctx unset) the blocks are returned untouched.
    """
    ceiling = ceiling_for(num_ctx)
    if ceiling <= 0:
        return list(blocks), {"ceiling": 0, "applied": False}

    # 1. per-faculty cap: bound each block to its share.
    capped: list[tuple[str, str]] = []
    requested: dict[str, int] = {}
    granted: dict[str, int] = {}
    for fac, text in blocks:
        requested[fac] = requested.get(fac, 0) + est_tokens(text)
        t = _truncate(text, cap_for(fac, ceiling))
        granted[fac] = granted.get(fac, 0) + est_tokens(t)
        capped.append((fac, t))

    # 2. total ceiling: drop whole blocks, lowest priority first.
    def _prio(i: int) -> tuple[int, int]:
        return (_ORDER.get(capped[i][0], len(_ORDER)), i)

    total = sum(est_tokens(t) for _, t in capped)
    dropped: list[str] = []
    while total > ceiling and len(capped) > 1:
        idx = max(range(len(capped)), key=_prio)
        fac, t = capped.pop(idx)
        dropped.append(fac)
        total -= est_tokens(t)

    # 3. a single surviving block still over -> truncate it to the ceiling.
    if total > ceiling and len(capped) == 1:
        fac, t = capped[0]
        capped[0] = (fac, _truncate(t, ceiling))
        total = est_tokens(capped[0][1])

    report = {"ceiling": ceiling, "applied": True, "total": total,
              "requested": requested, "granted": granted, "dropped": dropped}
    log.info("prompt_budget: ceiling=%d total=%d dropped=%s req=%s granted=%s",
             ceiling, total, dropped, requested, granted)
    return capped, report
