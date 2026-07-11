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
        coherence_gate=None,
    ) -> None:
        self._writer = beliefs_writer
        self._reader = beliefs_reader
        self._voice = voice_client
        self._errors = errors_channel or errors
        self._gate = coherence_gate

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

        # Phase 22 — Coherence Gate (runs after quality gate, before INSERT)
        if self._gate is not None:
            from theory_x.stage_gate.coherence_gate import ThoughtPacket, GateOutcome
            packet = ThoughtPacket(
                content=text,
                source_node="synergizer",
                confidence=0.65,
                branch_id=belief_b.get("branch_id"),
            )
            decision = self._gate.check(packet)
            if decision.outcome != GateOutcome.ACCEPT:
                self._errors.record(
                    f"Synergizer gate {decision.outcome.value} ({decision.reason}): {text[:60]}",
                    source=_LOG_SOURCE, level="INFO",
                )
                self._log(belief_a["id"], belief_b["id"], None, None)
                return None

        # PHASE 19 fix 2026-05-09: branch_id propagated from belief_b (the fresh belief
        # in primary anchor×fresh path; the second belief in cross-branch fallback).
        # Was: bug where T6 syntheses all attributed to systems regardless of input branches.
        result_id = self._writer.write(
            "INSERT INTO beliefs "
            "(content, tier, confidence, created_at, source, branch_id, locked) "
            "VALUES (?, 6, 0.65, ?, 'synergized', ?, 0)",
            (text, time.time(), belief_b.get("branch_id")),
        )
        self._log(belief_a["id"], belief_b["id"], text, result_id)
        self._errors.record(
            f"synergizer: new belief {result_id!r}: {text[:80]}",
            source=_LOG_SOURCE, level="INFO",
        )
        # Record lineage only — no boost for synergized.
        # Boost projected synergized ~1.2-1.4 days into the future via BOOST_TIME_BONUS_SECONDS,
        # making them outrank genuinely-newer sense beliefs in retrieval even with sense cap=5
        # (the oversample itself was dominated by future-projected synergized). Synergized are
        # derivative re-syntheses of content the fountain already read, not fresh perceptions —
        # giving them a time advantage created a closed loop.
        # See 2026-05-13/14 session diagnosis.
        try:
            from theory_x.diversity.lineage import record_synergy
            record_synergy(self._writer, result_id, belief_a["id"], belief_b["id"])
        except Exception as _de:
            self._errors.record(f"diversity lineage failed: {_de}", source=_LOG_SOURCE)
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
    # Below this embedding distance, treat a fresh belief as a near-duplicate
    # restatement of the anchor rather than a genuine pairing candidate.
    # Raised 0.05 -> 0.15 (session 24): live distance distribution showed
    # 0.05 let verbatim-duplicate (0.068) and near-paraphrase (0.137) pairs
    # through, giving the LLM nothing to synthesize. 0.15 excludes those
    # while preserving genuinely distinct pairs (e.g. the flag/wind koan at
    # 0.189). Does NOT fix the separate templated-cluster problem around
    # anchors 98/135 -- see commit message.
    _MIN_RELATEDNESS_DISTANCE = 0.15

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

        # Preferred: anchor × fresh, selected by SEMANTIC RELATEDNESS.
        # Session 22/23: the old avg_conf*rec_w score is ~99.5% tied
        # (confidence is a fixed per-source default), so with no ORDER BY the
        # strict-> argmax always won on lowest rowid — the same ~20 beliefs
        # (263-283) recycled forever regardless of content. Relatedness
        # replaces confidence as the selector; rec_w (recent-pair penalty)
        # carries over unchanged so the same pair isn't picked every tick.
        # Ties broken by recency (most-recent fresh belief iterated first,
        # strict >) not rowid, so the groove can't reform even on an exact tie.
        if anchors and fresh:
            from theory_x.diversity.embeddings import embed_belief, distance

            fresh_sorted = sorted(fresh, key=lambda b: b["created_at"], reverse=True)
            fresh_vecs = [
                (bb, embed_belief(bb["id"], bb["content"])) for bb in fresh_sorted
            ]

            best_relatedness = -1.0
            for ba in anchors:
                a_vec = embed_belief(ba["id"], ba["content"])
                for bb, b_vec in fresh_vecs:
                    d = distance(a_vec, b_vec)
                    if d < self._MIN_RELATEDNESS_DISTANCE:
                        # Near-duplicate guard: don't pair a belief with a
                        # restatement of itself.
                        continue
                    rec_w = 0.5 if (ba["id"] in recent_ids or bb["id"] in recent_ids) else 1.0
                    relatedness = (1.0 - d) * rec_w
                    if relatedness > best_relatedness:
                        best_relatedness = relatedness
                        best_pair = (ba, bb)
            if best_pair:
                return best_pair
            # Every anchor × fresh candidate was filtered as a near-duplicate —
            # fall through to the cross-branch fallback below.

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
