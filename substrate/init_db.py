"""Initialize all substrate databases.

Creates the data directory, opens a Writer per database (which creates
the file and sets WAL mode), applies the schema, and seeds keystone
beliefs into beliefs.db.

Run:
    python -m substrate.init_db

Idempotent — every schema statement uses IF NOT EXISTS; keystone
seeding uses INSERT OR IGNORE.
"""
from __future__ import annotations

import logging
import re
import sqlite3
import sys
from pathlib import Path

from .paths import data_dir, db_paths
from .writer import Writer

THEORY_X_STAGE = None

logger = logging.getLogger("substrate.init_db")

_SCHEMA_DIR = Path(__file__).parent / "schema"

_SCHEMA_FOR_DB = {
    "beliefs":       "beliefs.sql",
    "sense":         "sense.sql",
    "dynamic":       "dynamic.sql",
    "intel":         "intel.sql",
    "conversations": "conversations.sql",
    "probes":        "probes.sql",
}


def _split_sql(text: str) -> list[str]:
    # Strip SQL line comments and split on ';' — our schema files do not
    # use ';' inside literals, so this is sufficient.
    stripped = re.sub(r"--[^\n]*", "", text)
    return [s.strip() for s in stripped.split(";") if s.strip()]


def _apply_schema(writer: Writer, schema_path: Path) -> int:
    sql_text = schema_path.read_text()
    statements = _split_sql(sql_text)
    applied = 0
    for stmt in statements:
        if re.match(r"ALTER\s+TABLE\b", stmt, re.I):
            # ALTER TABLE belongs in _apply_migrations(), not schema files.
            # Skipping here prevents duplicate-column crashes on re-init.
            logger.warning("Skipping ALTER TABLE in schema file %s — use _MIGRATIONS instead", schema_path.name)
            continue
        writer.write(stmt, ())
        applied += 1
    return applied


