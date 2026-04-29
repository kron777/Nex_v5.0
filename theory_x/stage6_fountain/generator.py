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
    "behavioural_observation",
    "auto_probe",
)

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

Produce ONE drift thought. Nothing else. No preamble, no framing.\
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
from theory_x.stage6_fountain.crystallizer import FountainCrystallizer

THEORY_X_STAGE = 6


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
        self._evaluator = ReadinessEvaluator()
        self._last_fountain_output: Optional[str] = None
        self._last_fire_ts: float = 0.0
        self._total_fires: int = 0
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
            self._last_fountain_output = thought
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
            self._last_fountain_output = thought
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
            "INSERT INTO fountain_events (ts, thought, droplet, readiness, hot_branch, word_count) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (ts_now, thought, droplet, readiness, hot_branch, word_count),
        )

        self._last_fountain_output = thought
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

    def _recent_sense_sample(self, limit: int = 3) -> str:
        """Return a compact multi-source sense snippet for drift context."""
        if self._sense_reader is None:
            return "(no sense data)"
        try:
            rows = self._sense_reader.read(
                "SELECT stream, payload, timestamp FROM sense_events "
                "WHERE stream NOT LIKE 'internal.%' "
                "ORDER BY timestamp DESC LIMIT ?",
                (limit * 6,),  # oversample more to allow for filtered-out rows
            )
            seen_streams: set[str] = set()
            lines = []
            for r in rows:
                if r["stream"] in seen_streams:
                    continue
                payload = (r["payload"] or "")[:80].strip()
                if self._sense_payload_is_noise(r["stream"], payload):
                    continue
                seen_streams.add(r["stream"])
                lines.append(f"  [{r['stream']}] {payload}")
                if len(lines) >= limit:
                    break
            return "\n".join(lines) or "(quiet)"
        except Exception:
            return "(unavailable)"

    def _retrieve_context_beliefs(self, own_n: int = 7, seed_n: int = 2) -> list:  # noqa: E501
        """Retrieve beliefs for fountain context.

        Own lived content dominates (~80%): most recent N regardless of tier.
        Seed reference material is minority (~20%): random sample so the same
        3 seeds don't dominate forever. Tier is ignored — T7 is long-term
        memory, not archived content.

        Boost: beliefs with a belief_boost row rise in priority via weighted sort.
        Residue: up to 2 beliefs from the previous cycle are prepended as candidates.
        Reanimation: every 20th fire, one dormant belief is prepended.
        """
        if self._beliefs_reader is None:
            return []
        own_placeholders = ",".join("?" * len(_OWN_CONTENT_SOURCES))
        seed_placeholders = ",".join("?" * len(_SEED_SOURCES))
        try:
            own_rows = self._beliefs_reader.read(
                f"SELECT b.id, b.content, b.source, b.tier, b.confidence, b.created_at, "
                f"       COALESCE(bb.boost_value, 1.0) AS boost_value "
                f"FROM beliefs b LEFT JOIN belief_boost bb ON b.id = bb.belief_id "
                f"WHERE b.source IN ({own_placeholders}) "
                f"ORDER BY (b.created_at * COALESCE(bb.boost_value, 1.0)) DESC LIMIT ?",
                (*_OWN_CONTENT_SOURCES, own_n),
            )
        except Exception:
            own_rows = []
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

        # Save current cycle's considered-but-unused candidates as residue
        if self._beliefs_writer is not None and own_rows:
            try:
                import uuid as _uuid
                from theory_x.diversity.residue import save_residue
                own_rows_dicts = [dict(r) for r in own_rows]
                cycle_id = _uuid.uuid4().hex
                for i, row in enumerate(own_rows_dicts):
                    if row.get("id") and i >= own_n // 2:
                        save_residue(self._beliefs_writer, cycle_id, row["id"],
                                     float(row.get("boost_value", 1.0)))
            except Exception as e:
                logger.error("residue_save_failed: %s", e)

        result.extend(list(own_rows))
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
        open_problem_text = None
        if self._problem_memory is not None:
            try:
                open_problems = self._problem_memory.list_open()
                if open_problems:
                    p = open_problems[0]
                    open_problem_text = self._problem_memory.format_for_prompt(p["id"])
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

        # Spectrum foundation — always present, drawn randomly each fire.
        # These are standing-points from which she witnesses, not claims to repeat.
        if self._beliefs_reader is not None:
            try:
                spec_rows = self._beliefs_reader.read(
                    "SELECT id, content FROM beliefs WHERE source='spectrum' "
                    "ORDER BY RANDOM() LIMIT 8"
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

        if own:
            prompt_parts.append("Some of what you've been thinking recently:")
            for _own_rank, b in enumerate(own, start=1):
                age_min = int((now - b["created_at"]) / 60)
                prompt_parts.append(f"  ({age_min} min ago) {b['content']}")
                try:
                    _boost = b["boost_value"] if "boost_value" in b.keys() else None
                    retrieval_manifest.append((b["id"], "own", _own_rank, _boost))
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

        # Recent fountain outputs — continuity with her last N generative fires
        _RECENT_THOUGHTS_N = 5
        try:
            _recent_rows = list(self._dynamic_reader.read(
                "SELECT thought, ts FROM fountain_events "
                "WHERE thought IS NOT NULL AND thought != '' "
                "ORDER BY id DESC LIMIT ?",
                (_RECENT_THOUGHTS_N,)
            ))
            if _recent_rows:
                prompt_parts.append("Your recent thoughts (most recent first):")
                for _r in _recent_rows:
                    _mins_ago = max(0, int((now - _r["ts"]) / 60))
                    prompt_parts.append(f"  ({_mins_ago} min ago) {_r['thought']}")
                prompt_parts.append("")
        except Exception as _rte:
            errors.record(
                f"recent_thoughts_block_failed: {_rte}",
                source="stage6_fountain",
                exc=_rte,
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

        if arc_block:
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
        if active:
            lines.append("Your current ongoing threads:")
            for a in active:
                theme = (a.get("theme_summary") or "")[:70]
                mins_ago = int((time.time() - a["last_active_at"]) / 60)
                arc_kind = "progression" if a["arc_type"] == "progression" else "return-transformation"
                lines.append(
                    f'  - "{theme}" ({a["member_count"]} fires, '
                    f'{arc_kind}, last ~{mins_ago} min ago)'
                )
        if recent:
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
