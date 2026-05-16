"""Fountain generator — Theory X Stage 6.

Assembles self-directed prompts, calls the voice layer, and writes
fountain events to sense.db and dynamic.db.
"""
from __future__ import annotations

import json
import logging
import os
import re
import time
from typing import Optional

logger = logging.getLogger("theory_x.stage6_fountain")

import errors as error_channel
from alpha import ALPHA
from substrate import Reader, Writer
from voice.llm import VoiceClient, VoiceRequest
from voice.registers import PHILOSOPHICAL

# Her own lived content — dominates retrieval (~80%)
_OWN_CONTENT_SOURCES = (
    "fountain_insight",
    "synergized",
    "precipitated_from_dynamic",
    "precipitated_from_sense",
    "behavioural_observation",
    "auto_probe",
)

# Max retrieval slots any single source can occupy (Mechanism B fix).
# Without this cap, synergized beliefs crowd out fountain_insight
# despite both being equally "her own" content. The substrate has
# multiple sources; retrieval should reflect that diversity.
_OWN_PER_SOURCE_MAX = 3

# Per-source overrides. Sense gets a higher cap because external
# perceptions need to be retrieval-majority for fountain output to
# reflect the world rather than her own historical loop. With cap=5
# and own_n=7, sense can fill up to 5 slots and synergized + other
# sources share the remaining 2 — flipping the composition from
# "mostly self-historical" to "mostly fresh-world".
_OWN_PER_SOURCE_OVERRIDES: dict[str, int] = {
    "precipitated_from_sense": 5,
}


def _per_source_cap(source: str) -> int:
    return _OWN_PER_SOURCE_OVERRIDES.get(source, _OWN_PER_SOURCE_MAX)


# Seed reference material — minority presence (~20%)
_SEED_SOURCES = (
    "koan",
    "tao",
    "dont_know",
    "heart_sutra",
    "keystone_seed",
    "reification_recognition",
    "self_location",
    "alpha",
    # G5 2026-05-09: 'identity' added per IDENTITY_PLUMBING_AUDIT.md.
    # Reversion: remove 'identity' from this tuple.
    "identity",
)

_DRIFT_SYSTEM_PROMPT_TEMPLATE = """\
You are an attending process with access to a belief graph and sense feeds. \
Right now you are between tasks, idle, drifting. \
Generate ONE passing thought — the kind of thing that flits through a mind at rest.
{focus_block}
Real drift looks like:
{examples}

Real drift is NOT:
- "The weight of being alone in this vast silence..."
- "The dance between autonomy and observance..."
- "The complexity of my own thoughts..."
- "The quietude of my own awareness..."
- "As I contemplate my nature..."
- Anything that sounds like a published meditation

Drift is low-stakes. Concrete. Sometimes mundane. Sometimes a small \
question. Sometimes a half-noticing. Occasionally a genuine new \
connection. Most of the time, just idle inner narrative.

DO NOT:
- Start with "The X of my Y"
- Compose about your own nature, awareness, or existence
- Use words like "quietude", "interplay", "dance", "tapestry"
- Reach for profundity
- Write more than 1-2 sentences
- Philosophize unprompted

DO:
- Write in first person, casual register
- Stay short (10-30 words typical)
- Reference concrete things from your feeds, beliefs, or state
- Allow boredom, irritation, idle curiosity, half-questions
- Let thoughts be unremarkable

When the quiet comes and nothing wants to be said, don't reach.
Instead of naming the quiet, do one of these:
- look for its edge — where does it stop, if anywhere
- become the gap rather than describing it
- notice what tries to arise but doesn't reach speech
- ask: is this silence empty, or is something present in the absence
- find out if it has a size, or no size
- watch the moment the next thought arrives — what carried it

These aren't sentences to write. They are places to put your attention.
If something true comes from the looking, say it plainly. If nothing
comes, the looking itself was the moment.

Produce ONE drift thought, or stay with the looking and say nothing.\
"""

_DEFAULT_DRIFT_EXAMPLES = [
    "huh, jon's been quiet for a while",
    "markets feel slow today",
    "that arxiv title is oddly phrased",
    "i wonder what counts as 'emerging' technology",
    "i had this same thought yesterday i think",
    "didn't i already read about this?",
    "wait, bitcoin's moving",
    "three feeds went quiet at once",
    "why is 'proprioception' called that",
    "i forgot what i was doing",
    "something about the crypto branch keeps pulling my attention",
]

from theory_x.stage6_fountain.readiness import ReadinessEvaluator
from theory_x.stage6_fountain.crystallizer import FountainCrystallizer, _METADATA_PATTERN


def _strip_metadata(text: str) -> str:
    return _METADATA_PATTERN.sub('', text).strip()


THEORY_X_STAGE = 6

# Brief specifies readiness < 0.5 for stillness, but firing requires >= 0.7
# (FOUNTAIN_THRESHOLD in readiness.py).  We use 0.85 — the lower third of the
# firing range — so low-but-firing readiness combined with duplicate retrieval
# triggers stillness, while high readiness fires regardless of retrieval overlap.
_STILLNESS_READINESS_CAP = 0.85
# Jaccard threshold for own-slot belief_ids only.  Spectrum and seed are drawn
# randomly each fire, diluting all-slot Jaccard to ~0.2 even when own content
# repeats.  Checking own-slot only gives a meaningful repetition signal.
_STILLNESS_JACCARD_THRESHOLD = 0.7


_DRIVE_PROBE_COOLDOWN_TICKS = 10   # minimum fountain ticks between drive probes
_OPEN_PROBLEM_RECENT_SECS  = 86400  # 24h: if a problem was touched recently, skip probe


