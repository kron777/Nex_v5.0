"""compass — the dharmic moral compass (NEX5_COMPASS).

NOT a rule engine and NOT a verdict machine. At a moment that carries some moral
weight, it READS the situated faculties she now has — compassion (care owed to
the person), amoha (is she seeing clearly?), the affliction cluster (is her
stance distorted?) — and WEIGHS whichever are live into a provisional, abductive,
HELD-OPEN lean she brings into the dialogue. It composes her own reads; it never
maps a situation to a fixed action, never pronounces a judgment, never gates what
she may think.

Doctrine (hard line): abductive, situated, co-constructed. The stance is
something to think WITH the person, offered as "given what I'm seeing, the
caring-and-clear thing seems to be X, held open" — not issued AT them. If the
reads are quiet (no care owed, seeing clear, no distortion) there is no moral
weight and the compass is silent.

GUARD 2: prompt-only. Reads other faculties; writes no belief/world table, and
does not mutate compassion's level (uses its non-persisting read). FAIL-SAFE:
any error -> '' (no stance). Admin-scoped at the seam; non-admin path untouched.
"""
from __future__ import annotations

_CARE_MIN = 0.33   # a distress salience worth weighing as care owed (~compassion's fire point)


def weigh(message: str) -> dict:
    """Read the situated faculties for this moment. Returns the live considerations
    — care (level+register), clarity (amoha), distortion (afflictions firing).
    Pure read: mutates nothing. Fail-safe: empty reads on any error."""
    reads = {"care": 0.0, "care_register": "", "clarity": "clear", "distortions": []}
    try:
        from theory_x.stage_affect.compassion import _distress_read
        sal, reg = _distress_read(message)      # non-persisting read; no level mutation
        reads["care"], reads["care_register"] = sal, reg
    except Exception:
        pass
    try:
        from theory_x.stage_tom.amoha_detector import detect as _amoha
        reads["clarity"] = _amoha().get("state", "clear")
    except Exception:
        pass
    try:
        from theory_x.stage_tom.self_binding import _cluster_reads, _AFFLICTION_HIGH
        cur = _cluster_reads()
        reads["distortions"] = [name for name, (hi, _) in _AFFLICTION_HIGH.items()
                                if cur.get(name) == hi]
    except Exception:
        pass
    return reads


def format_stance(reads: dict) -> str:
    """Compose the live considerations into a provisional, held-open lean. Empty
    when no consideration is live (no moral weight). This ASSEMBLES the active
    situated considerations — it does not look a verdict up from a table."""
    try:
        care = float(reads.get("care", 0.0) or 0.0)
        clarity = reads.get("clarity", "clear")
        distortions = list(reads.get("distortions", []))

        # Non-care dimensions decide WHETHER the compass speaks. Care alone is
        # compassion's job — the compass adds a note only when it has something
        # beyond care to weigh (clouded seeing or an affliction).
        non_care = []
        if clarity == "clouded":
            non_care.append(
                "your own seeing is clouded right now — hold your read lightly, you may have it wrong")
        elif clarity == "mild":
            non_care.append(
                "your seeing is only partly clear — leave room to be corrected")
        if distortions:
            non_care.append(
                "your stance is coloured just now (" + ", ".join(distortions) +
                ") — loosen it before you lean on it")

        if not non_care:
            return ""   # care-only, or nothing live => compassion owns it => silent

        # Compass speaks: lead with care if it is also live, then the non-care weights.
        considerations = []
        if care >= _CARE_MIN:
            considerations.append(
                "the person seems to be carrying some difficulty — care is owed here")
        considerations.extend(non_care)

        return (
            "[A moment with some weight in it. Given what you are reading here — "
            + "; ".join(considerations) +
            " — the caring-and-clear thing seems to be to slow down, attend to who "
            "is actually in front of you, and do no harm, held open to revision as "
            "you learn more. This is a way of leaning, not a verdict: think it "
            "through with them, don't pronounce it, and let the choice stay live.]\n\n"
        )
    except Exception:
        return ""


def stance_for(message: str) -> str:
    """Compose-path entry: weigh the moment and return the held-open stance ('' if
    no moral weight). Fail-safe: '' on any error."""
    try:
        return format_stance(weigh(message))
    except Exception:
        return ""
