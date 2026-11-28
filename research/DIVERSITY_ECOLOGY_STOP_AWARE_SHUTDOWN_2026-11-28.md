# Diversity ecology and substrate harmonic shutdown — 28 November 2026

**Base:** main at 55fd635bd535d15ece3e3878bf1e71621f56fa7c.  
**Scope:** cooperative stop checkpoints through the 60-second DiversityLoop, its groove/dormancy/consolidation stages, and the log-only SubstrateHarmonic worker. No scoring formulas, thresholds, weights, cadences, schemas or feature flags changed.

## 1. Source evidence

- DiversityLoop is AppState-managed and runs GrooveSpotter, DormancyScanner and ClockRunner sequentially every 60 seconds.
- GrooveSpotter reads a rolling belief window, detects exact/gram/template repetition, and embeds current/previous windows for centroid tightening. It can write groove_alerts and signal_cooldown rows.
- DormancyScanner reads up to 50 beliefs, computes average gap and writes dormant_beliefs rows.
- ClockRunner has fast/medium/slow stages. Fast applies decay across belief_boost rows, runs dormancy scoring and may reanimate one belief. Medium reads groove/branch findings. Slow runs GraderEvolver across collision grades, retrospective reads and mismatch/version writes.
- SubstrateHarmonic is a separate log-only worker. Each tick reads eight streams sequentially, computes pair scores and writes one substrate_coherence row.
- Before this change, DiversityLoop checked its Event only between 60-second waits; component operations and the harmonic tick did not receive it.

## 2. Bounded correction

- Pass DiversityLoop's Event into GrooveSpotter, DormancyScanner and ClockRunner; stop between components.
- GrooveSpotter checks between detector stages, within template comparisons and between centroid embeddings; it checks before alert and cooldown writes.
- DormancyScanner checks after its initial read and average-gap read, then between per-belief writes.
- ClockRunner checks between fast/medium/slow stages and only advances each clock's last-run fire count when that stage completes. Fast passes the Event into decay, dormancy and reanimation; slow passes it into GraderEvolver.
- apply_decay checks between boost-row updates; wake_one checks before its single reanimation write.
- GraderEvolver checks between grade samples, retrospective Reader calls, mismatch writes and grader-version persistence.
- SubstrateHarmonic reads streams sequentially with checks between Readers and checks before its single log write.
- Add deterministic Event-based regressions for component handoff, centroid embedding, dormancy, clock stages, decay, grader evolution and harmonic stream reads.

## 3. Boundaries and residuals

- Individual Reader/SQLite calls and NumPy fitting/centroid calculations are synchronous and not forcibly cancelled; the current call/calculation must return before stop is observed.
- A per-belief update or alert write already started may complete. Groove alert and cooldown rows remain separate writes; cooldown is skipped if stop is observed after the alert.
- A reanimation row already written may complete; no later clock stage starts after stop.
- Grader-version persistence is skipped if stop arrives during sample collection, mismatch detection or fitting. Mismatch rows already written remain.
- SubstrateHarmonic's single row write already started may complete.
- This does not establish host-level process quiescence.

## 4. Validation

Exact-head full-suite CI and baseline verification are required before merge. Tests use mocked Readers/Writers and deterministic Events.
