"""attribution_marker — structured 'per [source]' markers that survive rewrites.

Contested/attributed beliefs lose their source when consolidation paraphrases
their content into a bare claim. A marker that lives only in the text dies with
the paraphrase. So the attribution is kept in a STRUCTURED tag (outside content)
and re-applied in code after a rewrite — a contested claim cannot silently
flatten into settled fact.

Contested signal = the SUPERSET chosen in the map: the belief entered carrying a
hedge/attribution phrase. Cheapest reliable signal, no new classifier. A belief
already stamped (marker in tags) stays contested even after its content is bare.

Transform/inspect only — callers own the DB writes. Everything is best-effort
and never raises; it runs inside the fire path.
"""
from __future__ import annotations

import json
import re

_MARKER_PREFIX = "attribution:"   # tags convention: "attribution:<snippet>"

# Hedge / attribution phrases marking a sourced or contested entry (superset).
_ATTRIB_RX = re.compile(
    r"\b(?:this item (?:states|discusses|describes|reports|claims|introduces|notes)"
    r"|the feed (?:discusses|reports|states|notes)"
    r"|according to|reportedly|allegedly|purportedly|sources say"
    r"|as (?:reported|stated|claimed) by|cites?|citing"
    r"|per\s+[A-Z])\b",
    re.IGNORECASE,
)

# A named source after an EXPLICIT attribution connector ("according to
# Reuters", "per CERN", "cites X"). Case-insensitive on the connector; the
# source must be capitalized. "by"/"from" are deliberately excluded — they occur
# constantly inside claim bodies and would fabricate false sources.
# Case-insensitive on the connector only (?i:...); the source stays strictly
# capitalized so it can't swallow trailing lowercase words.
_NAMED_RX = re.compile(
    r"\b(?i:per|according to|cites?|citing|as reported by|as stated by)\s+"
    r"([A-Z][\w.&'\-]*(?:\s+[A-Z][\w.&'\-]*){0,3})"
)


def detect_attribution(content):
    """Return a short attribution snippet if `content` entered sourced/hedged,
    else None. Best-effort; never raises."""
    try:
        if not content:
            return None
        # Prefer an explicitly-named source (reliable connector + capitalized
        # name); it is also its own sufficient evidence of attribution.
        named = _NAMED_RX.search(content)
        if named:
            return named.group(1).strip()
        # Else fall back to a generic hedge phrase (kept short, for the marker).
        m = _ATTRIB_RX.search(content)
        if not m:
            return None
        snippet = content[m.start():m.start() + 60]
        snippet = re.split(r"[.;:]|['\"]", snippet)[0].strip()
        return snippet or None
    except Exception:
        return None


def marker_in_tags(tags):
    """Return the attribution snippet stored in a tags value (JSON string or
    list), or None."""
    try:
        if isinstance(tags, str):
            tags = json.loads(tags) if tags.strip() else []
        if not isinstance(tags, list):
            return None
        for t in tags:
            if isinstance(t, str) and t.startswith(_MARKER_PREFIX):
                snip = t[len(_MARKER_PREFIX):].strip()
                return snip or None
        return None
    except Exception:
        return None


def contested_snippet(belief):
    """A belief is contested/attributed if it already carries a stored marker OR
    its content entered hedged. Returns the snippet or None. `belief` is a
    dict-like with 'content' and optionally 'tags'."""
    try:
        get = getattr(belief, "get", None)
        if get is None:
            return None
        snip = marker_in_tags(belief.get("tags"))
        if snip:
            return snip
        return detect_attribution(belief.get("content"))
    except Exception:
        return None


def stamp_tags(existing_tags, snippet):
    """Return a JSON tags string carrying the attribution marker (idempotent).
    Returns None only if even the fallback fails."""
    try:
        tags = []
        if isinstance(existing_tags, str) and existing_tags.strip():
            tags = json.loads(existing_tags)
        elif isinstance(existing_tags, list):
            tags = list(existing_tags)
        if not isinstance(tags, list):
            tags = []
        marker = _MARKER_PREFIX + (snippet or "")[:80]
        if marker not in tags:
            tags.append(marker)
        return json.dumps(tags)
    except Exception:
        try:
            return json.dumps([_MARKER_PREFIX + (snippet or "")[:80]])
        except Exception:
            return None


def surface_in_content(content, snippet):
    """Append an honest attribution clause to `content` if it is not already
    attributed. A named source becomes '(per <Name>)'; an un-named hedge becomes
    '(per its source)' — never fabricates a specific citation. Never raises."""
    try:
        if not content or not snippet:
            return content
        if detect_attribution(content):
            return content  # rewrite kept an attribution — leave it
        src = snippet.strip().rstrip(".")
        # Surface a SPECIFIC source only when the snippet is a clean name (short,
        # and not itself a hedge phrase). Otherwise stay honest: "per its source"
        # — never fabricate a specific citation from a generic hedge.
        looks_named = bool(src) and len(src) <= 40 and not _ATTRIB_RX.search(src)
        clause = f" (per {src})." if looks_named else " (per its source)."
        return content.rstrip(".") + clause
    except Exception:
        return content