_MIGRATIONS: dict[str, list[str]] = {
    "beliefs": [
        "CREATE TABLE IF NOT EXISTS belief_edges ("
        "id INTEGER PRIMARY KEY AUTOINCREMENT, "
        "source_id INTEGER NOT NULL REFERENCES beliefs(id), "
        "target_id INTEGER NOT NULL REFERENCES beliefs(id), "
        "edge_type TEXT NOT NULL CHECK (edge_type IN ("
        "'supports','opposes','synthesises','cross_domain','refines')), "
        "weight REAL NOT NULL DEFAULT 0.5, "
        "created_at REAL NOT NULL, "
        "last_traversed_at REAL)",
        "CREATE INDEX IF NOT EXISTS idx_edges_source ON belief_edges(source_id)",
        "CREATE INDEX IF NOT EXISTS idx_edges_target ON belief_edges(target_id)",
        "CREATE UNIQUE INDEX IF NOT EXISTS idx_edges_pair "
        "ON belief_edges(source_id, target_id, edge_type)",
        "CREATE TABLE IF NOT EXISTS belief_blacklist ("
        "id INTEGER PRIMARY KEY AUTOINCREMENT, "
        "pattern TEXT NOT NULL UNIQUE, "
        "reason TEXT NOT NULL DEFAULT '', "
        "added_at REAL NOT NULL)",
        "CREATE INDEX IF NOT EXISTS idx_blacklist_pattern ON belief_blacklist(pattern)",
        "ALTER TABLE beliefs ADD COLUMN reinforce_count INTEGER NOT NULL DEFAULT 0",
        "ALTER TABLE beliefs ADD COLUMN use_count INTEGER NOT NULL DEFAULT 0",
        "ALTER TABLE beliefs ADD COLUMN erosion_stage TEXT NOT NULL DEFAULT 'external'",
        "CREATE TABLE IF NOT EXISTS koan_reads ("
        "id INTEGER PRIMARY KEY AUTOINCREMENT, "
        "gate_id TEXT NOT NULL, "
        "read_at REAL NOT NULL)",
        "CREATE INDEX IF NOT EXISTS idx_koan_reads_gate ON koan_reads(gate_id)",
        "CREATE TABLE IF NOT EXISTS synergizer_log ("
        "id INTEGER PRIMARY KEY AUTOINCREMENT, "
        "ts REAL NOT NULL, "
        "belief_id_a INTEGER NOT NULL, "
        "belief_id_b INTEGER NOT NULL, "
        "result_content TEXT, "
        "result_belief_id INTEGER)",
        "CREATE INDEX IF NOT EXISTS idx_synergizer_ts ON synergizer_log(ts)",
        "CREATE TABLE IF NOT EXISTS fountain_crystallizations ("
        "id INTEGER PRIMARY KEY AUTOINCREMENT, "
        "fountain_event_id INTEGER NOT NULL, "
        "belief_id INTEGER NOT NULL, "
        "ts REAL NOT NULL, "
        "content TEXT NOT NULL)",
        "CREATE INDEX IF NOT EXISTS idx_crystal_event ON fountain_crystallizations(fountain_event_id)",
        "CREATE INDEX IF NOT EXISTS idx_crystal_belief ON fountain_crystallizations(belief_id)",
        "CREATE TABLE IF NOT EXISTS speech_queue ("
        "id INTEGER PRIMARY KEY AUTOINCREMENT, "
        "belief_id INTEGER NOT NULL, "
        "content TEXT NOT NULL, "
        "voice TEXT DEFAULT 'af_bella', "
        "queued_at REAL NOT NULL, "
        "spoken_at REAL, "
        "status TEXT DEFAULT 'pending', "
        "error TEXT, "
        "FOREIGN KEY (belief_id) REFERENCES beliefs(id))",
        "CREATE INDEX IF NOT EXISTS idx_speech_queue_status "
        "ON speech_queue(status, queued_at)",
        "UPDATE speech_queue SET voice='af_sarah' "
        "WHERE voice='af_bella' AND status='pending'",
        "CREATE TABLE IF NOT EXISTS config ("
        "key TEXT PRIMARY KEY, "
        "value TEXT NOT NULL, "
        "updated_at REAL NOT NULL)",
        "CREATE TABLE IF NOT EXISTS belief_activation ("
        "belief_id INTEGER PRIMARY KEY, "
        "activation REAL NOT NULL DEFAULT 0.0, "
        "last_touched_at REAL NOT NULL, "
        "FOREIGN KEY (belief_id) REFERENCES beliefs(id))",
        "CREATE INDEX IF NOT EXISTS idx_belief_activation_at "
        "ON belief_activation(last_touched_at)",
        # Phase 17 — Novel Association log
        "CREATE TABLE IF NOT EXISTS novel_association_log ("
        "id INTEGER PRIMARY KEY AUTOINCREMENT, "
        "detected_at REAL NOT NULL, "
        "belief_id_a INTEGER NOT NULL, "
        "belief_id_b INTEGER NOT NULL, "
        "branch_id_a TEXT NOT NULL, "
        "branch_id_b TEXT NOT NULL, "
        "similarity REAL NOT NULL, "
        "annotated_at REAL)",
        "CREATE UNIQUE INDEX IF NOT EXISTS idx_nassoc_pair "
        "ON novel_association_log(belief_id_a, belief_id_b)",
        "CREATE INDEX IF NOT EXISTS idx_nassoc_detected "
        "ON novel_association_log(detected_at DESC)",
        # Phase 22 — Coherence Gate decisions log
        "CREATE TABLE IF NOT EXISTS gate_decisions ("
        "id INTEGER PRIMARY KEY AUTOINCREMENT, "
        "ts REAL NOT NULL, "
        "source_node TEXT NOT NULL, "
        "outcome TEXT NOT NULL, "
        "reason TEXT NOT NULL, "
        "latency_ms REAL NOT NULL, "
        "content_preview TEXT NOT NULL, "
        "branch_id TEXT, "
        "confidence REAL)",
        "CREATE INDEX IF NOT EXISTS idx_gate_decisions_ts "
        "ON gate_decisions(ts)",
        "CREATE INDEX IF NOT EXISTS idx_gate_decisions_outcome "
        "ON gate_decisions(outcome)",
        # Phase 23 — Holding Zone
        "CREATE TABLE IF NOT EXISTS held_thoughts ("
        "id INTEGER PRIMARY KEY AUTOINCREMENT, "
        "content TEXT NOT NULL, "
        "source_node TEXT NOT NULL, "
        "confidence REAL NOT NULL, "
        "branch_id TEXT, "
        "hold_reason TEXT NOT NULL, "
        "created_at REAL NOT NULL, "
        "last_seen_at REAL NOT NULL, "
        "corroboration_count INTEGER NOT NULL DEFAULT 0, "
        "status TEXT NOT NULL DEFAULT 'holding', "
        "reshape_depth INTEGER NOT NULL DEFAULT 0, "
        "metadata TEXT)",
        "CREATE INDEX IF NOT EXISTS idx_held_status_created "
        "ON held_thoughts(status, created_at)",
        "CREATE INDEX IF NOT EXISTS idx_held_source "
        "ON held_thoughts(source_node)",
        "CREATE TABLE IF NOT EXISTS held_resolutions ("
        "id INTEGER PRIMARY KEY AUTOINCREMENT, "
        "held_id INTEGER NOT NULL, "
        "ts REAL NOT NULL, "
        "action TEXT NOT NULL, "
        "reason TEXT NOT NULL, "
        "trigger_packet_preview TEXT)",
        "CREATE INDEX IF NOT EXISTS idx_held_resolutions_held_id "
        "ON held_resolutions(held_id)",
        "CREATE INDEX IF NOT EXISTS idx_held_resolutions_ts "
        "ON held_resolutions(ts)",
        # Phase 24 — Reshape depth column (existing installs)
        "ALTER TABLE held_thoughts ADD COLUMN reshape_depth INTEGER NOT NULL DEFAULT 0",
        # Phase 25a TN-0 — Throw-Net schema
        "CREATE TABLE IF NOT EXISTS throw_net_sessions ("
        "id INTEGER PRIMARY KEY AUTOINCREMENT, "
        "session_id TEXT NOT NULL UNIQUE, "
        "topic TEXT, "
        "triggered_by TEXT NOT NULL, "
        "trigger_context TEXT, "
        "started_at REAL NOT NULL, "
        "completed_at REAL, "
        "status TEXT NOT NULL DEFAULT 'running', "
        "throw_count INTEGER NOT NULL DEFAULT 0, "
        "refined_count INTEGER NOT NULL DEFAULT 0, "
        "accepted_count INTEGER NOT NULL DEFAULT 0, "
        "metadata TEXT)",
        "CREATE INDEX IF NOT EXISTS idx_tn_sessions_status_started "
        "ON throw_net_sessions(status, started_at)",
        "CREATE INDEX IF NOT EXISTS idx_tn_sessions_topic "
        "ON throw_net_sessions(topic)",
        "CREATE TABLE IF NOT EXISTS throw_net_triggers ("
        "id INTEGER PRIMARY KEY AUTOINCREMENT, "
        "ts REAL NOT NULL, "
        "trigger_type TEXT NOT NULL, "
        "topic TEXT, "
        "source_event_id TEXT, "
        "threshold_state TEXT, "
        "fired INTEGER NOT NULL DEFAULT 0, "
        "session_id TEXT)",
        "CREATE INDEX IF NOT EXISTS idx_tn_triggers_ts_type "
        "ON throw_net_triggers(ts, trigger_type)",
        "CREATE INDEX IF NOT EXISTS idx_tn_triggers_fired "
        "ON throw_net_triggers(fired)",
        "CREATE TABLE IF NOT EXISTS throw_net_x_vars ("
        "var_id TEXT PRIMARY KEY, "
        "label TEXT NOT NULL, "
        "nex5_status TEXT NOT NULL, "
        "salience REAL NOT NULL DEFAULT 1.0, "
        "last_observed_at REAL, "
        "notes TEXT)",
        "CREATE INDEX IF NOT EXISTS idx_tn_x_vars_status "
        "ON throw_net_x_vars(nex5_status)",
        # Tag Protocol — inline JSON tag column on beliefs
        "ALTER TABLE beliefs ADD COLUMN tags TEXT NOT NULL DEFAULT '[]'",
        # arc_closers is a beliefs.db table — migration must run in the beliefs block.
        "ALTER TABLE arc_closers ADD COLUMN closure_type TEXT NOT NULL DEFAULT 'template'",
        # Phase 25b — CounterfactualNode: links accepted beliefs to source problem
        "ALTER TABLE beliefs ADD COLUMN problem_id INTEGER",
        # affinity / affinity_updated_at were read and written by
        # theory_x/life/affinity_loop.py but defined in NO schema file or
        # migration -- they exist only in the live DB (added out-of-band), so a
        # fresh init_all() produced a beliefs table without them and the first
        # affinity_tick raised "no such column: affinity". Added here; both
        # nullable (affinity IS NULL is the "not yet rated" state the loop's
        # SELECT depends on). Idempotent: skipped on the live DB that already has
        # them, created on a fresh one.
        "ALTER TABLE beliefs ADD COLUMN affinity REAL",
        "ALTER TABLE beliefs ADD COLUMN affinity_updated_at REAL",
        # D-A (affinity provenance): columns for the forward-only migration. Both
        # nullable, nothing reads them yet -- affinity_model stamps which scorer
        # wrote a row ('prov_v1'), affinity_legacy preserves the old llm value so
        # a rollback can COALESCE(affinity_legacy, affinity). Backfill is a
        # separate, dry-run-default step gated behind NEX5_AFFINITY_PROVENANCE=on.
        "ALTER TABLE beliefs ADD COLUMN affinity_model TEXT",
        "ALTER TABLE beliefs ADD COLUMN affinity_legacy REAL",
        # Schema drift (surfaced by the generalized INSERT guard): the spectrum
        # seed asserts these and both it and probe_runner read them back, but no
        # schema/migration created them -- live-DB-only. Formalise as plain
        # nullable INTEGERs: parent_belief_id holds sentinel markers (-2 process
        # cluster, -99 probe exclusion), NOT real parent ids, so NO foreign key
        # (it would reject the sentinels and any orphaned parent) and NO index at
        # this row count. A unique on (parent_belief_id, variant_index) is
        # deliberately NOT added here -- it can fail on existing live data; measure
        # first, add in a follow-up.
        "ALTER TABLE beliefs ADD COLUMN parent_belief_id INTEGER",
        "ALTER TABLE beliefs ADD COLUMN variant_index INTEGER",
        # Phase 34 — Belief uniqueness guard: closes structural gap where only
        # tier=1 locked keystones had a unique constraint; all other tiers could
        # silently accumulate duplicate content via INSERT OR IGNORE.
        # Semantic: same problem cannot have duplicate beliefs; different problems
        # can have similar exploratory content. Orphan (fountain) beliefs cannot
        # duplicate themselves. Pre-existing duplicates deduped one-off before
        # this migration applied (588 rows removed, oldest row kept per group).
        "CREATE UNIQUE INDEX IF NOT EXISTS idx_beliefs_content_problem_uniq "
        "ON beliefs(content, problem_id) "
        "WHERE problem_id IS NOT NULL",
        "CREATE UNIQUE INDEX IF NOT EXISTS idx_beliefs_content_orphan_uniq "
        "ON beliefs(content) "
        "WHERE problem_id IS NULL",
        # Round 27 — serves pop_residue's hot query directly. That query runs
        # once per fire against a 446k-row table with no supporting index:
        # measured 34ms before the ordering change and 79ms after (full SCAN
        # plus a temp B-tree for the ORDER BY). Partial on consumed_at IS NULL
        # so the index covers only the live queue, not the consumed history
        # the reaper deletes.
        "CREATE INDEX IF NOT EXISTS idx_residue_unconsumed_recent "
        "ON residue(created_at DESC) "
        "WHERE consumed_at IS NULL",
        # Substrate-voice anchor rotation (generator: least-recently-voiced T<=2
        # anchor) and provenance's recency fallback both read this; it was set by
        # an UPDATE but created in no schema, so on a fresh store the groove
        # breaker's anchor query failed silently and never fired.
        "ALTER TABLE beliefs ADD COLUMN last_voiced_at REAL",
        # Carryx §8 Step 1 — intake resonance probe.
        # Logs the cosine similarity between each newly-crystallized
        # belief and her existing standing-points (T1-T3 keystones + top T6).
        # Pure observation; does not change tier yet. Foundation for §8
        # Step 2 (tier mapping by resonance). Lives in beliefs.db: the probe
        # writes it through the beliefs Writer and intake_resonance_cli joins it
        # against beliefs (it was once mis-filed under dynamic, so a fresh
        # beliefs.db lacked it and every intake write failed).
        "CREATE TABLE IF NOT EXISTS intake_resonance_log ("
        "id INTEGER PRIMARY KEY AUTOINCREMENT, "
        "content TEXT NOT NULL, "
        "resonance REAL NOT NULL, "
        "top_match_belief_id INTEGER, "
        "ts REAL NOT NULL)",
        "CREATE INDEX IF NOT EXISTS idx_intake_resonance_ts "
        "ON intake_resonance_log(ts DESC)",
        "CREATE INDEX IF NOT EXISTS idx_intake_resonance_score "
        "ON intake_resonance_log(resonance DESC)",
        # Groove-breaker probe queue (theory_x/auto_probe/groove_breaker.py).
        # created_at defaults to insert time: competing_drives._probe_rate
        # filters on it while the breaker itself writes only ts.
        "CREATE TABLE IF NOT EXISTS auto_probe_log ("
        "id INTEGER PRIMARY KEY AUTOINCREMENT, "
        "groove_alert_id INTEGER, "
        "groove_severity REAL, "
        "dominant_opcode TEXT, "
        "sustained_fires INTEGER, "
        "selected_category TEXT, "
        "selected_probe_text TEXT, "
        "status TEXT NOT NULL DEFAULT 'observation', "
        "ts REAL NOT NULL, "
        "delivered_at REAL, "
        "created_at REAL NOT NULL "
        "DEFAULT ((julianday('now') - 2440587.5) * 86400.0))",
        "CREATE INDEX IF NOT EXISTS idx_auto_probe_log_ts "
        "ON auto_probe_log(ts DESC)",
        # World-bridge selection log (theory_x/world_bridge/selector.py): which
        # sense events were injected into a fire.
        "CREATE TABLE IF NOT EXISTS world_bridge_log ("
        "id INTEGER PRIMARY KEY AUTOINCREMENT, "
        "ts REAL NOT NULL, "
        "fountain_event_id INTEGER, "
        "selected_events_json TEXT NOT NULL DEFAULT '[]', "
        "selection_count INTEGER NOT NULL DEFAULT 0, "
        "streams_seen TEXT, "
        "injected INTEGER NOT NULL DEFAULT 0, "
        "notes TEXT)",
        "CREATE INDEX IF NOT EXISTS idx_world_bridge_log_ts "
        "ON world_bridge_log(ts DESC)",
    ],
    "dynamic": [
        "CREATE TABLE IF NOT EXISTS harmonizer_events ("
        "id INTEGER PRIMARY KEY AUTOINCREMENT, ts REAL NOT NULL, "
        "belief_id_a INTEGER, belief_id_b INTEGER, resolution TEXT, "
        "synthesis_belief_id INTEGER)",
        "CREATE TABLE IF NOT EXISTS fountain_events ("
        "id INTEGER PRIMARY KEY AUTOINCREMENT, ts REAL NOT NULL, "
        "thought TEXT NOT NULL, droplet TEXT, readiness REAL NOT NULL, "
        "hot_branch TEXT, word_count INTEGER)",
        "CREATE INDEX IF NOT EXISTS idx_fountain_ts ON fountain_events(ts)",
        "CREATE INDEX IF NOT EXISTS idx_fountain_droplet ON fountain_events(droplet)",
        "ALTER TABLE fountain_events ADD COLUMN anchor_belief_id INTEGER",
        "CREATE INDEX IF NOT EXISTS idx_fountain_anchor ON fountain_events(anchor_belief_id) WHERE anchor_belief_id IS NOT NULL",
        "ALTER TABLE fountain_events ADD COLUMN droplet TEXT",
        "CREATE TABLE IF NOT EXISTS drive_proposals ("
        "id INTEGER PRIMARY KEY AUTOINCREMENT, "
        "ts REAL NOT NULL, "
        "branch_id TEXT NOT NULL, "
        "pressure REAL NOT NULL, "
        "representative_beliefs TEXT NOT NULL, "
        "proposed_curiosity REAL NOT NULL, "
        "status TEXT NOT NULL DEFAULT 'pending')",
        "CREATE TABLE IF NOT EXISTS substrate_fires ("
        "id INTEGER PRIMARY KEY AUTOINCREMENT, "
        "ts REAL NOT NULL, "
        "parallel_fire_id INTEGER, "
        "output TEXT NOT NULL, "
        "activated_belief_id INTEGER, "
        "activation_value REAL)",
        "CREATE INDEX IF NOT EXISTS idx_substrate_fires_ts ON substrate_fires(ts)",
        # Phase 1 — stillness instrumentation
        "ALTER TABLE fountain_events ADD COLUMN stillness_reason TEXT",
        # Round 23 — record which template produced each fire, and its focal
        # item. EXPLAIN/ARGUE selection is an unseeded, unlogged _rnd.choice
        # (generator.py:239), so half of production was previously invisible;
        # focal_item retires the 50-char soak-log join.
        # NULL on substrate-voice fires, which never consult _select_wide_mode.
        "ALTER TABLE fountain_events ADD COLUMN mode TEXT",
        "ALTER TABLE fountain_events ADD COLUMN focal_item TEXT",
        "CREATE TABLE IF NOT EXISTS stillness_log ("
        "id INTEGER PRIMARY KEY AUTOINCREMENT, "
        "ts REAL NOT NULL, "
        "reason TEXT NOT NULL, "
        "retrieval_signature TEXT, "
        "consecutive_stillness_count INTEGER, "
        "jaccard REAL)",
        "CREATE INDEX IF NOT EXISTS idx_stillness_ts ON stillness_log(ts)",
        "ALTER TABLE stillness_log ADD COLUMN jaccard REAL",
        # Phase 35 — PredictiveSubstrate: prediction storage + surprise event log
        "CREATE TABLE IF NOT EXISTS predictions ("
        "id INTEGER PRIMARY KEY AUTOINCREMENT, "
        "made_at REAL NOT NULL, "
        "target_window_end REAL NOT NULL, "
        "prediction_type TEXT NOT NULL, "
        "centroid_embedding BLOB NOT NULL, "
        "representative_content TEXT, "
        "verified_at REAL, "
        "surprise_score REAL, "
        "surprise_flag INTEGER, "
        "tags TEXT NOT NULL DEFAULT '[]')",
        "CREATE INDEX IF NOT EXISTS idx_predictions_target_window "
        "ON predictions(target_window_end)",
        "CREATE INDEX IF NOT EXISTS idx_predictions_type "
        "ON predictions(prediction_type)",
        "CREATE TABLE IF NOT EXISTS surprise_events ("
        "id INTEGER PRIMARY KEY AUTOINCREMENT, "
        "triggered_at REAL NOT NULL, "
        "prediction_id INTEGER NOT NULL, "
        "prediction_type TEXT NOT NULL, "
        "surprise_score REAL NOT NULL, "
        "surprise_flag INTEGER NOT NULL, "
        "big_surprise INTEGER NOT NULL DEFAULT 0, "
        "predicted_content TEXT, "
        "actual_content TEXT, "
        "tags TEXT NOT NULL DEFAULT '[]')",
        "CREATE INDEX IF NOT EXISTS idx_surprise_events_triggered_at "
        "ON surprise_events(triggered_at DESC)",
        "CREATE INDEX IF NOT EXISTS idx_surprise_events_flag "
        "ON surprise_events(surprise_flag)",
        # Phase 37 — SelfMindView: self-mind snapshot archive
        "CREATE TABLE IF NOT EXISTS self_mind_snapshots ("
        "id INTEGER PRIMARY KEY AUTOINCREMENT, "
        "taken_at REAL NOT NULL, "
        "belief_total_count INTEGER NOT NULL, "
        "belief_t1_count INTEGER NOT NULL, "
        "belief_t2_count INTEGER NOT NULL, "
        "belief_t3_count INTEGER NOT NULL, "
        "belief_t4_count INTEGER NOT NULL, "
        "belief_avg_confidence REAL, "
        "recent_beliefs_json TEXT NOT NULL DEFAULT '[]', "
        "open_problem_count INTEGER NOT NULL, "
        "active_drive_count INTEGER NOT NULL, "
        "current_intentions_json TEXT NOT NULL DEFAULT '[]', "
        "knowledge_anchors_json TEXT NOT NULL DEFAULT '[]', "
        "review_queue_count INTEGER NOT NULL, "
        "t3_t4_count INTEGER NOT NULL, "
        "explicit_unknowns_json TEXT NOT NULL DEFAULT '[]', "
        "recent_belief_count_5m INTEGER NOT NULL, "
        "recent_gate_count_5m INTEGER NOT NULL, "
        "current_themes_json TEXT NOT NULL DEFAULT '[]', "
        "current_drive_theme TEXT, "
        "tags TEXT NOT NULL DEFAULT '[]')",
        "CREATE INDEX IF NOT EXISTS idx_self_mind_snapshots_taken_at "
        "ON self_mind_snapshots(taken_at DESC)",
        # bridge: the qualitative felt self ("I am...", hum included) written
        # alongside the quantitative ledger each 5-min snapshot. Self-ledger -> self-narrative.
        "ALTER TABLE self_mind_snapshots ADD COLUMN bound_self_synthesis TEXT",
        # Phase 38 — SocialPresence: social-presence snapshot archive
        "CREATE TABLE IF NOT EXISTS social_presence_snapshots ("
        "id INTEGER PRIMARY KEY AUTOINCREMENT, "
        "taken_at REAL NOT NULL, "
        "total_output_count_5m INTEGER NOT NULL, "
        "avg_sentence_length_words REAL, "
        "question_ratio REAL, "
        "vocab_distinctiveness REAL, "
        "avg_arousal_during_outputs REAL, "
        "vocabulary_top_words_json TEXT NOT NULL DEFAULT '[]', "
        "voice_self_report TEXT, "
        "response_count_5m INTEGER NOT NULL, "
        "avg_response_latency_s REAL, "
        "active_conversation_count INTEGER NOT NULL, "
        "topic_diversity INTEGER NOT NULL, "
        "recent_topics_json TEXT NOT NULL DEFAULT '[]', "
        "active_sessions_json TEXT NOT NULL DEFAULT '[]', "
        "engagement_self_report TEXT, "
        "tags TEXT NOT NULL DEFAULT '[]')",
        "CREATE INDEX IF NOT EXISTS idx_social_presence_taken_at "
        "ON social_presence_snapshots(taken_at DESC)",
        # Daily-life schedule (theory_x/life/daily_life.py): each activity fires
        # at most once per local calendar day -- INSERT OR IGNORE relies on the
        # (activity, date_local) key. Previously created in no schema, so a
        # fresh store failed every daily_loop tick with 'no such table'.
        "CREATE TABLE IF NOT EXISTS daily_activities ("
        "activity TEXT NOT NULL, "
        "date_local TEXT NOT NULL, "
        "fired_at REAL NOT NULL, "
        "details TEXT NOT NULL DEFAULT '', "
        "PRIMARY KEY (activity, date_local))",
        # Coincidence tag (coin/maybe/non) written by /api/coincidence/tag and
        # read by the decoder loop. Was never added by any migration, so on a
        # fresh store every decoder_tick failed with 'no such column: tag'.
        "ALTER TABLE fountain_events ADD COLUMN tag TEXT",
        # pattern_loop / witness_loop create these on their first compose-hour
        # tick; until then the decoder's daemon counts queried tables that did
        # not exist (surfaced by NEX5_SCHEMA_TRIPWIRE on the fresh store).
        # Same DDL as the loops.
        "CREATE TABLE IF NOT EXISTS pattern_log ("
        "id INTEGER PRIMARY KEY AUTOINCREMENT, "
        "composed_at REAL NOT NULL, "
        "date_local TEXT NOT NULL, "
        "hour_local INTEGER NOT NULL, "
        "statement TEXT NOT NULL, "
        "UNIQUE(date_local, hour_local))",
        "CREATE TABLE IF NOT EXISTS witness_log ("
        "id INTEGER PRIMARY KEY AUTOINCREMENT, "
        "composed_at REAL NOT NULL, "
        "date_local TEXT NOT NULL, "
        "statement TEXT NOT NULL, "
        "UNIQUE(date_local))",
        # The open problem she is currently working (theory_x/sustained/
        # focus_loop.py): a single row, id=1; problem_id -> open_problems.id in
        # conversations.db. Read by daily_life, identity_loop, virya, provenance.
        "CREATE TABLE IF NOT EXISTS current_focus ("
        "id INTEGER PRIMARY KEY CHECK (id = 1), "
        "problem_id INTEGER NOT NULL, "
        "picked_at REAL NOT NULL, "
        "observations_at_pick INTEGER NOT NULL DEFAULT 0)",
        # Coincidence module (theory_x/coincidence/): the substrate context
        # frozen when a fire is tagged coin/maybe/non, one row per fire.
        "CREATE TABLE IF NOT EXISTS coincidence_context ("
        "fountain_event_id INTEGER PRIMARY KEY, "
        "tagged_at REAL NOT NULL, "
        "tag TEXT, "
        "aperture REAL, "
        "hot_branch TEXT, "
        "branch_activations TEXT, "
        "recent_fountain TEXT, "
        "recent_surprises TEXT, "
        "recent_daemons TEXT, "
        "belief_delta_1h INTEGER, "
        "groove_alerts TEXT, "
        "last_identity TEXT, "
        "last_pattern TEXT, "
        "last_witness TEXT, "
        "full_snapshot TEXT)",
        # Per-word decoder rows (theory_x/coincidence/decoder_loop.py), one per
        # word of each fire, with the substrate state at that fire.
        "CREATE TABLE IF NOT EXISTS word_contexts ("
        "id INTEGER PRIMARY KEY AUTOINCREMENT, "
        "word TEXT NOT NULL, "
        "fountain_event_id INTEGER NOT NULL, "
        "ts REAL, "
        "aperture REAL, "
        "hot_branch TEXT, "
        "surprises_30min INTEGER, "
        "daemons_5min INTEGER, "
        "belief_delta_1h INTEGER, "
        "fountain_tag TEXT, "
        "hour_of_day INTEGER, "
        "day_of_week INTEGER, "
        "seconds_since_feed REAL, "
        "seconds_since_daemon REAL, "
        "active_branch_count INTEGER, "
        "groove_active INTEGER)",
        "CREATE INDEX IF NOT EXISTS idx_word_contexts_word "
        "ON word_contexts(word)",
        "CREATE INDEX IF NOT EXISTS idx_word_contexts_event "
        "ON word_contexts(fountain_event_id)",
        # Operator word tags (key/noise/unsure) and coincidence hypotheses,
        # both written from the GUI (gui/server.py).
        "CREATE TABLE IF NOT EXISTS word_tags ("
        "word TEXT PRIMARY KEY, "
        "tag TEXT NOT NULL, "
        "tagged_at REAL NOT NULL, "
        "note TEXT)",
        "CREATE TABLE IF NOT EXISTS hypotheses ("
        "id INTEGER PRIMARY KEY AUTOINCREMENT, "
        "created_at REAL NOT NULL, "
        "claim TEXT NOT NULL, "
        "keywords TEXT, "
        "time_window TEXT, "
        "status TEXT NOT NULL DEFAULT 'open', "
        "supporting INTEGER NOT NULL DEFAULT 0, "
        "contradicting INTEGER NOT NULL DEFAULT 0, "
        "closed_at REAL, "
        "notes TEXT)",
    ],
    "conversations": [
        # NEX5_PROVENANCE — what she held going INTO a turn, written before the
        # reply is composed, so reply provenance can be scored against a small
        # pre-turn set later instead of the whole belief graph.
        "CREATE TABLE IF NOT EXISTS provenance_snapshots ("
        "id INTEGER PRIMARY KEY AUTOINCREMENT, "
        "session_id TEXT, "
        "ts REAL NOT NULL, "
        "focus_problem_id INTEGER, "
        "focus_title TEXT, "
        "focal_thought TEXT, "
        "belief_ids TEXT NOT NULL DEFAULT '[]', "
        "belief_texts TEXT NOT NULL DEFAULT '[]', "
        "valence REAL, "
        "arousal REAL, "
        "stability REAL, "
        "mood_label TEXT, "
        "user_turn TEXT, "
        # 'retrieved' = the belief block actually assembled into that turn's reply
        # prompt; 'recency' = the pre-2026-09-22 proxy (25 most recently touched),
        # which measured as a null. Never pool the two in one analysis.
        "belief_source TEXT NOT NULL DEFAULT 'recency')",
        "CREATE INDEX IF NOT EXISTS idx_prov_snap_ts ON provenance_snapshots(ts DESC)",
        "ALTER TABLE provenance_snapshots ADD COLUMN belief_source TEXT NOT NULL DEFAULT 'recency'",
        "CREATE TABLE IF NOT EXISTS open_problems ("
        "id INTEGER PRIMARY KEY AUTOINCREMENT, "
        "title TEXT NOT NULL, "
        "description TEXT NOT NULL, "
        "state TEXT NOT NULL DEFAULT 'open', "
        "created_at REAL NOT NULL, "
        "last_touched_at REAL NOT NULL, "
        "plan TEXT NOT NULL DEFAULT '', "
        "observations TEXT NOT NULL DEFAULT '[]', "
        "resolved_at REAL)",
        "CREATE INDEX IF NOT EXISTS idx_problems_state ON open_problems(state)",
        "ALTER TABLE messages ADD COLUMN tool_used TEXT",
        "CREATE TABLE IF NOT EXISTS goals ("
        "id INTEGER PRIMARY KEY AUTOINCREMENT, "
        "title TEXT NOT NULL, "
        "description TEXT NOT NULL DEFAULT '', "
        "priority REAL NOT NULL DEFAULT 0.5, "
        "state TEXT NOT NULL DEFAULT 'open', "
        "source TEXT NOT NULL DEFAULT 'user', "
        "created_at REAL NOT NULL, "
        "last_touched_at REAL NOT NULL, "
        "completed_at REAL, "
        "problem_id INTEGER REFERENCES open_problems(id))",
        "CREATE INDEX IF NOT EXISTS idx_goals_state ON goals(state)",
        "CREATE INDEX IF NOT EXISTS idx_goals_priority ON goals(priority DESC)",
        "CREATE TABLE IF NOT EXISTS narrative_log ("
        "id INTEGER PRIMARY KEY AUTOINCREMENT, "
        "content TEXT NOT NULL, "
        "trigger TEXT NOT NULL, "
        "source_id INTEGER, "
        "created_at REAL NOT NULL)",
        "CREATE INDEX IF NOT EXISTS idx_narrative_ts ON narrative_log(created_at DESC)",
        # Phase 27 — AffectState (single-row table; id=1 always)
        "CREATE TABLE IF NOT EXISTS affect_state ("
        "id         INTEGER PRIMARY KEY, "
        "valence    REAL    NOT NULL DEFAULT 0.0, "
        "arousal    REAL    NOT NULL DEFAULT 0.1, "
        "stability  REAL    NOT NULL DEFAULT 0.9, "
        "mood_label TEXT    NOT NULL DEFAULT 'neutral', "
        "updated_at REAL    NOT NULL)",
        # affect_history — append-only trace of every affect tick, feeding
        # CompetingDrives' affect_variance (added 2026-05-20). It had NO CREATE
        # anywhere, so the INSERT in affect_state.py failed and was swallowed and
        # the variance signal read an empty table since. Declared here so the
        # loop actually closes. (Retention: nex_db_reaper TARGETS, 30d.)
        "CREATE TABLE IF NOT EXISTS affect_history ("
        "id         INTEGER PRIMARY KEY AUTOINCREMENT, "
        "ts         REAL    NOT NULL, "
        "valence    REAL, "
        "arousal    REAL, "
        "stability  REAL, "
        "mood_label TEXT)",
        "CREATE INDEX IF NOT EXISTS idx_affect_history_ts ON affect_history(ts DESC)",
        # self_present — the structured, persisted present (Phase A / W3). Carries
        # the chat arbiter's candidate salience vector across turns, per session,
        # so attention has continuity. Written only when NEX5_SELF_PRESENT=1.
        "CREATE TABLE IF NOT EXISTS self_present ("
        "session_id      TEXT PRIMARY KEY, "
        "winner_kind     TEXT, "
        "winner_salience REAL, "
        "salience_json   TEXT, "
        "turn_count      INTEGER NOT NULL DEFAULT 0, "
        "updated_at      REAL NOT NULL)",
        # Phase 29 — DriveEmergence (single-row table; id=1 always; INSERT OR REPLACE)
        "CREATE TABLE IF NOT EXISTS drives ("
        "id                 INTEGER PRIMARY KEY, "
        "topic              TEXT    NOT NULL, "
        "source_beliefs     TEXT    NOT NULL, "
        "drive_strength     REAL    NOT NULL, "
        "repetition_score   REAL    NOT NULL, "
        "convergence_score  REAL    NOT NULL, "
        "formed_at          REAL    NOT NULL, "
        "last_reinforced_at REAL    NOT NULL, "
        "reinforce_count    INTEGER NOT NULL DEFAULT 1)",
        # Row 9 Stillness — append-only log; Fountain reads most-recent active row
        "CREATE TABLE IF NOT EXISTS stillness_log ("
        "id          INTEGER PRIMARY KEY AUTOINCREMENT, "
        "started_at  REAL    NOT NULL, "
        "duration_s  REAL    NOT NULL, "
        "expires_at  REAL    NOT NULL, "
        "trigger     TEXT    NOT NULL, "
        "groove_count INTEGER NOT NULL)",
        "CREATE INDEX IF NOT EXISTS idx_stillness_log_expires "
        "ON stillness_log(expires_at DESC)",
        # Phase 29b — DriveEmergence observability log (append-only, no behavior change)
        "CREATE TABLE IF NOT EXISTS drive_emergence_log ("
        "id                  INTEGER PRIMARY KEY AUTOINCREMENT, "
        "tick_at             REAL    NOT NULL, "
        "candidates_examined INTEGER NOT NULL, "
        "top_candidates      TEXT    NOT NULL, "
        "rejection_reasons   TEXT    NOT NULL, "
        "thresholds_snapshot TEXT    NOT NULL, "
        "drive_formed_id     TEXT, "
        "tick_duration_ms    REAL    NOT NULL)",
        "CREATE INDEX IF NOT EXISTS idx_drive_emergence_log_tick_at "
        "ON drive_emergence_log(tick_at)",
        # Tag Protocol — inline JSON tag column on open_problems
        "ALTER TABLE open_problems ADD COLUMN tags TEXT NOT NULL DEFAULT '[]'",
        # Phase 25b — CounterfactualNode: problems promoted here after 3 ACCEPTs
        "CREATE TABLE IF NOT EXISTS review_queue ("
        "id INTEGER PRIMARY KEY, "
        "title TEXT NOT NULL, "
        "description TEXT, "
        "created_at REAL NOT NULL, "
        "flagged_at REAL NOT NULL, "
        "tags TEXT NOT NULL DEFAULT '[]')",
        "CREATE INDEX IF NOT EXISTS idx_review_queue_flagged_at "
        "ON review_queue(flagged_at DESC)",
        # CHORD §4 deliverable C — substrate_harmonic coherence metric
        # Log-only at phase 1; consumers (HUD panel, future mirror-character,
        # chord-aware arc closure) read but do not write.
        "CREATE TABLE IF NOT EXISTS substrate_coherence ("
        "id INTEGER PRIMARY KEY AUTOINCREMENT, "
        "ts REAL NOT NULL, "
        "total REAL NOT NULL, "
        "pair_scores TEXT NOT NULL, "
        "walk_state TEXT, "
        "walk_anchor_id INTEGER, "
        "drive_conflict TEXT, "
        "notes TEXT)",
        "CREATE INDEX IF NOT EXISTS idx_coherence_ts "
        "ON substrate_coherence(ts DESC)",
        # GENIUS_SCORE_v2 step 1 — training set for logistic regression fit.
        # Jon flags fires as striking=1 / ordinary=0; the v2 score weights
        # are fit against this table. Sparse (~40-60 rows expected).
        "CREATE TABLE IF NOT EXISTS genius_training ("
        "fountain_event_id INTEGER PRIMARY KEY, "
        "striking INTEGER NOT NULL CHECK (striking IN (0, 1)), "
        "flagged_at REAL NOT NULL, "
        "flagged_by TEXT NOT NULL DEFAULT 'jon', "
        "notes TEXT)",
        "CREATE INDEX IF NOT EXISTS idx_genius_training_striking "
        "ON genius_training(striking)",
        # GENIUS_SCORE_v2 §7a — auto-tagger output table.
        # Every fountain fire scored against the fitted v2 weights gets one
        # row per (fountain_event_id, weights_version). UNIQUE allows old
        # and new weight versions to coexist when Jon re-fits. Log-only at
        # phase 1; future consumers (retrieval bias, fountain prompt
        # context) read but do not write.
        "CREATE TABLE IF NOT EXISTS genius_tags ("
        "id INTEGER PRIMARY KEY AUTOINCREMENT, "
        "fountain_event_id INTEGER NOT NULL, "
        "score REAL NOT NULL, "
        "class TEXT NOT NULL CHECK (class IN ('STRIKING', 'ordinary')), "
        "weights_version TEXT NOT NULL, "
        "tagged_at REAL NOT NULL, "
        "UNIQUE(fountain_event_id, weights_version))",
        "CREATE INDEX IF NOT EXISTS idx_genius_tags_score "
        "ON genius_tags(score DESC)",
        "CREATE INDEX IF NOT EXISTS idx_genius_tags_event "
        "ON genius_tags(fountain_event_id)",
        "CREATE INDEX IF NOT EXISTS idx_genius_tags_tagged_at "
        "ON genius_tags(tagged_at DESC)",
        # Trust stamp: what NEX knew about her own reliability at the moment
        # she made a voice prediction. Recorded, not acted on -- acting on it
        # (abstaining/deferring when trust is low) would remove the very
        # measurement this scorecard exists to produce.
        "ALTER TABLE world_predictions ADD COLUMN trust_level TEXT",
        "ALTER TABLE world_predictions ADD COLUMN trust_gap REAL",
        "ALTER TABLE world_predictions ADD COLUMN trust_n INTEGER",
        # Competing drives (theory_x/stage_drives/competing_drives.py): one live
        # row (id=1) of drive weights, plus a per-tick history the synergizer
        # and fountain read back. Previously created in no schema, so a fresh
        # store silently never persisted drive state.
        "CREATE TABLE IF NOT EXISTS drives_competing ("
        "id INTEGER PRIMARY KEY, "
        "coherence REAL NOT NULL, "
        "exploration REAL NOT NULL, "
        "integration REAL NOT NULL, "
        "self_preservation REAL NOT NULL, "
        "curiosity REAL NOT NULL, "
        "tension_pairs TEXT NOT NULL DEFAULT '[]', "
        "computed_at REAL NOT NULL)",
        "CREATE TABLE IF NOT EXISTS drives_competing_log ("
        "id INTEGER PRIMARY KEY AUTOINCREMENT, "
        "tick_at REAL NOT NULL, "
        "weights_json TEXT NOT NULL, "
        "inputs_json TEXT, "
        "tension_active INTEGER NOT NULL DEFAULT 0)",
        "CREATE INDEX IF NOT EXISTS idx_drives_competing_log_tick "
        "ON drives_competing_log(tick_at DESC)",
        # Per-fire drive activation and the per-drive-pair voice profile
        # (competing_drives.compute_now / drive_history). DDL as recorded in
        # journal/JOURNAL_2026-05-19.md (commit 8a348c5); it was applied to the
        # live DB by hand and never registered here.
        "CREATE TABLE IF NOT EXISTS drive_activations ("
        "id INTEGER PRIMARY KEY AUTOINCREMENT, "
        "fountain_event_id INTEGER, "
        "timestamp REAL NOT NULL, "
        "coherence_weight REAL NOT NULL, "
        "exploration_weight REAL NOT NULL, "
        "integration_weight REAL NOT NULL, "
        "self_preservation_weight REAL NOT NULL, "
        "curiosity_weight REAL NOT NULL, "
        "active_conflicts TEXT, "
        "resolution_summary TEXT)",
        "CREATE INDEX IF NOT EXISTS idx_drive_activations_ts "
        "ON drive_activations(timestamp)",
        "CREATE TABLE IF NOT EXISTS voice_profile ("
        "id INTEGER PRIMARY KEY AUTOINCREMENT, "
        "drive_pair TEXT NOT NULL UNIQUE, "
        "resolution_pattern TEXT, "
        "frequency INTEGER NOT NULL DEFAULT 1, "
        "signature_vocabulary TEXT, "
        "updated_at REAL NOT NULL)",
    ],
}


