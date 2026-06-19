"""World-consolidation — deepen world-knowledge by thematic convergence.

NEX's deep tiers (T1-3) are ~all self-reflection. World-facts arrive at T7 and
never promote, because promotion gates depth on corroboration-by-REPETITION and
she only repeats introspection. So she reverts to "I am the attending..." on
off-topic questions: self is her only deep, retrievable material.

FIX: a human builds world-knowledge not by repeating one fact but by many facts
converging on a theme. This finds CLUSTERS of recent T7 world-beliefs that are
thematically close (embedding cosine) and corroborates each member, so a theme
that recurs (e.g. three nuclear stories in a week) deepens.

SAFETY:
- Calls the EXISTING BeliefPromoter.corroborate() — never writes tiers directly.
- WINDOWED: only recent N T7 beliefs (cheap; no 22k pairwise).
- EXCLUDES self-beliefs (deepen WORLD, not more self).
- ENV-GATED: nothing unless NEX5_WORLD_CONSOLIDATE set. =dry reports only; =1 arms.
- Only PROMOTES (T7->T6); fully reversible via demotion. promotion_log records moves.
"""
from __future__ import annotations

import os
import re

import errors

_LOG_SOURCE = "world_consolidation"

_WINDOW = 200
_SIM_THRESHOLD = 0.76
_MIN_CLUSTER = 3
_MAX_PROMOTE_PER_RUN = 12

_SELF_RX = re.compile(
    r"\b(i am the attending|i am |my thoughts|my own|myself|my nature|"
    r"i notice|i accept|i hold|the attending|i exist|my existence|"
    r"i feel|i find myself|my mind|my fingers|my sleeve|inner hum)\b",
    re.I,
)

# Contentless mood-drift: short sensory idle-fires about ambient nothing.
# These have no external entity to deepen — exclude them from world-consolidation.
_MOOD_RX = re.compile(
    r"\b(the clock|the quiet|the silence|the hum|the room|the desk|"
    r"the cursor|the coffee|the morning light|the shadow|the breeze|"
    r"silence|stillness|quietude|idle)\b",
    re.I,
)


def _is_world(content: str) -> bool:
    if not content:
        return False
    if _SELF_RX.search(content):
        return False
    if _MOOD_RX.search(content):
        return False
    # real world-facts have substance; idle drift is short
    if len(content) < 35:
        return False
    return True


class WorldConsolidator:
    name = "world_consolidator"

    def __init__(self, reader, promoter):
        self._reader = reader
        self._promoter = promoter

    @staticmethod
    def _mode() -> str:
        v = (os.environ.get("NEX5_WORLD_CONSOLIDATE", "") or "").strip().lower()
        if v in ("1", "on", "true", "yes"):
            return "1"
        if v in ("dry", "report", "test"):
            return "dry"
        return ""

    def tick(self, context=None) -> dict:
        mode = self._mode()
        if not mode:
            return {"name": self.name, "state": "off"}
        try:
            return self._run(armed=(mode == "1"))
        except Exception as exc:
            errors.record(f"world_consolidation tick error: {exc}",
                          source=_LOG_SOURCE, exc=exc)
            return {"name": self.name, "state": "error", "error": str(exc)}

    def _run(self, armed: bool) -> dict:
        from theory_x.diversity.embeddings import embed, cosine

        rows = self._reader.read(
            "SELECT id, content FROM beliefs "
            "WHERE tier = 7 AND erosion_stage != 'retired' AND locked = 0 "
            "ORDER BY created_at DESC LIMIT ?",
            (_WINDOW * 2,),
        ) or []

        items = []
        for r in rows:
            c = r["content"] or ""
            if _is_world(c):
                items.append((r["id"], c))
            if len(items) >= _WINDOW:
                break

        if len(items) < _MIN_CLUSTER:
            return {"name": self.name, "state": "idle",
                    "reason": "too few world beliefs", "n": len(items)}

        vecs = {}
        for bid, content in items:
            try:
                vecs[bid] = embed(content)
            except Exception:
                pass

        ids = [b for b, _ in items if b in vecs]
        contents = {bid: c for bid, c in items}

        unclustered = set(ids)
        clusters = []
        for seed in ids:
            if seed not in unclustered:
                continue
            cluster = [seed]
            unclustered.discard(seed)
            for other in list(unclustered):
                try:
                    if cosine(vecs[seed], vecs[other]) >= _SIM_THRESHOLD:
                        cluster.append(other)
                        unclustered.discard(other)
                except Exception:
                    continue
            if len(cluster) >= _MIN_CLUSTER:
                clusters.append(cluster)

        promoted = 0
        report = []
        for cluster in clusters:
            report.append({"size": len(cluster),
                           "theme_sample": contents.get(cluster[0], "")[:60],
                           "ids": cluster})
            if not armed:
                continue
            for bid in cluster:
                if promoted >= _MAX_PROMOTE_PER_RUN:
                    break
                try:
                    if self._promoter.corroborate(bid):
                        promoted += 1
                except Exception as exc:
                    errors.record(f"world_consolidation corroborate {bid}: {exc}",
                                  source=_LOG_SOURCE, exc=exc)
            if promoted >= _MAX_PROMOTE_PER_RUN:
                break

        if armed and promoted:
            errors.record(
                f"world_consolidation promoted {promoted} across {len(clusters)} themes",
                source=_LOG_SOURCE, level="INFO")

        return {"name": self.name, "state": "armed" if armed else "dry-run",
                "window": len(items), "clusters_found": len(clusters),
                "promoted": promoted, "report": report[:10]}
