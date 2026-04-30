"""Theory X Stage 3 — Belief Synergizer.

Selects a cross-branch pair of beliefs, strikes them together via LLM,
and writes the emergent insight as a new synergized belief.
Cell mitosis for the belief graph.
"""
from __future__ import annotations

import time
from typing import Optional

import errors
from substrate import Reader, Writer
from voice.llm import VoiceClient, VoiceRequest
from voice.registers import PHILOSOPHICAL

THEORY_X_STAGE = 3

_LOG_SOURCE = "synergizer"

_SYNTHESIS_PROMPT = """\
I hold two thoughts at once:
"{belief_a}"
"{belief_b}"
In one sentence, what new insight do I notice?\
"""


class BeliefSynergizer:

    def __init__(
        self,
        beliefs_writer: Writer,
        beliefs_reader: Reader,
        voice_client: VoiceClient,
        errors_channel=None,
    ) -> None:
        self._writer = beliefs_writer
        self._reader = beliefs_reader
        self._voice = voice_client
        self._errors = errors_channel or errors

    def synthesize(self) -> Optional[dict]:
        pair = self._select_pair()
        if pair is None:
            return None

        belief_a, belief_b = pair
        prompt = _SYNTHESIS_PROMPT.format(
            belief_a=belief_a["content"],
            belief_b=belief_b["content"],
        )

        try:
            req = VoiceRequest(
                prompt=prompt,
                register=PHILOSOPHICAL,
                max_tokens=80,
                temperature=0.9,
            )
            resp = self._voice.speak(req)
            text = resp.text.strip() if resp and resp.text else ""
        except Exception as exc:
            self._errors.record(
                f"synergizer voice error: {exc}",
                source=_LOG_SOURCE, exc=exc,
            )
            self._log(belief_a["id"], belief_b["id"], None, None)
            return None

        # Extract first sentence — LLMs often ignore "one sentence" instructions
        if text:
            import re as _re
            m = _re.search(r'^(.{20,200}?[.!?])', text, _re.DOTALL)
            if m:
                text = m.group(1).strip()

        if not text or len(text) > 200:
            self._log(belief_a["id"], belief_b["id"], None, None)
            return None

        if not self._quality_check(text):
            self._log(belief_a["id"], belief_b["id"], None, None)
            return None

        result_id = self._writer.write(
            "INSERT INTO beliefs "
            "(content, tier, confidence, created_at, source, branch_id, locked) "
            "VALUES (?, 6, 0.65, ?, 'synergized', 'systems', 0)",
            (text, time.time()),
        )
        self._log(belief_a["id"], belief_b["id"], text, result_id)
        self._errors.record(
            f"synergizer: new belief {result_id!r}: {text[:80]}",
            source=_LOG_SOURCE, level="INFO",
        )
        # Diversity ecology: grade collision + record lineage
        try:
            from theory_x.diversity.grader import CrossbreedGrader
            from theory_x.diversity.boost import apply_boost, BOOST_THRESHOLD
            from theory_x.diversity.lineage import record_synergy
            record_synergy(self._writer, result_id, belief_a["id"], belief_b["id"])
            grader = CrossbreedGrader(self._writer, self._reader)
            grade = grader.grade(result_id, belief_a["id"], belief_b["id"])
            if grade is not None and grade > BOOST_THRESHOLD:
                apply_boost(self._writer, result_id, grade)
                self._errors.record(
                    f"boost_applied: belief_id={result_id} grade={grade:.3f} "
                    f"boost_value={1.0 + grade:.2f}",
                    source=_LOG_SOURCE, level="INFO",
                )
        except Exception as _de:
            self._errors.record(f"diversity grading failed: {_de}", source=_LOG_SOURCE)
        return {
            "content": text,
            "belief_id_a": belief_a["id"],
            "belief_id_b": belief_b["id"],
        }

    # ------------------------------------------------------------------

    # Seed sources used as anchor beliefs for synthesis
    _ANCHOR_SOURCES = frozenset({"koan", "tao", "dont_know", "keystone_seed",
                                  "heart_sutra", "self_location",
                                  "reification_recognition"})
    # Generated sources that provide fresh material
    _FRESH_SOURCES = frozenset({"fountain_insight", "synergized",
                                 "behavioural_observation"})

    def _select_pair(self) -> Optional[tuple[dict, dict]]:
        # Include locked seed beliefs (koans, keystones) — rich, philosophically
        # diverse candidates. Exclude low-quality URL stubs.
        rows = self._reader.read(
            "SELECT id, content, branch_id, confidence, created_at, source "
            "FROM beliefs "
            "WHERE source NOT IN ('precipitated_from_dynamic') "
            "AND confidence > 0.5"
        )
        if not rows:
            return None

        recent_ids: set[int] = set()
        try:
            log_rows = self._reader.read(
                "SELECT belief_id_a, belief_id_b FROM synergizer_log "
                "ORDER BY ts DESC LIMIT 20"
            )
            for lr in log_rows:
                recent_ids.add(lr["belief_id_a"])
                recent_ids.add(lr["belief_id_b"])
        except Exception:
            pass

        all_beliefs = [dict(r) for r in rows]

        # Partition into anchors (seeds) and fresh (generated)
        anchors = [b for b in all_beliefs if b["source"] in self._ANCHOR_SOURCES]
        fresh = [b for b in all_beliefs if b["source"] in self._FRESH_SOURCES]

        best_score = -1.0
        best_pair: Optional[tuple[dict, dict]] = None

        def _score(ba, bb) -> float:
            avg_conf = (ba["confidence"] + bb["confidence"]) / 2.0
            rec_w = 0.5 if (ba["id"] in recent_ids or bb["id"] in recent_ids) else 1.0
            return avg_conf * rec_w

        # Preferred: anchor × fresh (seed wisdom + lived observation)
        if anchors and fresh:
            for ba in anchors:
                for bb in fresh:
                    s = _score(ba, bb)
                    if s > best_score:
                        best_score = s
                        best_pair = (ba, bb)
            return best_pair

        # Fallback: cross-branch among whatever we have
        by_branch: dict[str, list[dict]] = {}
        for b in all_beliefs:
            br = b["branch_id"] or "unknown"
            by_branch.setdefault(br, []).append(b)
        branch_list = list(by_branch.items())
        if len(branch_list) >= 2:
            for i, (_, ba_list) in enumerate(branch_list):
                for _, bb_list in branch_list[i + 1:]:
                    for ba in ba_list:
                        for bb in bb_list:
                            s = _score(ba, bb)
                            if s > best_score:
                                best_score = s
                                best_pair = (ba, bb)
            if best_pair:
                return best_pair

        # Last resort: temporally distant within single pool, avoid same source
        all_beliefs.sort(key=lambda b: b["created_at"])
        n = len(all_beliefs)
        for i in range(min(10, n // 2)):
            ba = all_beliefs[i]
            bb = all_beliefs[n - 1 - i]
            if ba["id"] != bb["id"] and ba["source"] != bb["source"]:
                s = _score(ba, bb) * 0.7
                if s > best_score:
                    best_score = s
                    best_pair = (ba, bb)

        return best_pair

    def _quality_check(self, text: str) -> bool:
        if not text:
            return False
        if text.lower().strip() == "nothing":
            return False
        if len(text) < 20 or len(text) > 200:
            return False

        # Blacklist check
        try:
            from theory_x.stage3_world_model.promotion import BeliefPromoter  # noqa: F401
            bl_rows = self._reader.read(
                "SELECT pattern FROM belief_blacklist"
            )
            tl = text.lower()
            for row in bl_rows:
                if row["pattern"].lower() in tl:
                    return False
        except Exception:
            pass

        # Duplicate check — keyword overlap < 0.7
        try:
            existing = self._reader.read(
                "SELECT content FROM beliefs ORDER BY created_at DESC LIMIT 200"
            )
            new_words = set(text.lower().split())
            if not new_words:
                return False
            for row in existing:
                ex_words = set(row["content"].lower().split())
                if not ex_words:
                    continue
                overlap = len(new_words & ex_words) / len(new_words | ex_words)
                if overlap >= 0.7:
                    return False
        except Exception:
            pass

        return True

    def _log(
        self,
        id_a: int,
        id_b: int,
        content: Optional[str],
        result_id: Optional[int],
    ) -> None:
        try:
            self._writer.write(
                "INSERT INTO synergizer_log "
                "(ts, belief_id_a, belief_id_b, result_content, result_belief_id) "
                "VALUES (?, ?, ?, ?, ?)",
                (time.time(), id_a, id_b, content, result_id),
            )
        except Exception as exc:
            self._errors.record(
                f"synergizer log error: {exc}", source=_LOG_SOURCE, exc=exc
            )