_ALTER_COL_RE = re.compile(
    r"ALTER\s+TABLE\s+(\w+)\s+ADD\s+COLUMN\s+(\w+)", re.I
)


def _column_exists(db_path: str, table: str, column: str) -> bool:
    """Read-only PRAGMA check via direct sqlite3 — safe alongside WAL Writer."""
    try:
        with sqlite3.connect(f"file:{db_path}?mode=ro", uri=True) as conn:
            rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
            return any(row[1] == column for row in rows)
    except Exception:
        return False  # DB not yet created or unreadable — let the write proceed


def _table_exists(db_path: str, table: str) -> bool:
    """Read-only check whether a table exists — direct sqlite3, WAL-safe.

    Distinct from _column_exists: an ADD COLUMN migration must be skipped when
    the *table* is absent, not just when the column is. Some tables (e.g.
    world_predictions, conversations.db) are created lazily by their own module
    rather than during init_db, so running their ALTERs here fires against a
    non-existent table -- a swallowed "no such table" error whose only legacy
    was log noise, while the columns never landed on a fresh DB. The table's
    own creator owns the full schema; here we migrate only what already exists.
    """
    try:
        with sqlite3.connect(f"file:{db_path}?mode=ro", uri=True) as conn:
            rows = conn.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
                (table,),
            ).fetchall()
            return bool(rows)
    except Exception:
        return False  # DB/table not readable — treat as absent, skip the ALTER