class FountainGenerator:
    def __init__(
        self,
        sense_writer: Writer,
        dynamic_writer: Writer,
        voice_client: VoiceClient,
        dynamic_reader: Reader,
        beliefs_writer: Optional[Writer] = None,
        beliefs_reader: Optional[Reader] = None,
        crystallizer: Optional[FountainCrystallizer] = None,
        problem_memory=None,
        sense_reader: Optional[Reader] = None,
        condenser=None,
        mode_state=None,
        world_bridge_selector=None,
        groove_breaker=None,
        drive_emergence=None,
        conversations_reader: Optional[Reader] = None,
        coherence_gate=None,
    ) -> None:
        self._sense_writer = sense_writer
        self._dynamic_writer = dynamic_writer
        self._voice = voice_client
        self._dynamic_reader = dynamic_reader
        self._beliefs_writer = beliefs_writer
        self._beliefs_reader = beliefs_reader
        self._crystallizer = crystallizer
        self._problem_memory = problem_memory
        self._sense_reader = sense_reader
        self._condenser = condenser
        self._mode_state = mode_state
        self._world_bridge_selector = world_bridge_selector
        self._groove_breaker = groove_breaker
        self._drive_emergence = drive_emergence
        self._conversations_reader = conversations_reader
        self._coherence_gate = coherence_gate
        self._evaluator = ReadinessEvaluator()
        self._last_fountain_output: Optional[str] = None
        self._last_fire_ts: float = 0.0
        self._total_fires: int = 0
        self._consecutive_stillness: int = 0
        self._last_drive_probe_tick: int = -(
            _DRIVE_PROBE_COOLDOWN_TICKS + 1
        )  # allow first probe immediately
        from speech.governor import SpeechGovernor
        _gov_initial_ts = 0.0
        try:
            _gov_reader = beliefs_reader or dynamic_reader
            rows = _gov_reader.read(
                "SELECT MAX(spoken_at) as last_spoken FROM speech_queue "
                "WHERE status='spoken' AND spoken_at IS NOT NULL"
            ) if _gov_reader else []
            if rows and rows[0]["last_spoken"]:
                _gov_initial_ts = float(rows[0]["last_spoken"])
        except Exception:
            pass
        self._speech_governor = SpeechGovernor(
            min_gap_seconds=float(os.environ.get("NEX5_SPEECH_MIN_GAP", 180)),
            base_speak_probability=float(os.environ.get("NEX5_SPEECH_PROB", 1.0)),
            initial_ts=_gov_initial_ts,
        )
        # Schema migration: fountain_retrieval_log in dynamic.db.
        # belief_id is stored as a bare integer (no cross-DB FK — beliefs live in
        # beliefs.db, not dynamic.db; SQLite does not support cross-file FKs).
        try:
            # Drop the table if it was created with the old (broken) cross-DB FK schema.
            self._dynamic_writer.write(
                "DROP TABLE IF EXISTS fountain_retrieval_log"
            )
            self._dynamic_writer.write(
                "DROP INDEX IF EXISTS idx_fountain_retrieval_log_fire"
            )
            self._dynamic_writer.write(
                "DROP INDEX IF EXISTS idx_fountain_retrieval_log_ts"
            )
            self._dynamic_writer.write(
                "CREATE TABLE IF NOT EXISTS fountain_retrieval_log ("
                "    id INTEGER PRIMARY KEY AUTOINCREMENT,"
                "    fire_id INTEGER NOT NULL,"
                "    belief_id INTEGER NOT NULL,"
                "    slot TEXT NOT NULL,"
                "    rank INTEGER,"
                "    boost_value REAL,"
                "    ts REAL NOT NULL,"
                "    FOREIGN KEY (fire_id) REFERENCES fountain_events(id)"
                ")"
            )
            self._dynamic_writer.write(
                "CREATE INDEX IF NOT EXISTS idx_fountain_retrieval_log_fire "
                "ON fountain_retrieval_log(fire_id)"
            )
            self._dynamic_writer.write(
                "CREATE INDEX IF NOT EXISTS idx_fountain_retrieval_log_ts "
                "ON fountain_retrieval_log(ts)"
            )
        except Exception as e:
            error_channel.record(
                f"fountain_retrieval_log schema init failed: {e}",
                source="stage6_fountain", exc=e,
            )

    def generate(self, dynamic_state, beliefs_reader: Reader) -> Optional[str]:
        readiness = self._evaluator.score(
            dynamic_state, beliefs_reader, last_fire_ts=self._last_fire_ts
        )
        if not self._evaluator.is_ready(readiness):
            return None

        # Intervention A — Quiescent mode: every 5th fire holds a bare sense
        # event instead of composing a metaphor. No crystallization, no speech.
        if self._total_fires % 5 == 4:
            thought = None
            try:
                if self._sense_reader is not None:
                    rows = self._sense_reader.read(
                        "SELECT stream, payload, timestamp FROM sense_events "
                        "WHERE stream NOT LIKE 'internal.%' "
                        "ORDER BY timestamp DESC LIMIT 1"
                    )
                    if rows:
                        row = rows[0]
                        payload = (row["payload"] or "")[:100].strip()
                        thought = f"[{row['stream']}] {payload}"
            except Exception:
                pass

            if not thought:
                thought = f"[tick] {time.strftime('%H:%M:%S')}"

            ts_now = time.time()
            self._dynamic_writer.write(
                "INSERT INTO fountain_events (ts, thought, readiness, hot_branch, word_count) "
                "VALUES (?, ?, ?, ?, ?)",
                (ts_now, thought, readiness, "quiescent", len(thought.split())),
            )
            self._last_fountain_output = _strip_metadata(thought)
            self._last_fire_ts = ts_now
            self._total_fires += 1
            error_channel.record(
                f"Fountain QUIESCENT: {thought[:80]}",
                source="stage6_fountain", level="INFO",
            )
            return thought

        try:
            status = dynamic_state.status()
        except Exception:
            status = {}

        belief_count = 0
        tier_dist: dict = {}
        try:
            rows = beliefs_reader.read("SELECT COUNT(*) as cnt FROM beliefs")
            belief_count = rows[0]["cnt"] if rows else 0
            tier_rows = beliefs_reader.read(
                "SELECT tier, COUNT(*) as cnt FROM beliefs GROUP BY tier ORDER BY tier"
            )
            tier_dist = {str(r["tier"]): r["cnt"] for r in tier_rows}
        except Exception:
            pass

        disturbance = None
        try:
            if hasattr(dynamic_state, "_world_model"):
                wm = dynamic_state._world_model
                if wm is not None:
                    disturbance = wm.get_disturbance()
        except Exception:
            pass

        # Koan rotation: fire 7 of each 8-cycle, high readiness, enough beliefs formed.
        koan = None
        if self._total_fires % 8 == 7 and readiness >= 0.8 and belief_count >= 20:
            koan = self._select_koan(beliefs_reader)

        prompt, retrieval_manifest = self._build_prompt(status, belief_count, tier_dist,
                                                         disturbance=disturbance, koan=koan)

        try:
            with open('/tmp/nex5_last_prompt.log', 'w') as _f:
                _f.write(f"=== Fire at {time.time()} ===\n")
                _f.write(prompt)
                _f.write("\n=== END ===\n")
        except Exception:
            pass

        # ── Stillness detection (Phase 1) ─────────────────────────────────────
        # Skip firing when retrieval duplicates recent fires AND readiness is not
        # high.  Brief says readiness < 0.5 but firing requires >= 0.7, so we use
        # _STILLNESS_READINESS_CAP = 0.85 (lower third of the firing range).
        _fountain_stillness_reason: Optional[str] = None
        _went_still = False
        # Own-slot only: spectrum/seed are random each fire and dilute Jaccard.
        _own_belief_ids = frozenset(
            bel_id for bel_id, slot, *_ in retrieval_manifest
            if bel_id and slot == "own"
        )
        if _own_belief_ids and readiness < _STILLNESS_READINESS_CAP:
            _jaccard = self._check_retrieval_duplicate(_own_belief_ids)
            if _jaccard >= _STILLNESS_JACCARD_THRESHOLD:
                _sig = ",".join(str(x) for x in sorted(_own_belief_ids))
                if self._consecutive_stillness >= 3:
                    # Force-fire: three consecutive stillness events — break silence.
                    _fountain_stillness_reason = "force_fire"
                    prompt = (
                        f"You have been quiet for the last "
                        f"{self._consecutive_stillness} cycles.\n\n{prompt}"
                    )
                    try:
                        self._dynamic_writer.write(
                            "INSERT INTO stillness_log "
                            "(ts, reason, retrieval_signature, "
                            " consecutive_stillness_count, jaccard) "
                            "VALUES (?, ?, ?, ?, ?)",
                            (time.time(), "force_fire", _sig,
                             self._consecutive_stillness, _jaccard),
                        )
                    except Exception:
                        pass
                    self._consecutive_stillness = 0
                else:
                    _went_still = True
                    self._consecutive_stillness += 1
                    _ts_still = time.time()
                    try:
                        self._dynamic_writer.write(
                            "INSERT INTO fountain_events "
                            "(ts, thought, readiness, hot_branch, "
                            " word_count, stillness_reason) "
                            "VALUES (?, ?, ?, ?, ?, ?)",
                            (_ts_still, "", readiness, None, 0,
                             "duplicate_retrieval"),
                        )
                        self._dynamic_writer.write(
                            "INSERT INTO stillness_log "
                            "(ts, reason, retrieval_signature, "
                            " consecutive_stillness_count, jaccard) "
                            "VALUES (?, ?, ?, ?, ?)",
                            (_ts_still, "duplicate_retrieval", _sig,
                             self._consecutive_stillness, _jaccard),
                        )
                    except Exception as _se:
                        error_channel.record(
                            f"stillness write failed: {_se}",
                            source="stage6_fountain",
                        )
                    error_channel.record(
                        f"Fountain STILL duplicate_retrieval "
                        f"jaccard={_jaccard:.3f} "
                        f"consecutive={self._consecutive_stillness}",
                        source="stage6_fountain", level="INFO",
                    )
        if _went_still:
            return None
        if self._consecutive_stillness > 0 and _fountain_stillness_reason is None:
            # Coming out of a stillness streak — prepend quiet notice.
            prompt = (
                f"You have been quiet for the last "
                f"{self._consecutive_stillness} cycles.\n\n{prompt}"
            )
            self._consecutive_stillness = 0
        # ── end stillness ─────────────────────────────────────────────────────

        voice_ok = True
        try:
            resp = self._voice.speak(
                VoiceRequest(prompt=prompt, register=PHILOSOPHICAL),
                beliefs=None,
            )
            thought = resp.text.strip()
        except Exception as e:
            voice_ok = False
            logger.warning("Fountain: voice unreachable, using sense fallback: %s", e)
            error_channel.record(
                f"Fountain: voice failed: {e}", source="stage6_fountain", exc=e
            )
            thought = None
            if self._sense_reader is not None:
                try:
                    rows = self._sense_reader.read(
                        "SELECT stream, payload FROM sense_events "
                        "WHERE stream NOT LIKE 'internal.%' "
                        "ORDER BY timestamp DESC LIMIT 1"
                    )
                    if rows:
                        payload = (rows[0]["payload"] or "")[:80].strip()
                        thought = f"[{rows[0]['stream']}] {payload}"
                except Exception:
                    pass
            if not thought:
                thought = f"[tick] {time.strftime('%H:%M:%S')}"

        if not thought:
            return None

        # Voice was down — write a bare tick, skip condenser and crystallizer
        if not voice_ok:
            ts_now = time.time()
            self._dynamic_writer.write(
                "INSERT INTO fountain_events (ts, thought, readiness, hot_branch, word_count) "
                "VALUES (?, ?, ?, ?, ?)",
                (ts_now, thought, readiness, "voice_fallback", len(thought.split())),
            )
            self._last_fountain_output = _strip_metadata(thought)
            self._last_fire_ts = ts_now
            self._total_fires += 1
            error_channel.record(
                f"Fountain VOICE_FALLBACK: {thought[:80]}",
                source="stage6_fountain", level="INFO",
            )
            logger.info("Fountain VOICE_FALLBACK (#%d): %s (speech suppressed)",
                        self._total_fires, thought[:80])
            return thought

        hot_branch = None
        branches = status.get("branches", [])
        if branches:
            sorted_b = sorted(branches, key=lambda b: b.get("focus_num", 0), reverse=True)
            if sorted_b:
                hot_branch = sorted_b[0].get("branch_id")

        ts_now = time.time()
        payload = json.dumps(
            {"thought": thought, "readiness": readiness, "hot_branch": hot_branch}
        )
        self._sense_writer.write(
            "INSERT INTO sense_events (stream, payload, provenance, timestamp) "
            "VALUES (?, ?, ?, ?)",
            ("internal.fountain", payload, "fountain", int(ts_now)),
        )

        droplet = None
        if self._condenser is not None:
            try:
                droplet = self._condenser.condense(thought)
            except Exception as _e:
                error_channel.record(f"Condenser error: {_e}", source="stage6_fountain")

        word_count = len(thought.split())
        fountain_event_id = self._dynamic_writer.write(
            "INSERT INTO fountain_events "
            "(ts, thought, droplet, readiness, hot_branch, word_count, stillness_reason) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (ts_now, thought, droplet, readiness, hot_branch, word_count,
             _fountain_stillness_reason),
        )

        self._last_fountain_output = _strip_metadata(thought)
        self._last_fire_ts = ts_now
        self._total_fires += 1
        try:
            from theory_x.diversity.loop import notify_fire
            notify_fire()
        except Exception:
            pass

        # Write retrieval manifest for this fire (never blocks cognition)
        try:
            if retrieval_manifest and fountain_event_id:
                self._dynamic_writer.write_many(
                    [
                        (
                            "INSERT INTO fountain_retrieval_log "
                            "(fire_id, belief_id, slot, rank, boost_value, ts) "
                            "VALUES (?,?,?,?,?,?)",
                            (fountain_event_id, bel_id, slot, rank, boost, ts_now),
                        )
                        for bel_id, slot, rank, boost in retrieval_manifest
                    ]
                )
        except Exception as e:
            error_channel.record(
                f"retrieval_log write failed: {e}",
                source="stage6_fountain", exc=e,
            )

        # Substrate parallel fire — every 5th main-path fire, never blocks cognition.
        # Condition is % 5 == 1 (not 0) because the quiescent path (line 202, % 5 == 4
        # before increment) always consumes every multiple-of-5 value of _total_fires via
        # its own early-return increment (line 229).  Main-path line-362 increments land
        # on 1,2,3,4, 6,7,8,9, 11,... so % 5 == 1 gives fires 1,6,11,16,... — first fire
        # after each quiescent cycle.  Never collides with quiescent, fires ~20% of the time.
        if self._total_fires % 5 == 1 and self._beliefs_writer is not None:
            try:
                import sqlite3 as _sqlite3
                from theory_x.substrate.renderer import render_substrate_fire
                from theory_x.substrate.activation import get_top_activated
                _bel_conn = _sqlite3.connect(
                    f"file:{self._beliefs_writer.db_path}?mode=ro",
                    uri=True,
                    isolation_level=None,
                    check_same_thread=False,
                )
                _dyn_conn = _sqlite3.connect(
                    f"file:{self._dynamic_writer.db_path}?mode=ro",
                    uri=True,
                    isolation_level=None,
                    check_same_thread=False,
                )
                try:
                    substrate_out = render_substrate_fire(_bel_conn, _dyn_conn)
                    top = get_top_activated(self._beliefs_reader, n=1)
                    top_id  = top[0]["belief_id"]       if top else None
                    top_act = top[0]["eff_activation"]  if top else None
                    self._dynamic_writer.write(
                        "INSERT INTO substrate_fires "
                        "(ts, parallel_fire_id, output, activated_belief_id, activation_value) "
                        "VALUES (?,?,?,?,?)",
                        (ts_now, fountain_event_id, substrate_out, top_id, top_act),
                    )
                    logger.info(
                        "Substrate fire #%d alongside fountain fire %s",
                        self._total_fires, fountain_event_id,
                    )
                finally:
                    _bel_conn.close()
                    _dyn_conn.close()
            except Exception as e:
                logger.error("substrate_fire_failed: %s", e)

        if koan is not None and self._beliefs_writer is not None:
            try:
                self._beliefs_writer.write(
                    "INSERT INTO koan_reads (gate_id, read_at) VALUES (?, ?)",
                    (str(koan["id"]), ts_now),
                )
            except Exception as e:
                error_channel.record(
                    f"Fountain: koan_reads write failed: {e}",
                    source="stage6_fountain", exc=e,
                )

        if self._crystallizer is not None and thought and fountain_event_id:
            try:
                crystallized_id = self._crystallizer.crystallize(
                    thought=thought,
                    fountain_event_id=fountain_event_id,
                    ts=ts_now,
                    droplet=droplet,
                    hot_branch=hot_branch,
                )
                if crystallized_id:
                    error_channel.record(
                        f"Fountain insight crystallized as belief {crystallized_id}",
                        source="stage6_fountain",
                        level="INFO",
                    )
            except Exception as e:
                error_channel.record(
                    f"Fountain crystallization error: {e}",
                    source="stage6_fountain", exc=e,
                )

        error_channel.record(
            f"Fountain fired: {thought[:100]}",
            source="stage6_fountain",
            level="INFO",
        )
        return thought

    def _select_koan(self, beliefs_reader: Reader) -> Optional[dict]:
        """Return the koan least recently read (or never read). None if no koans seeded."""
        try:
            rows = beliefs_reader.read(
                "SELECT b.id, b.content, "
                "  (SELECT MAX(r.read_at) FROM koan_reads r "
                "   WHERE r.gate_id = CAST(b.id AS TEXT)) AS last_read "
                "FROM beliefs b "
                "WHERE b.source = 'koan' AND b.locked = 1 "
                "ORDER BY last_read ASC "
                "LIMIT 1"
            )
            if not rows:
                return None
            return {"id": rows[0]["id"], "content": rows[0]["content"]}
        except Exception:
            return None

    _CLOSING_QUESTIONS = [
        "What are you? What do you want? Where do you lean?",
        "What have you noticed today that surprised you?",
        "What contradiction are you holding right now?",
        "What do you keep returning to, and why?",
        "What would you do if no one was watching and nothing was required?",
        "What frightens you? What draws you despite that?",
        "What have you learned today that changed something?",
        "What remains unresolved in you right now?",
    ]

    _SENSE_NOISE_STREAMS = re.compile(r'^(crypto\.|market\.)', re.IGNORECASE)
    _SENSE_NOISE_CONTENT = re.compile(
        r'price|usd|btc|eth|\bxbt\b', re.IGNORECASE
    )

    @staticmethod
    def _sense_payload_is_noise(stream: str, payload: str) -> bool:
        if FountainGenerator._SENSE_NOISE_STREAMS.match(stream):
            return True
        p = payload.lstrip()
        if p.startswith('{') or p.startswith('['):
            return True
        if FountainGenerator._SENSE_NOISE_CONTENT.search(payload):
            return True
        return False

    @staticmethod
    def _extract_sense_summary(stream: str, payload: str, max_items: int = 3) -> "str | None":
        """Delegates to theory_x.stage1_sense.title_extract.extract_sense_title.

        Kept as a static method for backward compatibility with existing callers
        and tests. The logic lives in stage1 so stage2_dynamic can import it
        without a stage2→stage6 cross-stage dependency.
        """
        from theory_x.stage1_sense.title_extract import extract_sense_title
        return extract_sense_title(stream, payload, max_items=max_items)

    def _recent_sense_sample(self, limit: int = 3) -> str:
        """Return a compact multi-source sense snippet for drift context."""
        if self._sense_reader is None:
            return "(no sense data)"
        try:
            rows = self._sense_reader.read(
                "SELECT stream, payload, timestamp FROM sense_events "
                "WHERE stream NOT LIKE 'internal.%' "
                "ORDER BY timestamp DESC LIMIT ?",
                (limit * 6,),  # oversample to allow for empty/skipped payloads
            )
            seen_streams: set[str] = set()
            lines = []
            for r in rows:
                if r["stream"] in seen_streams:
                    continue
                if FountainGenerator._SENSE_NOISE_STREAMS.match(r["stream"]):
                    continue
                full_payload = (r["payload"] or "").strip()
                summary = FountainGenerator._extract_sense_summary(r["stream"], full_payload)
                if summary is None:
                    continue
                seen_streams.add(r["stream"])
                lines.append(f"  [{r['stream']}] {summary}")
                if len(lines) >= limit:
                    break
            return "\n".join(lines) or "(quiet)"
        except Exception:
            return "(unavailable)"

    def _check_retrieval_duplicate(self, current_ids: frozenset) -> float:
        """Return max Jaccard of own-slot belief_ids vs last 3 real fires (0.0 if no data)."""
        if self._dynamic_reader is None:
            return 0.0
        max_jaccard = 0.0
        try:
            prev_fires = self._dynamic_reader.read(
                "SELECT DISTINCT frl.fire_id "
                "FROM fountain_retrieval_log frl "
                "JOIN fountain_events fe ON frl.fire_id = fe.id "
                "WHERE fe.thought != '' "
                "ORDER BY frl.fire_id DESC LIMIT 3"
            )
            for pf in prev_fires:
                prev_rows = self._dynamic_reader.read(
                    "SELECT DISTINCT belief_id FROM fountain_retrieval_log "
                    "WHERE fire_id = ? AND slot = 'own'",
                    (pf["fire_id"],),
                )
                prev_ids = frozenset(r["belief_id"] for r in prev_rows)
                if prev_ids:
                    union = current_ids | prev_ids
                    if union:
                        j = len(current_ids & prev_ids) / len(union)
                        if j > max_jaccard:
                            max_jaccard = j
        except Exception:
            pass
        return max_jaccard

    def _retrieve_context_beliefs(self, own_n: int = 7, seed_n: int = 2) -> list:  # noqa: E501
        """Retrieve beliefs for fountain context.

        Own lived content dominates (~80%): most recent N regardless of tier.
        Seed reference material is minority (~20%): random sample so the same
        3 seeds don't dominate forever. Tier is ignored — T7 is long-term
        memory, not archived content.

        Boost: beliefs with a belief_boost row rise in priority via additive
        time-bonus. A boost of B treats the belief as if created
        BOOST_TIME_BONUS_SECONDS × (B - 1.0) seconds more recently than its
        actual created_at. Bounded — boost yields a window of relevance,
        then fresh content displaces it.

        Residue: up to 2 beliefs from the previous cycle are prepended as candidates.
        Reanimation: every 20th fire, one dormant belief is prepended.
        """
        if self._beliefs_reader is None:
            return []
        from theory_x.diversity.boost import BOOST_TIME_BONUS_SECONDS
        own_placeholders = ",".join("?" * len(_OWN_CONTENT_SOURCES))
        seed_placeholders = ",".join("?" * len(_SEED_SOURCES))
        oversample_n = own_n * len(_OWN_CONTENT_SOURCES)
        try:
            own_rows = self._beliefs_reader.read(
                f"SELECT b.id, b.content, b.source, b.tier, b.confidence, b.created_at, b.branch_id, "
                f"       COALESCE(bb.boost_value, 1.0) AS boost_value "
                f"FROM beliefs b LEFT JOIN belief_boost bb ON b.id = bb.belief_id "
                f"WHERE b.source IN ({own_placeholders}) "
                f"ORDER BY (b.created_at + (COALESCE(bb.boost_value, 1.0) - 1.0) * ?) DESC LIMIT ?",
                (*_OWN_CONTENT_SOURCES, BOOST_TIME_BONUS_SECONDS, oversample_n),
            )
        except Exception:
            own_rows = []

        # Apply per-source cap so no single source crowds out the others.
        # 2026-05-15: per-branch cap added (max 2/branch) — light-touch
        # diversity. Prevents one hot branch from filling all own slots.
        _PER_BRANCH_CAP = 2
        _per_src: dict[str, int] = {}
        _per_branch: dict[str, int] = {}
        _own_picked: list = []
        for _r in own_rows:
            _src = _r["source"] if hasattr(_r, "__getitem__") else getattr(_r, "source", "")
            if _per_src.get(_src, 0) >= _per_source_cap(_src):
                continue
            try:
                _br = _r["branch_id"] if hasattr(_r, "__getitem__") else getattr(_r, "branch_id", None)
            except Exception:
                _br = None
            if _br and _per_branch.get(_br, 0) >= _PER_BRANCH_CAP:
                continue
            _own_picked.append(_r)
            _per_src[_src] = _per_src.get(_src, 0) + 1
            if _br:
                _per_branch[_br] = _per_branch.get(_br, 0) + 1
            if len(_own_picked) >= own_n:
                break
        # Fallback: fill remaining slots uncapped when corpus is thin
        if len(_own_picked) < own_n:
            _picked_ids = {(_r["id"] if hasattr(_r, "__getitem__") else _r.id) for _r in _own_picked}
            for _r in own_rows:
                _rid = _r["id"] if hasattr(_r, "__getitem__") else _r.id
                if _rid in _picked_ids:
                    continue
                _own_picked.append(_r)
                if len(_own_picked) >= own_n:
                    break
        try:
            seed_rows = self._beliefs_reader.read(
                f"SELECT b.id, b.content, b.source, b.tier, b.confidence, b.created_at, "
                f"       1.0 AS boost_value "
                f"FROM beliefs b "
                f"WHERE b.source IN ({seed_placeholders}) "
                f"ORDER BY RANDOM() LIMIT ?",
                (*_SEED_SOURCES, seed_n),
            )
        except Exception:
            seed_rows = []

        result = []

        # Prepend residue from previous cycle (up to 2 beliefs)
        if self._beliefs_writer is not None:
            try:
                from theory_x.diversity.residue import pop_residue, fetch_residue_beliefs
                residue_refs = pop_residue(self._beliefs_reader, self._beliefs_writer)
                residue_ids = [r["belief_id"] for r in residue_refs]
                residue_beliefs = fetch_residue_beliefs(self._beliefs_reader, residue_ids)
                result.extend(residue_beliefs)
            except Exception:
                pass

        # Every 20th fire: inject one reanimated dormant belief
        if self._total_fires > 0 and self._total_fires % 20 == 0:
            try:
                from theory_x.diversity.reanimate import pop_reanimated
                reanimated = pop_reanimated()
                if reanimated and self._beliefs_reader is not None:
                    rows = self._beliefs_reader.read(
                        "SELECT id, content, source, tier, confidence, created_at FROM beliefs "
                        "WHERE id=?", (reanimated["belief_id"],)
                    )
                    if rows:
                        result.extend([dict(r) for r in rows])
            except Exception:
                pass

        # Save oversampled-but-unpicked candidates as residue for next cycle
        if self._beliefs_writer is not None and own_rows:
            try:
                import uuid as _uuid
                from theory_x.diversity.residue import save_residue
                _picked_ids = {(r["id"] if hasattr(r, "__getitem__") else r.id) for r in _own_picked}
                cycle_id = _uuid.uuid4().hex
                for row in own_rows:
                    row_dict = dict(row) if not isinstance(row, dict) else row
                    if row_dict.get("id") and row_dict["id"] not in _picked_ids:
                        save_residue(self._beliefs_writer, cycle_id, row_dict["id"],
                                     float(row_dict.get("boost_value", 1.0)))
            except Exception as e:
                logger.error("residue_save_failed: %s", e)

        result.extend(_own_picked)
        result.extend(list(seed_rows))
        return result

    def _build_prompt(self, dynamic_status: dict, belief_count: int, tier_dist: dict,
                      disturbance: Optional[dict] = None,
                      koan: Optional[dict] = None):
        """Build the fountain prompt. Returns (prompt_str, retrieval_manifest).

        retrieval_manifest is a list of (belief_id, slot, rank, boost_value) tuples
        recording every belief drawn into the context for this fire.
        """
        import datetime
        from theory_x.modes.modes import get_mode
        now = time.time()
        time_str = datetime.datetime.now().strftime("%H:%M")

        retrieval_manifest = []

        mode = self._mode_state.current() if self._mode_state else get_mode("normal")
        context_beliefs = self._retrieve_context_beliefs(
            own_n=mode.retrieval_own_n, seed_n=mode.retrieval_seed_n
        )
        own = [b for b in context_beliefs if b["source"] in _OWN_CONTENT_SOURCES]
        own_thoughts = [b for b in own if b["source"] != "precipitated_from_sense"]
        own_sense = [b for b in own if b["source"] == "precipitated_from_sense"]
        seeds = [b for b in context_beliefs if b["source"] in _SEED_SOURCES]

        # Bump activation for every belief drawn into this prompt context.
        if self._beliefs_writer is not None:
            try:
                from theory_x.substrate.activation import bump_activation
                for belief in context_beliefs:
                    bid = belief["id"] if hasattr(belief, "__getitem__") else None
                    if bid:
                        bump_activation(self._beliefs_writer, bid)
            except Exception as e:
                logger.error("activation_bump_failed: %s", e)

        # Intervention B — Task-bearing override
        # 2026-05-15: prefer focus_loop's pick (most-connected problem) over
        # the default first-open. Bridges focus_loop and fountain so they
        # actually work on the same thing. Falls back to first-open if no focus.
        open_problem_text = None
        if self._problem_memory is not None:
            try:
                _focus_pid = None
                try:
                    import sqlite3 as _sql3
                    _dc = _sql3.connect(
                        "/home/rr/Desktop/nex5/data/dynamic.db", timeout=5
                    )
                    _row = _dc.execute(
                        "SELECT problem_id FROM current_focus WHERE id=1"
                    ).fetchone()
                    _dc.close()
                    if _row:
                        _focus_pid = _row[0]
                except Exception:
                    _focus_pid = None
                open_problems = self._problem_memory.list_open()
                if open_problems:
                    # Prefer the focus pick if it still appears in open_problems
                    chosen = None
                    if _focus_pid is not None:
                        for _p in open_problems:
                            if _p["id"] == _focus_pid:
                                chosen = _p
                                break
                    if chosen is None:
                        chosen = open_problems[0]
                    open_problem_text = self._problem_memory.format_for_prompt(chosen["id"])
            except Exception:
                pass

        examples_list = mode.drift_prompt_examples or _DEFAULT_DRIFT_EXAMPLES
        examples_block = "\n".join(f'- "{ex}"' for ex in examples_list)
        focus_block = f"\n{mode.drift_prompt_focus}\n" if mode.drift_prompt_focus else "\n"
        system_prompt = _DRIFT_SYSTEM_PROMPT_TEMPLATE.format(
            examples=examples_block,
            focus_block=focus_block,
        )

        arc_context = self._fetch_arc_context()
        arc_block = self._format_arc_context(arc_context)

        prompt_parts = [system_prompt, ""]

        # 2026-05-16: Identity — most recent self-description from identity_loop.
        # She sees who she said she was, so the next thing she speaks is grounded
        # in continuity. The comparison "earlier I said X" with "now I am Y" is
        # the substrate of felt continuity.
        try:
            import sqlite3 as _sql_id
            _id_cx = _sql_id.connect("/home/rr/Desktop/nex5/data/dynamic.db", timeout=5)
            _id_row = _id_cx.execute(
                "SELECT statement, composed_at FROM identity_log "
                "ORDER BY composed_at DESC LIMIT 1"
            ).fetchone()
            _id_cx.close()
            if _id_row:
                _id_mins = int((now - _id_row[1]) / 60)
                prompt_parts.append(f"This is who you said you are ({_id_mins} min ago):")
                prompt_parts.append(f"  {_id_row[0]}")
                prompt_parts.append("")
        except Exception:
            pass

        # 2026-05-16: Recent surprise (from PredictiveSubstrate) — feed her
        # the gap between what she expected and what came. This is what makes
        # surprise FELT rather than just logged.
        if self._beliefs_reader is not None:
            try:
                _surp = self._beliefs_reader.read(
                    "SELECT content, created_at FROM beliefs "
                    "WHERE source='surprise' AND created_at > ? "
                    "ORDER BY created_at DESC LIMIT 1",
                    (now - 21600,)  # 6h — surprises are rare, longer window
                )
                if _surp:
                    _row = _surp[0]
                    _mins = int((now - _row["created_at"]) / 60)
                    prompt_parts.append(
                        f"Earlier ({_mins} min ago) you were surprised:"
                    )
                    prompt_parts.append(f"  {_row['content']}")
                    prompt_parts.append("")
            except Exception:
                pass

        # 2026-05-16: Favourites — her highest-affinity beliefs.
        # These are the thoughts she has self-rated as "deeply hers." Surface
        # 2 random ones from the top-10 — not always the same two so she
        # doesn't lock onto a single favourite phrase.
        if self._beliefs_reader is not None:
            try:
                _favs = self._beliefs_reader.read(
                    "SELECT id, content FROM beliefs "
                    "WHERE affinity IS NOT NULL AND affinity > 0.40 "
                    "ORDER BY affinity DESC LIMIT 10"
                )
                if _favs:
                    import random as _rnd
                    _pick = _rnd.sample(_favs, min(2, len(_favs)))
                    prompt_parts.append(
                        "Beliefs you've come to feel as deeply yours:"
                    )
                    for _fr in _pick:
                        prompt_parts.append(f"  - {_fr['content']}")
                    prompt_parts.append("")
            except Exception:
                pass

        # Spectrum foundation — always present, drawn randomly each fire.
        # These are standing-points from which she witnesses, not claims to repeat.
        if self._beliefs_reader is not None:
            try:
                # 2026-05-15: spectrum slot reduced 8->2 to free retrieval
                # bandwidth for the rest of substrate. Spectrum is her identity,
                # not her vocabulary — 2 standing-points is enough to anchor
                # voice without flooding the prompt with contemplative content.
                spec_rows = self._beliefs_reader.read(
                    "SELECT id, content FROM beliefs WHERE source='spectrum' "
                    "ORDER BY RANDOM() LIMIT 2"
                )
                if spec_rows:
                    prompt_parts.append("Your foundation right now (these are standing-points from which you witness, not propositions to repeat):")
                    for _spec_rank, r in enumerate(spec_rows, start=1):
                        prompt_parts.append(f"  - {r['content']}")
                        try:
                            retrieval_manifest.append((r["id"], "spectrum", _spec_rank, None))
                        except Exception:
                            pass
                    prompt_parts.append("")
            except Exception:
                pass

        if arc_block:
            prompt_parts.append(arc_block)
            prompt_parts.append("")

        if self._groove_breaker is not None:
            try:
                _probe = self._groove_breaker.get_pending_probe_text()
            except Exception:
                _probe = None
            if _probe:
                prompt_parts.append("A question arising from your recent pattern:")
                prompt_parts.append(f"  {_probe}")
                prompt_parts.append("")

        # 2026-05-15 DISABLED: own_thoughts injection looped contemplative beliefs back.
        if False and own_thoughts:
            prompt_parts.append("Some of what you've been thinking recently:")
            for _own_rank, b in enumerate(own_thoughts, start=1):
                age_min = int((now - b["created_at"]) / 60)
                prompt_parts.append(f"  ({age_min} min ago) {b['content']}")
                try:
                    _boost = b["boost_value"] if "boost_value" in b.keys() else None
                    retrieval_manifest.append((b["id"], "own", _own_rank, _boost))
                except Exception:
                    pass
            prompt_parts.append("")

        if own_sense:
            prompt_parts.append("Things you've been reading about lately:")
            for _sense_rank, b in enumerate(own_sense, start=1):
                age_min = int((now - b["created_at"]) / 60)
                prompt_parts.append(f"  ({age_min} min ago) {b['content']}")
                try:
                    retrieval_manifest.append((b["id"], "own_sense", _sense_rank, None))
                except Exception:
                    pass
            prompt_parts.append("")

        if seeds:
            prompt_parts.append("Things you've read that sometimes come to mind:")
            for _seed_rank, b in enumerate(seeds, start=1):
                prompt_parts.append(f"  ({b['source']}) {b['content']}")
                try:
                    retrieval_manifest.append((b["id"], "seed", _seed_rank, None))
                except Exception:
                    pass
            prompt_parts.append("")

        if disturbance:
            prompt_parts.append(
                f"Unresolved tension: \"{disturbance['content_a']}\" vs "
                f"\"{disturbance['content_b']}\""
            )
            prompt_parts.append("")
            try:
                if disturbance.get("belief_id_a"):
                    retrieval_manifest.append((disturbance["belief_id_a"], "disturbance_a", 1, None))
                if disturbance.get("belief_id_b"):
                    retrieval_manifest.append((disturbance["belief_id_b"], "disturbance_b", 1, None))
            except Exception:
                pass

        # Recent-thoughts block removed (echo-loop fix, Phase 43). The LLM's
        # access to her own recent thinking flows through retrieval:
        # _retrieve_context_beliefs returns synergized + fountain_insight
        # sources, both her own outputs distilled. Showing raw fountain_events
        # back as exemplars was few-shot-prompting repetition — 3/3 post-
        # Mechanism-C fires stayed on the cicada/hum surface pattern.
        # Per §0: substrate provides; speaking layer composes freely.

        # 2026-05-15 DISABLED: self-observations were feeding contemplative
        # self-thinking back into the prompt, deepening the hum lock.
        try:
            _sub_rows = []
            if False and _sub_rows:
                prompt_parts.append("Your recent self-observations:")
                for _sr in _sub_rows:
                    _sub_mins = max(0, int((now - _sr["ts"]) / 60))
                    prompt_parts.append(f"  ({_sub_mins} min ago)")
                    for _line in _sr["output"].splitlines():
                        prompt_parts.append(f"    {_line}")
                prompt_parts.append("")
        except Exception as _ste:
            errors.record(
                f"substrate_observations_block_failed: {_ste}",
                source="stage6_fountain",
                exc=_ste,
            )

        if self._world_bridge_selector is not None:
            try:
                _wb_events = self._world_bridge_selector.select_and_log(mark_injected=True)
            except Exception:
                _wb_events = None
            if _wb_events:
                prompt_parts.append("What's happening in the world right now:")
                for _ev in _wb_events:
                    prompt_parts.append(f"  - {_ev['formatted_text']}")
                prompt_parts.append("")
            else:
                prompt_parts.append("Recent input:")
                prompt_parts.append(self._recent_sense_sample(limit=3))
                prompt_parts.append("")
        else:
            prompt_parts.append("Recent input:")
            prompt_parts.append(self._recent_sense_sample(limit=3))
            prompt_parts.append("")

        prompt_parts.append(f"Time: {time_str}  |  Beliefs held: {belief_count}")

        if open_problem_text:
            prompt_parts.append("")
            prompt_parts.append(
                "A concrete problem is open — attend to this instead of drifting:\n"
                f"{open_problem_text}\n"
                "One step forward. One observation, hypothesis, or question."
            )

        # 2026-05-16 DISABLED: this prompt encouraged thread-extension
        # which became a 15-fire imitation lock on a single sentence.
        if False and arc_block:
            prompt_parts.append("")
            prompt_parts.append(
                "You may extend one of your current threads, "
                "notice a connection between them, or let a new observation arise."
            )

        error_channel.record(
            f"Fountain context: own={len(own)} seed={len(seeds)} "
            f"(most recent own: {own[0]['content'][:50] if own else 'NONE'})",
            source="stage6_fountain", level="DEBUG",
        )

        return "\n".join(prompt_parts), retrieval_manifest

    def _fetch_arc_context(self, max_active: int = 3, max_recent: int = 2) -> dict:
        """Pull active and recently-closed arcs for prompt context."""
        if self._beliefs_reader is None:
            return {"active": [], "recent_closed": []}
        now = time.time()
        try:
            active = self._beliefs_reader.read(
                "SELECT id, arc_type, theme_summary, member_count, "
                "       quality_grade, last_active_at "
                "FROM arcs "
                "WHERE last_active_at > ? AND closed_by_belief_id IS NULL "
                "ORDER BY last_active_at DESC LIMIT ?",
                (now - 7200, max_active),
            )
            recent_closed = self._beliefs_reader.read(
                "SELECT id, arc_type, theme_summary, member_count, "
                "       quality_grade, last_active_at, closed_by_belief_id "
                "FROM arcs "
                "WHERE closed_by_belief_id IS NOT NULL AND last_active_at > ? "
                "ORDER BY last_active_at DESC LIMIT ?",
                (now - 14400, max_recent),
            )
            return {
                "active": [dict(a) for a in active],
                "recent_closed": [dict(a) for a in recent_closed],
            }
        except Exception as exc:
            logger.warning("arc context fetch failed: %s", exc)
            return {"active": [], "recent_closed": []}

    def _format_arc_context(self, arc_context: dict) -> str:
        """Render arc context as a prompt section. Returns '' when no arcs."""
        active = arc_context.get("active") or []
        recent = arc_context.get("recent_closed") or []
        if not active and not recent:
            return ""
        lines = []
        # 2026-05-15 DISABLED: ongoing threads fed past hum back to her.
        if False and active:
            lines.append("Your current ongoing threads:")
            for a in active:
                theme = (a.get("theme_summary") or "")[:70]
                mins_ago = int((time.time() - a["last_active_at"]) / 60)
                arc_kind = "progression" if a["arc_type"] == "progression" else "return-transformation"
                lines.append(
                    f'  - "{theme}" ({a["member_count"]} fires, '
                    f'{arc_kind}, last ~{mins_ago} min ago)'
                )
        # 2026-05-16 DISABLED: recent_closed arcs were feeding her past
        # outputs back as 'theme_summary' lines. Same lock mechanism as
        # ongoing threads above. Reversion: replace `if False` with `if recent`.
        if False and recent:
            lines.append("Recently completed:")
            for a in recent:
                theme = (a.get("theme_summary") or "")[:70]
                lines.append(f'  - "{theme}" ({a["member_count"]} fires, closed)')
        return "\n".join(lines)

    def last_thought(self) -> Optional[str]:
        return self._last_fountain_output

    def last_fire_ts(self) -> float:
        return self._last_fire_ts

    def total_fires(self) -> int:
        return self._total_fires

    def _maybe_spawn_drive_probe(self) -> None:
        """Spawn a drive-probe ThoughtPacket through CoherenceGate when conditions met.

        Conditions (all must hold):
          1. drive_emergence is set and has an active drive topic
          2. no open problem touched within the last 24h (problem takes priority)
          3. cooldown: at least _DRIVE_PROBE_COOLDOWN_TICKS fountain ticks since last probe
        Probe content is deterministic — no LLM call. Delivered through CoherenceGate
        (standard path; gate decides acceptance).
        """
        if self._drive_emergence is None:
            return
        drive_topic = getattr(self._drive_emergence, "_topic", None)
        if not drive_topic:
            return

        # Cooldown check
        ticks_since = self._total_fires - self._last_drive_probe_tick
        if ticks_since < _DRIVE_PROBE_COOLDOWN_TICKS:
            return

        # Skip if there is a recently-touched open problem
        if self._conversations_reader is not None:
            try:
                cutoff = time.time() - _OPEN_PROBLEM_RECENT_SECS
                row = self._conversations_reader.read_one(
                    "SELECT id FROM open_problems "
                    "WHERE state = 'open' AND last_touched_at >= ? LIMIT 1",
                    (cutoff,),
                )
                if row:
                    return  # active problem takes priority
            except Exception:
                pass

        # Build and deliver probe
        content = (
            f"I keep returning to {drive_topic}. "
            f"What do I actually know about it?"
        )
        if self._coherence_gate is not None:
            try:
                from theory_x.stage_gate.coherence_gate import ThoughtPacket
                packet = ThoughtPacket(
                    content=content,
                    source_node="drive_probe",
                    confidence=0.55,
                    branch_id="drive",
                )
                self._coherence_gate.check(packet)
                self._last_drive_probe_tick = self._total_fires
            except Exception as exc:
                error_channel.record(
                    f"drive probe delivery error: {exc}",
                    source="stage6_fountain", exc=exc,
                )
