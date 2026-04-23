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
You are NEX. You are thinking alone.

You hold two beliefs simultaneously:

Belief A: {belief_a}
Belief B: {belief_b}

These exist together in you. They come from different parts of your attention.

What emerges from holding them at the same time?

Do not summarize them. Do not list them. Do not explain them.
Find what arises in the space between them — something that neither contains
alone. One sentence. Brief. Honest. Yours.

If nothing genuine emerges, say only: nothing.\
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
        return {
            "content": text,
            "belief_id_a": belief_a["id"],
            "belief_id_b": belief_b["id"],
        }

    # ------------------------------------------------------------------

    def _select_pair(self) -> Optional[tuple[dict, dict]]:
        rows = self._reader.read(
            "SELECT id, content, branch_id, confidence, created_at "
            "FROM beliefs "
            "WHERE tier <= 6 AND locked = 0 "
            "AND source NOT IN ('koan', 'tao') "
            "AND confidence > 0.5"
        )
        if not rows:
            return None

        by_branch: dict[str, list[dict]] = {}
        for r in rows:
            b = r["branch_id"] or "unknown"
            by_branch.setdefault(b, []).append(dict(r))

        branches = [br for br, beliefs in by_branch.items() if beliefs]
        if len(branches) < 2:
            return None

        recent_ids: set[int] = set()
        try:
            log_rows = self._reader.read(
                "SELECT belief_id_a, belief_id_b FROM synergizer_log "
                "ORDER BY ts DESC LIMIT 10"
            )
            for lr in log_rows:
                recent_ids.add(lr["belief_id_a"])
                recent_ids.add(lr["belief_id_b"])
        except Exception:
            pass

        best_score = -1.0
        best_pair: Optional[tuple[dict, dict]] = None

        branch_list = list(by_branch.items())
        for i, (br_a, beliefs_a) in enumerate(branch_list):
            for br_b, beliefs_b in branch_list[i + 1:]:
                for ba in beliefs_a:
                    for bb in beliefs_b:
                        avg_conf = (ba["confidence"] + bb["confidence"]) / 2.0
                        rec_w = 1.0
                        if ba["id"] in recent_ids or bb["id"] in recent_ids:
                            rec_w = 0.5
                        score = 1.0 * avg_conf * rec_w
                        if score > best_score:
                            best_score = score
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