def _apply_migrations(writers: dict[str, Writer]) -> None:
    """Apply additive migrations for existing databases.

    ALTER TABLE ADD COLUMN statements are pre-checked via PRAGMA table_info
    so the column-already-exists case is skipped before touching the Writer.
    This prevents the Writer's worker thread from logging a spurious ERROR for
    an expected, harmless condition on existing databases.
    """
    for db_name, stmts in _MIGRATIONS.items():
        w = writers.get(db_name)
        if w is None:
            continue
        for stmt in stmts:
            m = _ALTER_COL_RE.match(stmt.strip())
            if m:
                table, col = m.group(1), m.group(2)
                if not _table_exists(w.db_path, table):
                    continue  # table not created yet (lazy creator owns schema)
                if _column_exists(w.db_path, table, col):
                    continue  # column already exists — skip silently
            try:
                w.write(stmt, ())
            except Exception:
                pass  # CREATE IF NOT EXISTS etc. are idempotent; swallow any remainder


def init_all() -> None:
    data_dir().mkdir(parents=True, exist_ok=True)
    paths = db_paths()
    writers: dict[str, Writer] = {}
    try:
        for name, path in paths.items():
            schema_file = _SCHEMA_DIR / _SCHEMA_FOR_DB[name]
            w = Writer(path, name=name)
            writers[name] = w
            applied = _apply_schema(w, schema_file)
            logger.info("Initialized %s (%d statements)", path, applied)

        # Apply additive column migrations for existing DBs (idempotent)
        _apply_migrations(writers)

        # Seed Tier 1 keystones into beliefs.db.
        from keystone import reseed as keystone_reseed
        keystone_reseed(writers["beliefs"])
        logger.info("Keystone seeds applied to beliefs.db")

        # Seed contamination blacklist.
        from substrate.blacklist_seeds import seed_blacklist
        seed_blacklist(writers["beliefs"])
        logger.info("Blacklist seeds applied to beliefs.db")

        # Seed koan beta beliefs.
        from substrate.koan_seeds import seed_koans
        seed_koans(writers["beliefs"])
        logger.info("Koan beta beliefs seeded to beliefs.db")
    finally:
        for w in writers.values():
            w.close()


def main() -> int:
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s"
    )
    init_all()
    print("Substrate initialized.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
