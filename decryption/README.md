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
