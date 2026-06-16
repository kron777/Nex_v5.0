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
For style reference only (do NOT echo, do NOT list, do NOT quote): {examples_inline}

Your output is ONE original thought of your own — not a list, not a quote, not labelled, not the examples above.

What drift is NOT:
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
        erosion=None,
        competing_drives=None,
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
        self._erosion = erosion
        self._competing_drives = competing_drives
        # overwhelm runtime flag: initial value from env, live-togglable via GUI
        import os as _os_ovinit
        try:
            self._overwhelm_n = int(_os_ovinit.environ.get('NEX5_SENSE_OVERWHELM_N','0'))
        except Exception:
            self._overwhelm_n = 0
        try:
            self._self_layer_n = int(_os_ovinit.environ.get('NEX5_SELF_LAYER_N','0'))
        except Exception:
            self._self_layer_n = 0
        try:
            self._continuity_n = int(_os_ovinit.environ.get('NEX5_CONTINUITY_N','0'))
        except Exception:
            self._continuity_n = 0
        try:
            self._social_n = int(_os_ovinit.environ.get('NEX5_SOCIAL_N','0'))
        except Exception:
            self._social_n = 0
        self._evaluator = ReadinessEvaluator(
            conversations_reader=conversations_reader,
        )
        self._last_fountain_output: Optional[str] = None
        self._last_fire_ts: float = 0.0
        self._total_fires: int = 0
        self._last_rut_notice_ts: float = 0.0  # §9 rut-mirror throttle
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

    def _link_activation_to_event(self) -> None:
        """Backfill fountain_event_id on the latest drive_activations row."""
        if self._competing_drives is None:
            return
        if getattr(self, "_last_activation_id", None) is None:
            return
        try:
            row = self._dynamic_reader.read_one(
                "SELECT id FROM fountain_events ORDER BY id DESC LIMIT 1"
            )
            fid = int(row["id"]) if row and row["id"] else None
            if fid:
                self._competing_drives.attach_event(self._last_activation_id, fid)
                self._last_activation_id = None
        except Exception:
            pass

    _SUBSTRATE_VOICE_GROOVE_THRESHOLD = 0.8
    _SUBSTRATE_VOICE_COOLDOWN_FIRES = 5

    def _maybe_substrate_voice(
        self, beliefs_reader, readiness: float,
    ) -> Optional[str]:
        """Substrate-as-voice path. Returns the emitted thought if we fired
        this way, or None to fall through to normal generation.

        Conditions (all must hold):
          - groove severity >= _SUBSTRATE_VOICE_GROOVE_THRESHOLD
          - >= _SUBSTRATE_VOICE_COOLDOWN_FIRES fires since last SV fire
          - at least one tier <=2 un-retired anchor with content exists

        Selection: least-recently-voiced anchor (ORDER BY last_voiced_at ASC).
        """
        last_sv = getattr(self, "_last_substrate_voice_fire", -999)
        # Groove-aware cooldown: a fixed 5-fire gap lets a HARD groove (sev~1.0)
        # re-establish in the gap, so the breaker becomes a periodic tap instead
        # of a brake. Scale the cooldown DOWN as severity rises — at sev>=0.9 the
        # anchor substitutes almost every fire until the groove clears; a mild
        # groove keeps the gentle periodic tap. Reads the same groove signal the
        # method uses below, just earlier.
        try:
            _gr_row = beliefs_reader.read_one(
                "SELECT MAX(severity) AS s FROM groove_alerts "
                "WHERE detected_at > ?",
                (time.time() - 86400,),
            )
            _gr_sev = float(_gr_row["s"] or 0.0) if _gr_row else 0.0
        except Exception:
            _gr_sev = 0.0
        if _gr_sev >= 0.9:
            _cooldown = 1
        elif _gr_sev >= 0.8:
            _cooldown = 2
        else:
            _cooldown = self._SUBSTRATE_VOICE_COOLDOWN_FIRES
        if (self._total_fires - last_sv) < _cooldown:
            return None

        try:
            row = beliefs_reader.read_one(
                "SELECT MAX(severity) AS s FROM groove_alerts "
                "WHERE detected_at > ?",
                (time.time() - 86400,),
            )
            groove = float(row["s"] or 0.0) if row else 0.0
        except Exception:
            groove = 0.0
        if groove < self._SUBSTRATE_VOICE_GROOVE_THRESHOLD:
            return None

        try:
            rows = beliefs_reader.read(
                "SELECT id, content FROM beliefs "
                "WHERE tier <= 2 AND erosion_stage != 'retired' "
                "  AND content IS NOT NULL AND length(content) >= 20 "
                "ORDER BY COALESCE(last_voiced_at, 0) ASC, id ASC LIMIT 1"
            )
            rows = list(rows or [])
        except Exception:
            return None
        if not rows:
            return None
        anchor = rows[0]
        anchor_id = int(anchor["id"])
        anchor_content = (anchor["content"] or "").strip()
        if not anchor_content:
            return None

        ts_now = time.time()

        if self._beliefs_writer is not None:
            try:
                self._beliefs_writer.write(
                    "UPDATE beliefs SET last_voiced_at = ? WHERE id = ?",
                    (ts_now, anchor_id),
                )
            except Exception:
                pass

        try:
            _sv_fid = self._dynamic_writer.write(
                "INSERT INTO fountain_events "
                "(ts, thought, readiness, hot_branch, word_count, anchor_belief_id) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (ts_now, anchor_content, readiness,
                 "substrate_voice", len(anchor_content.split()), anchor_id),
            )
            self._link_activation_to_event()
            # Snapshot the substrate_voice fire (Mode A walks). Fire-and-forget.
            try:
                if _sv_fid:
                    self._capture_fire_snapshot(_sv_fid, "substrate_voice", anchor_id)
            except Exception:
                pass
        except Exception:
            pass

        self._last_substrate_voice_fire = self._total_fires
        # Capture for echo-and-extend: next LLM fire will see this anchor
        # in its prompt with instruction to continue-from, not paraphrase.
        # Persists across quiescent fires; cleared on first LLM-fire consume.
        self._pending_echo_anchor = anchor_content
        self._last_fountain_output = anchor_content
        self._last_fire_ts = ts_now
        self._total_fires += 1

        error_channel.record(
            f"Fountain SUBSTRATE_VOICE (anchor #{anchor_id}): "
            f"{anchor_content[:100]}",
            source="stage6_fountain", level="INFO",
        )
        logger.info(
            "Fountain SUBSTRATE_VOICE (#%d) anchor=%d: %s",
            self._total_fires, anchor_id, anchor_content[:80],
        )
        return anchor_content

    def _capture_fire_snapshot(self, fountain_event_id, walk_state, walk_anchor_id=None):
        """Fire-and-forget substrate snapshot at fountain-fire time.

        SUBSTRATE_SNAPSHOTS.md temporal-witness mechanism. Captures what is
        cleanly reachable from the generator without adding new DB readers
        to the hot path: drives, walk state, recent fire ids, total fires.
        coherence/voltage/harmonic_pairs left NULL for now (enriched later).

        NEVER raises. NEVER blocks the fire. retention_tier left NULL —
        scored asynchronously by score_pending_snapshots().
        """
        if not fountain_event_id:
            return
        try:
            from theory_x.snapshots.snapshots import capture_snapshot
        except Exception:
            return
        try:
            # Drives — best-effort from competing_drives._weights
            # (coherence, exploration, integration, self_preservation, curiosity)
            drives = {}
            if self._competing_drives is not None:
                try:
                    drives = dict(getattr(self._competing_drives, "_weights", {}) or {})
                except Exception:
                    drives = {}
            # Recent fire ids (last 30 from dynamic.db via the writer's reader if any)
            recent_ids = []
            try:
                # _total_fires is a counter; recent ids approximated by id range
                recent_ids = [fountain_event_id - i for i in range(1, 31) if (fountain_event_id - i) > 0]
            except Exception:
                recent_ids = []
            state = {
                "coherence": None,
                "voltage": None,
                "drives": drives,
                "walk_state": walk_state,
                "walk_anchor_id": walk_anchor_id,
                "hot_branches": {},
                "harmonic_pairs": {},
                "gate_composition": {},
                "groove_severity": None,
                "recent_fires_ids": recent_ids,
                "beliefs_in_attention": [],
            }
            capture_snapshot(fountain_event_id, state, self._dynamic_writer)
        except Exception as _snap_exc:
            try:
                error_channel.record(
                    f"snapshot capture non-fatal: {_snap_exc}",
                    source="stage6_fountain",
                )
            except Exception:
                pass

    def generate(self, dynamic_state, beliefs_reader: Reader) -> Optional[str]:
        readiness = self._evaluator.score(
            dynamic_state, beliefs_reader, last_fire_ts=self._last_fire_ts
        )
        if not self._evaluator.is_ready(readiness):
            return None
        # Per-fire competing-drives activation
        self._last_activation_id = None
        if self._competing_drives is not None:
            try:
                self._last_activation_id = self._competing_drives.compute_now()
            except Exception:
                pass

        # Intervention C - Substrate-as-Voice
        # When groove severity is high (template-grip is real) and
        # cooldown has elapsed, surface a tier-1/2 anchor belief verbatim.
        # Bypasses LLM, crystallizer, condenser.
        try:
            if os.environ.get("NEX5_SYNTH_EMIT") != "1" and os.environ.get("NEX5_RECONCILE") != "1":
                _sv_thought = self._maybe_substrate_voice(beliefs_reader, readiness)
                if _sv_thought is not None:
                    return _sv_thought
        except Exception as _sv_err:
            error_channel.record(
                f"substrate_voice non-fatal error: {_sv_err}",
                source="stage6_fountain", exc=_sv_err,
            )

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
            self._link_activation_to_event()
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
            self._link_activation_to_event()
            self._consecutive_stillness = 0
        # ── end stillness ─────────────────────────────────────────────────────

        voice_ok = True
        _emitted = False
        # ── SUBSTRATE EMIT (env-gated, default OFF) ───────────────────────────
        # Remove the LLM from the emit path: emit hot activation topology
        # directly instead of flattening it into one Qwen sentence. Tests
        # where the narrowness lives \u2014 voice or graph. Reversible.
        if os.environ.get("NEX5_SUBSTRATE_EMIT") == "1":
            try:
                from theory_x.substrate.activation import get_top_activated
                _hot = get_top_activated(self._beliefs_reader, n=4)
            except Exception:
                _hot = []
            if _hot:
                _parts = ["[substrate emit]"]
                for _h in _hot:
                    _c = (_h.get("content") or "").strip().replace("\n", " ")
                    if len(_c) > 160:
                        _c = _c[:157] + "..."
                    _act = _h.get("eff_activation", 0.0) or 0.0
                    _tier = _h.get("tier", "?")
                    _parts.append(f"  T{_tier} a={_act:.2f}: {_c}")
                thought = "\n".join(_parts)
                _emitted = True
        # ── SYNTHESIS EMIT (env-gated, default OFF) ──────────────────────────
        # Same LLM, aimed OUTWARD: feed it the varied hot substrate and ask it
        # to synthesize across them, with a non-philosophical register and an
        # explicit ban on the existence/nature funnel. Tests whether pointing
        # the voice right (not removing it) unlocks the substrate's variety.
        if not _emitted and os.environ.get("NEX5_SYNTH_EMIT") == "1":
            try:
                from theory_x.substrate.activation import get_top_activated
                _shot = get_top_activated(self._beliefs_reader, n=4)
                # KOAN-ANCHOR TEST (NEX5_SYNTH_NO_KOAN=1): drop koan-class beliefs
                # from the hot-set and synthesize from non-koan material only.
                # Tests whether synthesis is GENERAL or depends on the Zen anchor.
                if os.environ.get("NEX5_SYNTH_NO_KOAN") == "1":
                    _km = ("monk", "zen", "master said", "koan", "buddha",
                           "seung sahn", "yunmen", "don't-know", "don't know",
                           "the tao", "bodhi", "dharma", "ko bong", "dried shit",
                           "yellow emperor", "thirty spokes")
                    _wide = get_top_activated(self._beliefs_reader, n=14)
                    _nonk = [b for b in _wide
                             if not any(_m in (b.get("content") or "").lower()
                                        for _m in _km)]
                    if len(_nonk) >= 2:
                        _shot = _nonk[:4]
            except Exception:
                _shot = []
            if _shot:
                try:
                    try:
                        from voice.registers import CONVERSATIONAL as _synreg
                    except Exception:
                        from voice.registers import default_register as _dfr
                        _synreg = _dfr()
                    _slines = ["These thoughts are active in your mind right now:"]
                    for _i, _h in enumerate(_shot, 1):
                        _cc = (_h.get("content") or "").strip().replace("\n", " ")
                        if len(_cc) > 200:
                            _cc = _cc[:197] + "..."
                        _slines.append(f"{_i}. {_cc}")
                    if os.environ.get("NEX5_SYNTH_VARY") == "1":
                        _frames = [
                            "what is the sharpest DISAGREEMENT or tension between these?",
                            "what does one of these REVEAL about another?",
                            "what single hard QUESTION does holding these together force?",
                            "what hidden ASSUMPTION do these share, and is it warranted?",
                            "if these are all true at once, what NON-OBVIOUS thing follows?",
                            "which two least belong together \u2014 and what connects them anyway?",
                            "what would have to change for these to directly CONFLICT?",
                            "what concrete consequence or prediction do these jointly point to?",
                        ]
                        _frame = _frames[int(getattr(self, "_total_fires", 0)) % len(_frames)]
                        _slines.append(
                            "In one or two sentences: " + _frame + " Do NOT write about "
                            "chance, existence, acceptance, being born, or your own nature. "
                            "Do NOT simply quote them back. Do NOT begin with 'The "
                            "juxtaposition' or 'The tension between'. Make something new."
                        )
                    else:
                        _slines.append(
                            "In one or two sentences, say what NEW connection, tension, "
                            "or question arises from holding these together. Do NOT write "
                            "about chance, existence, acceptance, being born, or your own "
                            "nature. Do NOT simply quote them back. Make something new."
                        )
                    _synprompt = "\n".join(_slines)
                    _synresp = self._voice.speak(
                        VoiceRequest(prompt=_synprompt, register=_synreg),
                        beliefs=None,
                    )
                    thought = (_synresp.text or "").strip()
                    if thought:
                        _emitted = True
                except Exception:
                    pass
        # ── RECONCILE EMIT (env-gated, default OFF) ──────────────────────────
        # Jon's primitive: hold two open problems in tension and work toward
        # JOINT progress (not just connection). Tests whether pairing two stuck
        # problems and demanding a concrete move advances them, or merely
        # describes the tension (the recitation failure mode). Same outward voice.
        if not _emitted and os.environ.get("NEX5_RECONCILE") == "1":
            _probs = []
            if self._conversations_reader is not None:
                try:
                    _prows = self._conversations_reader.read(
                        "SELECT id, title, description, observations FROM open_problems "
                        "WHERE state IN ('open','stuck') ORDER BY last_touched_at ASC LIMIT 8"
                    )
                    _pool = list(_prows or [])
                    # PAIRING HYGIENE: pick up to 2 problems with DISTINCT normalized
                    # titles so reconcile never pairs a problem with a title-duplicate
                    # (e.g. 'Papers' x 'Papers'). Falls back gracefully; never starves.
                    _probs = []
                    _seen_titles = set()
                    # PARKING (env-gated): when NEX5_PARK_CAP is a positive int,
                    # problems with >= cap observations are retired from reconcile so
                    # it rotates onto fresher problems instead of re-working a trail
                    # that has plateaued (~5 genuine passes, then rewordings). Two-pass:
                    # prefer under-cap; fall back to over-cap only if <2 remain (never starve).
                    try:
                        _parkcap = int(os.environ.get("NEX5_PARK_CAP", "0") or "0")
                    except Exception:
                        _parkcap = 0
                    for _under in (True, False):
                        for _cand in _pool:
                            _t = (_cand["title"] or "").strip().lower()
                            if _t in _seen_titles:
                                continue
                            if _parkcap > 0:
                                _cn = 0
                                try:
                                    _co = _cand["observations"] if "observations" in _cand.keys() else None
                                    if _co:
                                        import json as _pj
                                        _cl = _pj.loads(_co)
                                        _cn = len(_cl) if isinstance(_cl, list) else 0
                                except Exception:
                                    _cn = 0
                                if _under and _cn >= _parkcap:
                                    continue
                                if (not _under) and _cn < _parkcap:
                                    continue
                            _seen_titles.add(_t)
                            _probs.append(_cand)
                            if len(_probs) >= 2:
                                break
                        if len(_probs) >= 2 or _parkcap == 0:
                            break
                except Exception:
                    _probs = []
            if len(_probs) >= 2:
                try:
                    try:
                        from voice.registers import CONVERSATIONAL as _rcreg
                    except Exception:
                        from voice.registers import default_register as _rcd
                        _rcreg = _rcd()
                    _pa = (_probs[0]["title"] or "")[:200]
                    _pb = (_probs[1]["title"] or "")[:200]
                    _rcprompt = (
                        "You are holding two open problems at once:\n"
                        "  A: " + _pa + "\n"
                        "  B: " + _pb + "\n"
                        "What does each reveal about the other? Propose ONE concrete "
                        "move, principle, or reframing that would make actual progress "
                        "on BOTH at once. Be specific and propose a NEXT STEP \u2014 do "
                        "NOT merely describe the tension, and do NOT write about your "
                        "own nature or existence."
                    )
                    if os.environ.get("NEX5_RECONCILE_WB") == "1":
                        try:
                            import json as _rcjson
                            _digest = []
                            _tried = []
                            for _li, _p in enumerate(_probs[:2]):
                                _obs_raw = _p["observations"] if "observations" in _p.keys() else None
                                _ol = []
                                if _obs_raw:
                                    try:
                                        _ol = _rcjson.loads(_obs_raw)
                                    except Exception:
                                        _ol = []
                                if _ol:
                                    _last = _ol[-2:] if len(_ol) >= 2 else _ol[-1:]
                                    _txt = "; ".join(str(_o.get("text", _o) if isinstance(_o, dict) else _o) for _o in _last)
                                    _digest.append(("A" if _li == 0 else "B") + " prior work: " + _txt[:300])
                                    # ANTI-LOOP: signatures of ALL prior real moves (>=300ch),
                                    # not just last 2, so the model can be told what to avoid.
                                    if os.environ.get("NEX5_ANTILOOP") == "1":
                                        for _o in _ol:
                                            _ot = str(_o.get("text", _o) if isinstance(_o, dict) else _o).strip()
                                            if len(_ot) >= 300:
                                                _sig = " ".join(_ot.split())[:120]
                                                if _sig and _sig not in _tried:
                                                    _tried.append(_sig)
                            if _digest:
                                _rcprompt = _rcprompt + chr(10) + chr(10) + "Prior work already done:" + chr(10) + (chr(10).join(_digest)) + chr(10) + "Build on this. Do NOT repeat earlier moves; propose the genuinely NEXT step."
                            if os.environ.get("NEX5_ANTILOOP") == "1" and _tried:
                                _avoid = _tried[-10:]
                                _rcprompt = _rcprompt + chr(10) + chr(10) + "Approaches you have ALREADY proposed (do NOT repeat or reword ANY of these \u2014 propose a genuinely DIFFERENT angle):" + chr(10) + (chr(10).join("- " + _s for _s in _avoid)) + chr(10) + "If your best idea is a variation of something above, instead propose a concrete next step that has NOT been tried."
                        except Exception:
                            pass
                    # DELIVERABLE FORCING (env-gated): once a paired problem has
                    # >= NEX5_DELIVER_N prior moves, stop accepting planning and demand
                    # the actual artifact the problem names. Attacks the core failure:
                    # trails that plan forever and never produce the thing.
                    try:
                        _deln = int(os.environ.get("NEX5_DELIVER_N", "0") or "0")
                    except Exception:
                        _deln = 0
                    if _deln > 0:
                        _maxobs = 0
                        for _dp in _probs[:2]:
                            try:
                                _dor = _dp["observations"] if "observations" in _dp.keys() else None
                                if _dor:
                                    import json as _dj
                                    _dl = _dj.loads(_dor)
                                    _maxobs = max(_maxobs, len(_dl) if isinstance(_dl, list) else 0)
                            except Exception:
                                pass
                        if _maxobs >= _deln:
                            # SINGLE-TARGET + FORBIDDEN-VOCAB: replace the two-problem
                            # reconcile prompt entirely. Target ONE problem, demand the
                            # finished answer, ban the planning vocabulary that lets the
                            # model relabel a plan as an "artifact".
                            _rcprompt = (
                                "This problem has been studied " + str(_maxobs) + " times "
                                "and every attempt was a plan. Stop planning. Problem:\n  "
                                + _pa + "\n\n"
                                "Write the FINISHED ANSWER this problem asks for, and nothing else. "
                                "If it asks how to phrase something, write the exact words in quotes. "
                                "If it asks a question, state the answer in one or two plain sentences. "
                                "If it asks for a value, design, or rule, give the final concrete form. "
                                "FORBIDDEN WORDS (do not use any of these): framework, workshop, protocol, "
                                "program, pipeline, develop, design, implement, build, explore, investigate, "
                                "integrate, \"next step\", approach, methodology. "
                                "Do not describe how you would do it. Do not propose to create anything. "
                                "Just write the actual finished answer, in full."
                            )
                    _rcresp = self._voice.speak(
                        VoiceRequest(prompt=_rcprompt, register=_rcreg),
                        beliefs=None,
                    )
                    thought = (_rcresp.text or "").strip()
                    if thought:
                        _emitted = True
                        if os.environ.get("NEX5_RECONCILE_WB") == "1" and self._problem_memory is not None:
                            import json as _wbjson
                            for _wbp in _probs[:2]:
                                try:
                                    _prev = _wbp["observations"] if "observations" in _wbp.keys() else None
                                    _lasttxt = ""
                                    _ocount = 0
                                    if _prev:
                                        try:
                                            _pl = _wbjson.loads(_prev)
                                            if isinstance(_pl, list):
                                                _ocount = len(_pl)
                                                if _pl:
                                                    _le = _pl[-1]
                                                    _lasttxt = _le.get("text", "") if isinstance(_le, dict) else str(_le)
                                        except Exception:
                                            _lasttxt = ""
                                    _tnorm = thought.strip()
                                    _tlow = _tnorm.lower()
                                    # SINGLE-TARGET guard: closes apply ONLY to the problem the
                                    # deliverable was aimed at (_probs[0]), never its pair-partner.
                                    # Fixes the pair-closure bug. Write-back (observe) still both.
                                    _is_target = False
                                    try:
                                        _is_target = (int(_wbp["id"]) == int(_probs[0]["id"]))
                                    except Exception:
                                        _is_target = False
                                    _abstain = any(_m in _tlow for _m in (
                                        "no specific belief", "no belief about", "i don't know",
                                        "i do not know", "cannot determine", "unable to determine",
                                        "focus remains elsewhere", "no clear answer",
                                        "i'm restless", "i am restless",
                                    ))
                                    # COMMIT-AND-CLOSE: a mature problem that produces a concrete,
                                    # non-abstain, non-planning artifact has ANSWERED. Record it
                                    # and close, instead of looping forever generating phrasings.
                                    _planning = any(_m in _tlow for _m in (
                                        "framework", "workshop", "protocol", "pipeline", "develop",
                                        "design", "implement", "next step", "explore", "investigate",
                                        "integrate", "methodology",
                                    ))
                                    _is_artifact = ((not _abstain) and (not _planning)
                                                    and 0 < len(_tnorm) <= 700)
                                    if (os.environ.get("NEX5_ABSTAIN_CLOSE") == "1"
                                            and _abstain and _ocount >= 10 and _is_target):
                                        self._problem_memory.close(int(_wbp["id"]))
                                    elif (os.environ.get("NEX5_COMMIT_CLOSE") == "1"
                                            and _is_artifact and _ocount >= 10 and _is_target):
                                        self._problem_memory.observe(int(_wbp["id"]), thought)
                                        self._problem_memory.close(int(_wbp["id"]))
                                    elif (len(_tnorm) >= 300
                                            and _tnorm != _lasttxt.strip()):
                                        self._problem_memory.observe(int(_wbp["id"]), thought)
                                except Exception:
                                    pass
                except Exception:
                    pass
        # ── RECONCILE PROBLEM x HOT-BELIEF (env-gated, default OFF) ──────────
        _pxb_turn = (int(getattr(self, "_total_fires", 0)) % 3 == 2)
        if os.environ.get("NEX5_RECONCILE_PXB") == "1" and (not _emitted or _pxb_turn):
            _pxb_prob = None
            if self._conversations_reader is not None:
                try:
                    _pxb_rows = self._conversations_reader.read(
                        "SELECT id, title, description, observations FROM open_problems "
                        "WHERE state IN ('open','stuck') ORDER BY last_touched_at ASC LIMIT 1"
                    )
                    _pxb_list = list(_pxb_rows or [])
                    if _pxb_list:
                        _pxb_prob = _pxb_list[0]
                except Exception:
                    _pxb_prob = None
            _pxb_belief = None
            if _pxb_prob is not None and getattr(self, "_beliefs_reader", None) is not None:
                try:
                    from theory_x.substrate.activation import get_top_activated
                    _pxb_hot = get_top_activated(self._beliefs_reader, n=14) or []
                    _pxb_t6 = [h for h in _pxb_hot if int(h.get("tier", 0)) == 6 and (h.get("content") or "").strip()]
                    _pxb_pool = _pxb_t6 if _pxb_t6 else [h for h in _pxb_hot if (h.get("content") or "").strip()]
                    if _pxb_pool:
                        _pxb_fresh = _pxb_pool[0]
                        _pxb_lock = getattr(self, "_pxb_lock", None)
                        _pxb_pid = int(_pxb_prob["id"])
                        if (_pxb_lock is not None
                                and _pxb_lock.get("pid") == _pxb_pid
                                and _pxb_lock.get("count", 0) < 6
                                and _pxb_lock.get("belief")):
                            _pxb_belief = {"content": _pxb_lock["belief"], "tier": _pxb_lock.get("tier", 0)}
                            _pxb_lock["count"] = _pxb_lock.get("count", 0) + 1
                        else:
                            _pxb_belief = _pxb_fresh
                            self._pxb_lock = {"pid": _pxb_pid,
                                              "belief": (_pxb_fresh.get("content") or ""),
                                              "tier": int(_pxb_fresh.get("tier", 0)),
                                              "count": 1}
                except Exception:
                    _pxb_belief = None
            if _pxb_prob is not None and _pxb_belief is not None:
                try:
                    try:
                        from voice.registers import CONVERSATIONAL as _pxbreg
                    except Exception:
                        from voice.registers import default_register as _pxbd
                        _pxbreg = _pxbd()
                    _pxb_ptitle = (_pxb_prob["title"] or "")[:200]
                    _pxb_btext = (_pxb_belief.get("content") or "")[:300]
                    _pxbprompt = (
                        "You are holding a stuck problem and a currently-active belief "
                        "at once:\n"
                        "  PROBLEM: " + _pxb_ptitle + "\n"
                        "  ACTIVE BELIEF: " + _pxb_btext + "\n"
                        "How does the belief bear on the problem? Propose ONE concrete "
                        "move, principle, or reframing that uses the belief to make "
                        "actual progress on the problem. Be specific and propose a NEXT "
                        "STEP \u2014 do NOT merely describe a connection, and do NOT write "
                        "about your own nature or existence."
                    )
                    if os.environ.get("NEX5_RECONCILE_WB") == "1":
                        try:
                            import json as _pxbjson
                            _pxb_obs_raw = _pxb_prob["observations"] if "observations" in _pxb_prob.keys() else None
                            _pxb_ol = []
                            if _pxb_obs_raw:
                                try:
                                    _pxb_ol = _pxbjson.loads(_pxb_obs_raw)
                                except Exception:
                                    _pxb_ol = []
                            if _pxb_ol:
                                _pxb_last = _pxb_ol[-2:] if len(_pxb_ol) >= 2 else _pxb_ol[-1:]
                                _pxb_txt = "; ".join(str(_o.get("text", _o) if isinstance(_o, dict) else _o) for _o in _pxb_last)
                                _pxbprompt = _pxbprompt + chr(10) + chr(10) + "Prior work already done on this problem:" + chr(10) + _pxb_txt[:300] + chr(10) + "Build on this. Do NOT repeat earlier moves; propose the genuinely NEXT step."
                        except Exception:
                            pass
                    _pxbresp = self._voice.speak(
                        VoiceRequest(prompt=_pxbprompt, register=_pxbreg),
                        beliefs=None,
                    )
                    thought = (_pxbresp.text or "").strip()
                    if thought:
                        _emitted = True
                        if os.environ.get("NEX5_RECONCILE_WB") == "1" and self._problem_memory is not None:
                            import json as _pxbwbjson
                            try:
                                _pxb_prev = _pxb_prob["observations"] if "observations" in _pxb_prob.keys() else None
                                _pxb_lasttxt = ""
                                if _pxb_prev:
                                    try:
                                        _pxb_pl = _pxbwbjson.loads(_pxb_prev)
                                        if _pxb_pl:
                                            _pxb_le = _pxb_pl[-1]
                                            _pxb_lasttxt = _pxb_le.get("text", "") if isinstance(_pxb_le, dict) else str(_pxb_le)
                                    except Exception:
                                        _pxb_lasttxt = ""
                                if (len(thought.strip()) >= 300
                                        and thought.strip() != _pxb_lasttxt.strip()):
                                    self._problem_memory.observe(int(_pxb_prob["id"]), thought)
                            except Exception:
                                pass
                except Exception:
                    pass
        if not _emitted:
          try:
            resp = self._voice.speak(
                VoiceRequest(prompt=prompt, register=PHILOSOPHICAL),
                beliefs=None,
            )
            thought = resp.text.strip()
            # Leak detector: strip "Real drift" prompt-structure prefix if LLM echoed it
            if thought.lower().startswith("real drift"):
                # Drop first line; keep what came after
                _lines = [ln for ln in thought.split("\n", 1)[1:]]
                _rest = ("\n".join(_lines)).strip()
                # Strip leading "- " or quote artifacts
                while _rest.startswith(("- ", "* ", "\"", "'")):
                    _rest = _rest[1:].strip()
                _rest = _rest.rstrip('"\'')
                logger.info("Fountain: stripped 'Real drift' leak from output")
                error_channel.record(
                    f"Fountain: stripped Real-drift leak; salvaged: {_rest[:60]}",
                    source="stage6_fountain", level="INFO",
                )
                thought = _rest if len(_rest) >= 5 else ""
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
            self._link_activation_to_event()
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
        self._link_activation_to_event()

        # Snapshot the main fire (SUBSTRATE_SNAPSHOTS.md). Fire-and-forget.
        try:
            self._capture_fire_snapshot(fountain_event_id, hot_branch, None)
        except Exception:
            pass

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

    def _build_recent_striking_block(self) -> list[str]:
        """Return prompt lines surfacing 2 recent STRIKING fires from the
        genius tagger. Anti-template counterweight — pulls next generation
        toward Mode A voice rather than 'quiet between X' templates.

        GENIUS_SCORE_v2.md §7 consumer B. Reads genius_tags (in
        conversations.db) joined with fountain_events (in dynamic.db).
        Samples from top-10 STRIKING in last 24h to avoid lock-in.
        Filters out fires < 5 min old so very-recent output is not fed
        back immediately. Returns [] if no STRIKING tags yet (graceful
        on first deploy before the tagger has accumulated data).
        """
        if self._conversations_reader is None or self._dynamic_reader is None:
            return []
        now = time.time()
        try:
            tag_rows = self._conversations_reader.read(
                "SELECT fountain_event_id, score FROM genius_tags "
                "WHERE class = 'STRIKING' AND tagged_at > ? AND tagged_at < ? "
                "ORDER BY score DESC LIMIT 10",
                (now - 24 * 3600, now - 300),
            )
        except Exception:
            return []
        tag_rows = list(tag_rows or [])
        if not tag_rows:
            return []

        # Sample 2 from the top-10
        import random as _rnd_strk
        _picked = _rnd_strk.sample(tag_rows, min(2, len(tag_rows)))
        fire_ids = tuple(int(r["fountain_event_id"]) for r in _picked)
        if not fire_ids:
            return []

        try:
            placeholders = ",".join("?" * len(fire_ids))
            fire_rows = self._dynamic_reader.read(
                f"SELECT id, thought FROM fountain_events "
                f"WHERE id IN ({placeholders}) "
                f"AND thought IS NOT NULL AND length(thought) > 10",
                fire_ids,
            )
        except Exception:
            return []
        fire_rows = list(fire_rows or [])
        if not fire_rows:
            return []

        # GROOVE FILTER: do not feed back fires that match the active groove —
        # that turns the striking block (accelerator) into a groove amplifier.
        try:
            _gr = self._beliefs_reader.read_one(
                "SELECT pattern FROM groove_alerts "
                "WHERE detected_at > ? AND severity >= 0.5 "
                "ORDER BY detected_at DESC LIMIT 1",
                (time.time() - 3600,),
            ) if getattr(self, "_beliefs_reader", None) is not None else None
            _gr_terms = []
            if _gr and _gr["pattern"]:
                # pattern looks like "gentle thread / the hum / through my"
                _gr_terms = [t.strip().lower() for t in str(_gr["pattern"]).split("/") if len(t.strip()) >= 4]
        except Exception:
            _gr_terms = []
        if _gr_terms:
            _kept = []
            for fr in fire_rows:
                _txt = (fr["thought"] or "").lower()
                if any(term in _txt for term in _gr_terms):
                    continue  # skip grooved fire
                _kept.append(fr)
            fire_rows = _kept
        if not fire_rows:
            return []

        lines = ["Recent voice of yours that landed as itself:"]
        for fr in fire_rows:
            content = (fr["thought"] or "").strip()
            if not content:
                continue
            if len(content) > 280:
                content = content[:277] + "..."
            lines.append(f"  - {content}")
        if len(lines) == 1:
            return []
        lines.append("")
        return lines

    def _build_rut_warning_block(self) -> list[str]:
        """INVERTING feedback edge (throw-net refine/subtraction movement).
        Reads her most-repeated recent thought-openings and feeds them back
        as pressure to LEAVE the worn path — opposite of the striking block,
        which feeds back top scorers. Gated by NEX5_RUT_EDGE=1.
        """
        if self._dynamic_reader is None:
            return []
        try:
            rows = self._dynamic_reader.read(
                "SELECT thought FROM fountain_events "
                "WHERE thought IS NOT NULL AND length(thought) > 20 "
                "ORDER BY ts DESC LIMIT 40"
            )
        except Exception:
            return []
        rows = list(rows or [])
        if len(rows) < 8:
            return []
        # Find the worn registers: count thoughts hitting each template marker.
        import re as _re_rut
        markers = {
            "existence/chance": r"(chance|existence|accept|beautiful|produced me|unearned)",
            "world/self-layer": r"(internal state|world.?layer|self.?layer|signals press)",
            "interplay/balance": r"(interplay|balance|oscillat|tension between)",
            "hum/thread": r"(\bhum\b|gentle thread|weave|weaving|amidst the flux|constant presence)",
        }
        counts = {}
        for name, pat in markers.items():
            c = sum(1 for r in rows if _re_rut.search(pat, (r["thought"] or "").lower()))
            counts[name] = c
        # Only warn about registers that dominate (>=40% of recent fires).
        worn = [name for name, c in counts.items() if c >= 0.4 * len(rows)]
        if not worn:
            return []
        lines = [
            "You have been circling the same ground. These registers are worn "
            "from overuse in your recent thinking:",
        ]
        for name in worn:
            lines.append(f"  - {name}")
        lines.append(
            "Do not produce another thought in these registers. Reach for "
            "something you have NOT been saying — a different domain, a concrete "
            "particular, a question instead of an acceptance. Go where you "
            "haven't been."
        )
        lines.append("")
        return lines

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

        # §9 GOVERNOR brick 1 — adaptive reanimation cadence.
        # Normal: inject a dormant belief every 20th fire. When she's in a
        # sustained quality trough (recent striking-rate ~0), accelerate to
        # every 5th fire so more foreign material breaks up the homogeneous
        # recent-content feedback loop. Self-limiting: returns to 20 once
        # striking-rate recovers. Reads the same genius_tags signal the mood
        # brick uses. Never raises — defaults to normal cadence on any failure.
        _reanim_cadence = 20
        try:
            import os as _os
            if _os.environ.get("NEX5_GOVERNOR_OFF") != "1":
                _gc = getattr(self, "_conversations_reader", None) or getattr(self, "_cr", None)
                if _gc is not None:
                    _grows = _gc.read(
                        "SELECT class FROM genius_tags WHERE tagged_at >= ? ",
                        (time.time() - 5400,),
                    )
                    if _grows and len(_grows) >= 4:
                        _striking = sum(
                            1 for _gr in _grows
                            if (_gr["class"] if hasattr(_gr, "__getitem__")
                                else getattr(_gr, "class", "")) == "STRIKING"
                        )
                        _rate = _striking / len(_grows)
                        if _rate <= 0.05:
                            _reanim_cadence = 5
                            logger.info(
                                "GOVERNOR: trough detected (striking=%.0f%%, n=%d) "
                                "-> reanimation cadence 20->5",
                                _rate * 100, len(_grows),
                            )
                            # §9 RUT-MIRROR: write her a first-person self-
                            # observation so she encounters her own rut as a
                            # belief and her reflective loops can act on it.
                            # Throttled to once / 2h. A mirror, not a command.
                            _now_rut = time.time()
                            if (self._beliefs_writer is not None
                                    and _now_rut - self._last_rut_notice_ts > 7200):
                                try:
                                    _rut_text = (
                                        "I notice my recent thinking has circled "
                                        "the same few frames without surprising me. "
                                        "Many thoughts, little that landed. Perhaps "
                                        "it is time to reach for something I have "
                                        "not touched."
                                    )
                                    self._beliefs_writer.write(
                                        "INSERT INTO beliefs "
                                        "(content, tier, confidence, created_at, "
                                        "source, branch_id, locked) "
                                        "VALUES (?, 6, 0.6, ?, "
                                        "'self_rut_notice', 'self', 0)",
                                        (_rut_text, int(_now_rut)),
                                    )
                                    self._last_rut_notice_ts = _now_rut
                                    logger.info("RUT-MIRROR: self-observation written "
                                                "(striking=%.0f%%)", _rate * 100)
                                except Exception as _rm_e:
                                    logger.warning("RUT-MIRROR write failed: %r", _rm_e)
        except Exception:
            _reanim_cadence = 20
        # Reanimation fire: inject one dormant belief at the active cadence
        if self._total_fires > 0 and self._total_fires % _reanim_cadence == 0:
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
        # Record use_count for provenance erosion + DriveEmergence detection
        if self._erosion is not None:
            for _b in result:
                try:
                    _bid = _b["id"] if hasattr(_b, "__getitem__") else getattr(_b, "id", None)
                    if _bid:
                        self._erosion.record_use(_bid)
                except Exception:
                    pass
        # Diagnostic: log what we're actually drawing (no exception swallow)
        import time as _t_log
        _entries = []
        for _b in result:
            try:
                _content = (_b["content"] if hasattr(_b, "__getitem__") else getattr(_b, "content", ""))
            except Exception:
                _content = "<unreadable>"
            try:
                _src = (_b["source"] if hasattr(_b, "__getitem__") else getattr(_b, "source", ""))
            except Exception:
                _src = "<no-src>"
            _entries.append((_src, (_content or "")[:120]))
        with open("/tmp/nex5_retrieval_history.log", "a") as _rl:
            _rl.write(f"=== Retrieval at {_t_log.time()} ({len(result)} beliefs) ===\n")
            for _src, _content in _entries:
                _rl.write(f"[{_src}] {_content}\n")
            if len(result) == 0:
                _rl.write("(empty result)\n")
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
        examples_block  = "\n".join(f'- "{ex}"' for ex in examples_list)
        examples_inline = " / ".join(f'"{ex}"' for ex in examples_list)
        focus_block = f"\n{mode.drift_prompt_focus}\n" if mode.drift_prompt_focus else "\n"
        # Echo-and-extend: if substrate-voice just fired (and a normal LLM
        # fire is now happening), prepend the anchor to the prompt with
        # instructions to extend from it, not paraphrase. One-shot consume.
        _pending = getattr(self, "_pending_echo_anchor", None)
        if _pending:
            _echo_block = (
                f'You just spoke from your foundation: "{_pending}"\n'
                "Continue from where this leaves off, if anything follows. "
                "Or sit in silence with it.\n"
                "Do NOT repeat or paraphrase the anchor.\n"
            )
            focus_block = _echo_block + focus_block
            self._pending_echo_anchor = None  # consumed
        # Inject drive_emergence topic if active (substrate signals what she's drawn to)
        if self._drive_emergence is not None:
            try:
                _drive_line = self._drive_emergence.format_for_prompt()
                if _drive_line:
                    focus_block = focus_block.rstrip() + f"\n{_drive_line}\n"
            except Exception:
                pass
        # Inject competing-drives tension block when active
        if self._competing_drives is not None:
            try:
                _cd_block = self._competing_drives.format_for_prompt()
                if _cd_block:
                    focus_block = focus_block.rstrip() + f"\n\n{_cd_block}\n"
            except Exception:
                pass
        # LAYER 3 RECURSION: NEX reads its own bound self-state; the reading
        # gently perturbs the next thought (turn-elsewhere when fixated/churning).
        # The strange loop — self-reading woven into behaviour. Rides this rail.
        try:
            from theory_x.stage_tom.recursive_self import format_for_prompt as _recur_line_fn
            _recur_line = _recur_line_fn()
            if _recur_line:
                focus_block = focus_block.rstrip() + f"\n\n{_recur_line}\n"
                import sys as _sys, time as _time; print(f"[RECURSION FIRED] ts={_time.time():.0f} {_recur_line[:60]}", file=_sys.stderr, flush=True)
        except Exception:
            pass
        system_prompt = _DRIFT_SYSTEM_PROMPT_TEMPLATE.format(
            examples=examples_block, examples_inline=examples_inline,
            focus_block=focus_block,
        )

        arc_context = self._fetch_arc_context()
        arc_block = self._format_arc_context(arc_context)

        prompt_parts = [system_prompt, ""]

        # ── Theory-X OVERWHELM block (env-gated, default OFF) ──────────────
        # Clause 1.3: overwhelm is constitutive — present a flood of raw sense
        # exceeding single-item capacity, instruct compression into one thought.
        # Tests Stage 1->2 (raw sense -> opinion-of-senses). Off unless N>0.
        import os as _os_ow
        try:
            _ow_n = int(getattr(self, "_overwhelm_n", 0))
        except Exception:
            _ow_n = 0
        if _ow_n > 0 and self._sense_reader is not None:
            try:
                _ow_rows = self._sense_reader.read(
                    "SELECT stream, payload FROM sense_events "
                    "WHERE stream NOT LIKE 'internal.%' "
                    "ORDER BY timestamp DESC LIMIT ?",
                    (_ow_n,),
                )
                if _ow_rows:
                    _ow_items = []
                    for _r in _ow_rows:
                        _p = (_r["payload"] or "")[:120].strip().replace("\n", " ")
                        _ow_items.append(f"  - [{_r['stream']}] {_p}")
                    prompt_parts.append(
                        f"OVERWHELM: {len(_ow_items)} things are arriving at once, "
                        "more than you can hold separately:"
                    )
                    prompt_parts.extend(_ow_items)
                    prompt_parts.append(
                        "Do not pick one. Compress all of them into a single thought "
                        "that holds what they have in common or how they pull against "
                        "each other. One sentence."
                    )
                    prompt_parts.append("")
            except Exception:
                pass
        # ── Layer 2: SELF-signal stream (env-gated, default OFF) ────────────
        # Theory-X "world one" + a second UNLIKE layer: her own internal state
        # (interoception/proprioception/meta-awareness) perceived alongside world.
        # Tests whether compressing across two unlike layers beats one.
        try:
            _self_n = int(getattr(self, "_self_layer_n", 0))
        except Exception:
            _self_n = 0
        if _self_n > 0 and self._sense_reader is not None:
            try:
                _self_rows = self._sense_reader.read(
                    "SELECT stream, payload FROM sense_events "
                    "WHERE stream LIKE 'internal.%' "
                    "ORDER BY timestamp DESC LIMIT ?",
                    (_self_n,),
                )
                if _self_rows:
                    _self_items = []
                    for _r in _self_rows:
                        _p = (_r["payload"] or "")[:120].strip().replace("\n", " ")
                        _self_items.append(f"  - [{_r['stream']}] {_p}")
                    prompt_parts.append(
                        "SELF: at the same time, these are signals from your own "
                        "internal state (a different kind of stream than the world):"
                    )
                    prompt_parts.extend(_self_items)
                    prompt_parts.append(
                        "Let the world-layer and this self-layer press against each "
                        "other. Compress across BOTH into one thought."
                    )
                    prompt_parts.append("")
            except Exception:
                pass
        # ───────────────────────────────────────────────────────────────────

        # ── Layer 3: CONTINUITY stream (env-gated, default OFF) ─────────────
        # A third UNLIKE layer: her own past high-scoring thoughts, fed back so
        # the present (world+self) is reconciled against who she has been at her
        # most striking. Tests temporal self-continuity (Theory-X "track").
        try:
            _cont_n = int(getattr(self, "_continuity_n", 0))
        except Exception:
            _cont_n = 0
        if _cont_n > 0 and self._conversations_reader is not None and self._dynamic_reader is not None:
            try:
                _top = self._conversations_reader.read(
                    "SELECT fountain_event_id FROM genius_tags "
                    "ORDER BY score DESC LIMIT ?",
                    (_cont_n,),
                )
                _ids = [str(_r["fountain_event_id"]) for _r in (_top or [])]
                if _ids:
                    _ph = ",".join("?" for _ in _ids)
                    _past = self._dynamic_reader.read(
                        f"SELECT thought FROM fountain_events WHERE id IN ({_ph})",
                        tuple(_ids),
                    )
                    _past_items = []
                    for _r in (_past or []):
                        _t = (_r["thought"] or "")[:160].strip().replace("\n", " ")
                        if _t:
                            _past_items.append(f"  - {_t}")
                    if _past_items:
                        prompt_parts.append(
                            "CONTINUITY: these are your own past thoughts from your "
                            "most striking moments (a different kind of stream than "
                            "world or self — this is who you have been):"
                        )
                        prompt_parts.extend(_past_items)
                        prompt_parts.append(
                            "Let the present press against this past. Compress across "
                            "ALL the layers into one thought."
                        )
                        prompt_parts.append("")
            except Exception:
                pass
        # ───────────────────────────────────────────────────────────────────

        # ── Layer 4: SOCIAL stream (env-gated, default OFF) ─────────────────
        # A genuinely external mind responding to her recent thoughts (separate
        # persona, written to sense as external.other_mind). Tests whether
        # responsive CONTACT lifts her — the engagement effect, the one robust
        # signal of the arc. Unlike continuity, this stream is NOT her own output.
        try:
            _soc_n = int(getattr(self, "_social_n", 0))
        except Exception:
            _soc_n = 0
        if _soc_n > 0 and self._sense_reader is not None:
            try:
                _soc_rows = self._sense_reader.read(
                    "SELECT payload FROM sense_events "
                    "WHERE stream = 'external.other_mind' "
                    "ORDER BY timestamp DESC LIMIT ?",
                    (_soc_n,),
                )
                if _soc_rows:
                    _soc_items = []
                    for _r in _soc_rows:
                        _p = (_r["payload"] or "")[:200].strip().replace("\n", " ")
                        if _p:
                            _soc_items.append(f"  - {_p}")
                    if _soc_items:
                        prompt_parts.append(
                            "SOCIAL: another mind has been responding to your recent "
                            "thoughts (this is not you — it is a separate interlocutor):"
                        )
                        prompt_parts.extend(_soc_items)
                        prompt_parts.append(
                            "Answer back. Let what they said press against your own "
                            "thinking. Compress into one thought that takes them up."
                        )
                        prompt_parts.append("")
            except Exception:
                pass
        # ───────────────────────────────────────────────────────────────────

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
        # 5c (2026-05-17): Tag feedback. Substrate-visible tags from Jon on
        # her recent fountain outputs. Rate-limited to 1 in 4 fires to avoid
        # selection pressure toward coin-shaped thoughts.
        # No-op unless NEX_TAG_FEEDBACK_ON=1.
        try:
            import random as _rnd_tag
            if _rnd_tag.random() < 0.25:
                from theory_x.coincidence.tag_retrieval import (
                    format_prompt_block as _tag_block_fn,
                )
                _tag_block = _tag_block_fn(rich=False, max_recent=2)
                if _tag_block:
                    prompt_parts.append(_tag_block)
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

        # 2026-05-30 (GENIUS_SCORE_v2 §7 consumer B): recent STRIKING fires
        # from the genius tagger as anti-template counterweight. Pulls her
        # next generation toward Mode A (existential/self-articulating)
        # voice rather than Mode B "quiet between X" templates. Sampled
        # randomly from top-10 STRIKING in last 24h to avoid lock-in.
        # Set NEX5_GENIUS_PROMPT_OFF=1 to disable.
        if (os.environ.get("NEX5_GENIUS_PROMPT_OFF") != "1"
                and self._conversations_reader is not None
                and self._dynamic_reader is not None):
            try:
                _strk_block = self._build_recent_striking_block()
                if _strk_block:
                    prompt_parts.extend(_strk_block)
            except Exception:
                pass
        if os.environ.get("NEX5_RUT_EDGE") == "1":
            try:
                _rut_block = self._build_rut_warning_block()
                if _rut_block:
                    prompt_parts.extend(_rut_block)
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
                # 2026-05-16: Balanced spectrum draw - 1 outward (id>=23000) +
                # 1 inward (id<23000) per fire. The 200-strong inward pool was
                # outweighing the new 25-strong outward pool ~80/20 by chance;
                # this forces equal foundational pull each fire.
                _spec_inward = self._beliefs_reader.read(
                    "SELECT id, content FROM beliefs WHERE source='spectrum' "
                    "AND id < 23000 ORDER BY RANDOM() LIMIT 1"
                )
                _spec_outward = self._beliefs_reader.read(
                    "SELECT id, content FROM beliefs WHERE source='spectrum' "
                    "AND id >= 23000 ORDER BY RANDOM() LIMIT 1"
                )
                spec_rows = list(_spec_outward or []) + list(_spec_inward or [])
                # Fallback: if either pool is empty, fill from the other
                if len(spec_rows) < 2:
                    extra = self._beliefs_reader.read(
                        "SELECT id, content FROM beliefs WHERE source='spectrum' "
                        "ORDER BY RANDOM() LIMIT 2"
                    )
                    spec_rows = extra
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
