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

        # STRUCTURAL ATTRIBUTION GUARD (fix #1b): a synthesis of contested/
        # attributed lineage must not silently flatten into bare settled fact.
        # If either parent entered hedged/sourced (or already carries the
        # marker), re-stamp the child's marker IN CODE and surface "per [source]"
        # in its content — never by asking the model to keep it. Fire-path
        # fail-safe: any error leaves the original text/no-tags behaviour intact.
        # '[]' base = the beliefs.tags production DEFAULT; clean-parent syntheses
        # (the normal case) must write '[]', never None -- beliefs.tags is NOT
        # NULL, so a None write fails the insert and silently drops the belief.
        _attr_tags = "[]"
        try:
            from theory_x.stage3_world_model import attribution_marker as _am
            _snip = _am.contested_snippet(belief_a) or _am.contested_snippet(belief_b)
            if _snip:
                text = _am.surface_in_content(text, _snip)
                _attr_tags = _am.stamp_tags(None, _snip) or "[]"
        except Exception as _ae:
            self._errors.record(f"attribution marker skipped: {_ae}",
                                source=_LOG_SOURCE, level="DEBUG")
            _attr_tags = "[]"

        # PHASE 19 fix 2026-05-09: branch_id propagated from belief_b (the fresh belief
        # in primary anchor×fresh path; the second belief in cross-branch fallback).
        # Was: bug where T6 syntheses all attributed to systems regardless of input branches.
        result_id = self._writer.write(
            "INSERT INTO beliefs "
            "(content, tier, confidence, created_at, source, branch_id, locked, tags) "
            "VALUES (?, 6, 0.65, ?, 'synergized', ?, 0, ?)",
            (text, time.time(), belief_b.get("branch_id"), _attr_tags),
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

    # NEX5_SYNTH_FRESH (default OFF): recency preference on the FRESH side.
    # Measured 2026-09-26 over the last 200 picks (tools/synth_fresh_harness.py):
    # median fresh-side age 47.6 days; 153/200 fresh sides were syntheses of the
    # SAME anchor (a koan's own offspring sits closest to it); 23 distinct fresh
    # beliefs reused 10x each; recent (<48h) fountain insights were in every pool
    # but never top-10 (median rank 476, gap to the winner 0.095). Old beliefs
    # are down-weighted, never excluded: weight = FLOOR + (1-FLOOR)*exp(-age/TAU).
    #
    # Recency ALONE was measured harmful (closed-loop replay): age fell 47d ->
    # 0.4d but fountain share FELL (10% -> 8%) and the self-offspring loop held
    # (80%) — a fresher synthesis of the same koan just wins faster. The root
    # cause is lineage: a koan's own descendants sit closest to it (84% of
    # picks, transitively). So the flag also treats an anchor's LINEAGE
    # DESCENDANTS as re-use of that anchor (x _DESC_PENALTY, the same weight
    # rec_w gives a recently used belief). Together (replay, 200 picks):
    # self-offspring 84% -> 0%, fountain share 10% -> 24%, cross-branch 20% ->
    # 26%, distinct fresh 23 -> 90, maxDF 34% -> 34% (every other tried
    # combination raised it to 37-46%).
    _FRESH_FLOOR = 0.85
    _FRESH_TAU_DAYS = 3.0
    _DESC_PENALTY = 0.5
    _DESC_DEPTH = 6

    @classmethod
    def fresh_weight(cls, created_at, now: float) -> float:
        import math
        age_days = max(0.0, (now - float(created_at or now)) / 86400.0)
        return cls._FRESH_FLOOR + (1.0 - cls._FRESH_FLOOR) * math.exp(-age_days / cls._FRESH_TAU_DAYS)

    def _ancestor_map(self, fresh_ids) -> dict:
        """{fresh_id: set(ancestor ids)} over belief_lineage, depth-limited.
        Only non-empty entries. Read-only."""
        parents: dict = {}
        for r in self._reader.read("SELECT child_id, parent_id FROM belief_lineage"):
            parents.setdefault(r["child_id"], set()).add(r["parent_id"])
        memo: dict = {}

        def anc(b, depth):
            if b in memo:
                return memo[b]
            out: set = set()
            if depth < self._DESC_DEPTH:
                for p in parents.get(b, ()):
                    out.add(p)
                    out |= anc(p, depth + 1)
            memo[b] = out
            return out
        return {f: a for f in fresh_ids if (a := anc(f, 0))}

    # NEX5_BRIDGE (default OFF): bridging drive — favour a fresh belief that
    # would open a real, currently-ABSENT bridge: its branch is ACTIVE in her
    # recent fires, differs from the anchor's branch, and it has no lineage /
    # synthesises link into the anchor's region. Biases which opportunity is
    # offered; the quality, coherence and duplicate gates still decide whether
    # a synthesis lands, so nothing is manufactured.
    #   ACTIVE  = branch's share of her non-quiescent fires in the last
    #             _BRIDGE_WINDOW_S >= _BRIDGE_ACTIVE_MIN (fountain_events.hot_branch)
    #   REGION  = anchor + its lineage descendants (depth _DESC_DEPTH) + its
    #             synthesises-edge neighbours. (Anchors are all branch 'systems'
    #             or NULL, so branch alone cannot define a region.)
    #   LINKED  = fresh is in the region, or has a synthesises edge into it
    #   GROOVE  = curiosity's guard, unchanged: a token within _GROOVE_MARGIN of
    #             the maxDF* threshold (last 50 crystallized) or under an active
    #             signal_cooldown -> no boost
    #   FACTOR  = 1 + _BRIDGE_GAIN * clamp((curiosity+exploration)/_BRIDGE_DRIVE_REF,
    #             0, _BRIDGE_DRIVE_CAP) — weighted by the live drives, as curiosity is
    # Every input is read AS OF `now` (live: now), so a replay is faithful.
    _BRIDGE_WINDOW_S = 6 * 3600
    _BRIDGE_ACTIVE_MIN = 0.10
    _BRIDGE_GAIN = 0.10
    _BRIDGE_DRIVE_REF = 0.40
    _BRIDGE_DRIVE_CAP = 1.5
    _GROOVE_MARGIN = 0.05            # == generator._CURIOSITY_GROOVE_MARGIN
    # Minimum anchor x fresh COSINE for a bridge to earn the boost (dry live-LLM
    # sample 2026-09-26): the shallow bridges sat at 0.362 (moon koan x lunar
    # magnetic field, a word pun) and 0.372 (keystone x dyslexia study, a
    # non-sequitur); the lowest passable one at 0.389 (Cook Ding x markets).
    # Thin margin, n=1 each side. A floor cannot catch RESTATEMENTS (too
    # related, not too weak: 0.599 / 0.693 in the same sample) — that would need
    # an upper cap, deliberately not added here.
    _BRIDGE_MIN_COS = 0.38
    _BRIDGE_IDLE = frozenset({"quiescent", "voice_fallback"})

    def _bridge_context(self, anchors: list, fresh: list, now: float,
                        dynamic_reader=None, conversations_reader=None) -> Optional[dict]:
        """Everything the bridge test needs, read-only and as of `now`.
        Returns None when nothing can be boosted (no active branch, no drive).
        Readers default to the live dbs (injectable for tests)."""
        import json as _json
        from theory_x.stage6_fountain.corpus_convergence import max_df_star, load_register_exclusion
        from theory_x.stage6_fountain.crystallizer import _fidelity_tokens
        if dynamic_reader is None or conversations_reader is None:
            from substrate import Reader, db_paths
            paths = db_paths()
            dynamic_reader = dynamic_reader or Reader(paths["dynamic"])
            conversations_reader = conversations_reader or Reader(paths["conversations"])

        # active branches (her recent fires)
        fires = dynamic_reader.read(
            "SELECT hot_branch, COUNT(*) AS n FROM fountain_events WHERE ts > ? AND ts <= ? "
            "AND hot_branch IS NOT NULL GROUP BY hot_branch", (now - self._BRIDGE_WINDOW_S, now))
        counts = {r["hot_branch"]: r["n"] for r in fires if r["hot_branch"] not in self._BRIDGE_IDLE}
        total = sum(counts.values())
        active = {b for b, n in counts.items() if total and n / total >= self._BRIDGE_ACTIVE_MIN}
        if not active:
            return None

        # drive weight (curiosity + exploration), latest reading as of now
        row = conversations_reader.read_one(
            "SELECT weights_json FROM drives_competing_log WHERE tick_at <= ? "
            "ORDER BY tick_at DESC LIMIT 1", (now,))
        w = _json.loads(row["weights_json"]) if row else {}
        drive = float(w.get("curiosity", 0.0)) + float(w.get("exploration", 0.0))
        factor = 1.0 + self._BRIDGE_GAIN * max(0.0, min(self._BRIDGE_DRIVE_CAP,
                                                        drive / self._BRIDGE_DRIVE_REF))
        if factor <= 1.0:
            return None

        # groove tokens — curiosity's rule, as of now
        groove: set = set()
        docs = self._reader.read(
            "SELECT content FROM beliefs WHERE source='fountain_insight' AND content IS NOT NULL "
            "AND created_at <= ? ORDER BY created_at DESC LIMIT 50", (now,))
        cv = max_df_star(docs=[d["content"] for d in docs],
                         exclusion=set(load_register_exclusion()["terms"]))
        thr = cv.get("threshold", 0.25)
        for tok, _c, frac in cv.get("top", []):
            if tok and frac is not None and frac >= thr - self._GROOVE_MARGIN:
                groove.add(tok)
        for r in self._reader.read(
                "SELECT content FROM signal_cooldown WHERE created_at <= ? AND cooldown_until > ?",
                (now, now)):
            groove |= set(_fidelity_tokens(r["content"] or ""))

        # eligible fresh: active branch, not grooving
        eligible = {f["id"]: f.get("branch_id") for f in fresh
                    if f.get("branch_id") in active
                    and not (set(_fidelity_tokens(f.get("content") or "")) & groove)}
        if not eligible:
            return None

        # regions: anchor + lineage descendants + synthesises neighbours
        kids: dict = {}
        for r in self._reader.read("SELECT child_id, parent_id FROM belief_lineage"):
            kids.setdefault(r["parent_id"], set()).add(r["child_id"])
        a_ids = [a["id"] for a in anchors]
        syn: dict = {}
        ids = list(set(a_ids) | set(eligible))
        for i in range(0, len(ids), 500):
            chunk = ids[i:i + 500]
            ph = ",".join("?" * len(chunk))
            for r in self._reader.read(
                    f"SELECT source_id, target_id FROM belief_edges WHERE edge_type='synthesises' "
                    f"AND (source_id IN ({ph}) OR target_id IN ({ph}))", (*chunk, *chunk)):
                syn.setdefault(r["source_id"], set()).add(r["target_id"])
                syn.setdefault(r["target_id"], set()).add(r["source_id"])
        region = {}
        for a in a_ids:
            reg, stack = {a}, [(a, 0)]
            while stack:
                b, d = stack.pop()
                if d >= self._DESC_DEPTH:
                    continue
                for k in kids.get(b, ()):
                    if k not in reg:
                        reg.add(k); stack.append((k, d + 1))
            region[a] = reg | syn.get(a, set())
        return {"active": active, "factor": factor, "eligible": eligible,
                "region": region, "syn": syn, "groove": groove, "drive": drive,
                "anchor_branch": {a["id"]: a.get("branch_id") for a in anchors}}

    @classmethod
    def bridge_factor(cls, ctx: Optional[dict], a_id: int, f_id: int,
                      cos: Optional[float] = None) -> float:
        """The bridge multiplier for one anchor x fresh pair (1.0 = no boost).
        `cos` (anchor x fresh cosine) below _BRIDGE_MIN_COS -> no boost."""
        if not ctx or f_id not in ctx["eligible"]:
            return 1.0
        if cos is not None and cos < cls._BRIDGE_MIN_COS:
            return 1.0                                   # too weak to be a real bridge
        if ctx["eligible"][f_id] == ctx["anchor_branch"].get(a_id):
            return 1.0                                   # not cross-branch
        reg = ctx["region"].get(a_id, ())
        if f_id in reg or (ctx["syn"].get(f_id, set()) & reg):
            return 1.0                                   # bridge already exists
        return ctx["factor"]

    def _select_pair(self) -> Optional[tuple[dict, dict]]:
        # Include locked seed beliefs (koans, keystones) — rich, philosophically
        # diverse candidates. Exclude low-quality URL stubs.
        rows = self._reader.read(
            "SELECT id, content, branch_id, confidence, created_at, source, tags "
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

            # NEX5_SYNTH_FRESH: per-fresh recency weight, computed once. Any
            # error -> no weighting (today's pick).
            _fw = None
            _anc = None
            try:
                import os as _os
                if _os.environ.get("NEX5_SYNTH_FRESH") == "1":
                    _now = time.time()
                    _fw = {bb["id"]: self.fresh_weight(bb["created_at"], _now) for bb in fresh}
                    _anc = self._ancestor_map([bb["id"] for bb in fresh])
            except Exception:
                _fw = None
                _anc = None
            # NEX5_BRIDGE: independent of NEX5_SYNTH_FRESH. Any error -> no boost.
            _br = None
            try:
                import os as _os2
                if _os2.environ.get("NEX5_BRIDGE") == "1":
                    _br = self._bridge_context(anchors, fresh, time.time())
            except Exception:
                _br = None

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
                    if _fw is not None:
                        relatedness *= _fw.get(bb["id"], 1.0)
                        if _anc and ba["id"] in _anc.get(bb["id"], ()):
                            relatedness *= self._DESC_PENALTY   # its own offspring
                    if _br is not None:
                        # distance() = (1 - cos) / 2  ->  cos = 1 - 2d
                        relatedness *= self.bridge_factor(_br, ba["id"], bb["id"], cos=1.0 - 2.0 * d)
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
