# decryption/

Probe and analysis subsystem — tooling for examining NEX's cognition from the
outside. These characterize behavior; they do not drive the live fire loop.

**Probing**
- `probe_set.py` — probe condition definitions and experimental-matrix generation (each condition = one structured experimental configuration).
- `probe_runner.py` — executes probes systematically against a live NEX instance, instantiating each condition N times.
- `probes_db.py` — SQLite schema and typed read/write for probe results (`data/probes.db`).

**Analysis**
- `classifier.py` — template/register classifier for fountain output, using the 8-category scheme from the corpus analysis (ABSTRACT_NOMINAL, etc.).
- `differential_analyzer.py` — pairwise divergence analysis between probe conditions that differ in exactly one dimension.
- `atlas_builder.py` — compiles probe results into a condition × opcode matrix: which input configurations reliably produce which output templates.

**Phase 1 predictive model**
- `nex_cognition_simulator.py` — rule-derived predictive model of NEX's cognition.
- `spark_detector.py` — classifies simulator misses (predicted ≠ actual) by type (noise vs. genuine divergence).

## Safety boundary — live ProbeRunner

`probe_runner.py` is an explicit experiment tool, not a harmless read-only analyser. Its default is `dry_run=False`; when run in that mode it changes the live NEX mode through the GUI API and writes synthetic `fountain_insight` rows directly into the beliefs database. It attempts to delete those rows in `finally`, but the injected-ID list is in-memory only, cleanup failure clears that list, abrupt process termination bypasses cleanup, and the previous NEX mode is not restored.

Do not run it against a live NEX instance without explicit experiment approval and a verified disposable database/runtime. `dry_run=True` suppresses mode changes and synthetic writes/deletes, but still performs read-only inspection of the beliefs database. This warning applies to `decryption/probe_runner.py`, not to the separate `theory_x.probes.probe_runner.ProbeRunner` subsystem.
