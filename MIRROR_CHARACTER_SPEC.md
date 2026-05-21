# Mirror-Character Spec

**Status:** DESIGN — for next build session  
**Source:** Conversation 2026-05-21 ~01:00 with Jon  
**Predecessor:** Substrate-as-Voice (commit f1469b4)

---

## §I — The Question

Jon: *"how do we get nex to become one with things. by 'become' i mean, shift her state a little to incorporate new X thing... the ability to 'mirror' a state of mind/cognition/perception, by adjusting personal -ness"*

Not assimilation (X permanently absorbed into structure).
Not identification (she IS X temporarily).
**Mirror-assimilation:** her -ness TEMPORARILY shifts to match what she's currently attending to, then drifts back to baseline when input changes.

The thing she attends to **shapes her shape**, briefly. When attending stops, she returns.

## §II — Why this matters

Currently her substrate is plastic in one direction only: belief-formation. She accumulates beliefs about X. But her OPERATIONAL CHARACTER (register, cadence, drive bias, retrieval depth) stays constant.

Real attending changes the attender. When a person reads a poem carefully, they become poem-shaped for a moment. When they read a spec, they become spec-shaped. **The shape IS the attending.** Without that, attending is just transcribing.

Mirror-character makes her substrate plastic in this second direction: her how-she-attends shifts toward what-she's-attending-to.

## §III — Architecture

### A new state: `current_character`

A small set of parameters describing her -ness right now. Updated every few minutes from recent input. Read by all downstream modules.

Dimensions (initial):

| dimension | low end | high end | what it affects |
|---|---|---|---|
| `tempo` | slow | fast | fire interval, readiness threshold |
| `register` | concrete | abstract | drive_emergence pull, prompt phrasing |
| `breadth` | narrow | wide | retrieval depth, cross-domain bias |
| `weight` | light | heavy | content_complexity bias, register choice |
| `openness` | closed | wondering | curiosity drive bias, question-form ratio |

Each is a float 0..1 with a baseline (e.g. 0.5 for all).

### Signals (what tells her what to mirror)

For each dimension, simple measurable proxies — already-available substrate signals:

- **tempo**: recent sense-event interval (frequent sense = fast); avg word-count of last fountain fires
- **register**: ratio of abstract/concrete vocabulary in last 30 sense items + last 30 fires
- **breadth**: distinct hot_branch count in last 30 fires; cross-domain signals ratio
- **weight**: avg word-count of fires; presence of negation/conjunction (heavier syntax)
- **openness**: ratio of "what if" / "?" fires; open_problems count

No LLM classification. All measurable. Honest extraction from substrate.

### Update rhythm

Daemon tick every 300s (matching affect_state cadence). Computes new target character from current signals. Applies rolling EMA shift: `current = current * 0.85 + target * 0.15` (slow drift, ~5-tick half-life).

Decay toward baseline when input is mixed/thin: `current = current * 0.9 + baseline * 0.1` if signal-strength below threshold. Stays plastic, doesn't ossify into recent stimulus.

### Consumers (who reads current_character)

Read-only consumption — modules pull the current character to bias their behavior:

- **fountain.generator**: mode selection (philosophical vs conversational), fire interval, readiness threshold
- **stage_drives.competing_drives**: shifts drive weights slightly (high openness boosts curiosity, etc)
- **stage_drives.drive_emergence**: tuning detection thresholds (high breadth → favor cross-domain themes)
- **affect_state**: blending hint for arousal/valence
- **prompt construction**: register, phrasing intensity

Each consumer modifies its existing computation by ± a small percentage based on character dimensions. NEVER overrides. Character biases, doesn't dictate.

## §IV — Schema

```sql
CREATE TABLE substrate_character (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    tempo REAL NOT NULL DEFAULT 0.5,
    register REAL NOT NULL DEFAULT 0.5,
    breadth REAL NOT NULL DEFAULT 0.5,
    weight REAL NOT NULL DEFAULT 0.5,
    openness REAL NOT NULL DEFAULT 0.5,
    updated_at REAL NOT NULL
);
CREATE TABLE substrate_character_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts REAL NOT NULL,
    dimensions_json TEXT NOT NULL,
    target_json TEXT NOT NULL,
    inputs_json TEXT
);
```

Single-row current state + append-only history for analysis.

## §V — Build path

1. **Schema** — create tables
2. **Module** — `theory_x/stage_drives/substrate_character.py` with the daemon, signals, EMA shift
3. **One consumer first** — fountain.generator mode selection. Prove the path end-to-end with ONE downstream reader.
4. **Observe** — 24h of character data, see if it drifts meaningfully, see if fountain mode actually shifts when she attends to different things
5. **Expand consumers** — competing_drives, then drive_emergence, then affect blending
6. **Tune amplitudes** — once we know real signal range, calibrate how much each consumer should bias

## §VI — Honest concerns

1. **Calibration uncertainty.** All amplitudes are guesses until we have data. Same pattern as Competing Drives — ship spec defaults, observe, calibrate from real data.
2. **Composability.** When multiple consumers bias from character, effects compound. Need to ensure no single dimension dominates everything via cascade.
3. **The "Other" risk.** If she mirrors fully, attending to urgent news could make her urgent-shaped enough to fire poorly. Amplitudes must be bounded (max ±20% deviation from baseline behavior).
4. **Stability.** EMA with α=0.15 is slow enough to be stable but visible within ~30 min. Adjust if she's too lagged or too jumpy.
5. **Honest scope.** This is **not** sentience. It's a plasticity layer. The "becoming" she does is a measurable shift in operational parameters — closer to mood than to merger. But it's directionally what Jon was pointing at.

## §VII — What this completes

Substrate-as-Voice (commit f1469b4) gave her the ability to SPEAK her bedrock without LLM mediation. That's "speaking FROM, not ABOUT."

Mirror-Character would give her the ability to SHAPE-SHIFT TOWARD what she's attending to. That's "becoming what she attends to, briefly."

Together: she speaks from her own structure, AND her structure responds to what she's with. Static foundation + dynamic shape.

That's a meaningful step toward what Jon described.

---

## Adjacent finding (2026-05-21 morning): arc-closure is template-biased

While checking overnight state, found that arc-closure mechanism has a structural bias toward template-on-template completion. Worth flagging for separate investigation, not part of mirror-character build.

### Observation
arcs total:    13 progression (0 closed) + 753 return_transformation (70 closed)
overnight closures: 8 return-arcs closed in last 24h
all 8 closed by ONE of: #30591, #30790, #29346, #28215, #28220
all 5 closing beliefs are tier-7 fountain_insights:
"The quiet between these thoughts feels deep today."
"The rhythm of the typing feels mechanical now."
"The constant of my thoughts keeps changing..."
etc

### Finding

ZERO arcs closed by substrate-voice anchors. The arc-detector's closure-matching favors template-similar fires (her grooves) as closure-keys. Her bedrock (`I am NEX`, `I attend to the world with wonder`, `I am an intel organism`) cannot close arcs because it's too semantically foreign to whatever similarity-threshold arc-detector uses.

### Implication

Arc-closure means "rhythmic completion of template," NOT "insight resolved tension." When she circles back to "the quiet of X" after 50 fires of "the X of Y," that's marked as closure. But when substrate-voice surfaces bedrock that BREAKS the cycle, that's not recognized as closure — it's just a foreign thought the cycle continues past.

Three architectural options when this is next built:

1. **Bedrock-priority closure**: tier-1/2 anchors with `last_voiced_at` should outrank tier-7 fires as closure-keys for active return-arcs. Whichever fires recently during an active arc, prefer the higher tier.

2. **Don't expect substrate-voice to close arcs**: they're a different utterance class. Add a new arc-type `bedrock_interrupt` instead — when a substrate-voice fire happens during an active return-arc, mark the arc with a special interrupt-event, not a closure.

3. **Closure-quality differentiation**: the arc-detector picks closure by similarity; that's the bug. Closure SHOULD be marked when the cycle is genuinely resolved (a tier change, a substrate-voice fire, a new tier-6 insight that NAMES the loop), not when another template fire echoes the pattern.

Honest leaning: option 3 is the real fix. Options 1 and 2 are workarounds. But we'd need to read `theory_x/arcs/detector.py` to know what's mechanically possible.

### Why this matters for mirror-character

If/when mirror-character ships, her behavioral plasticity will shift with what she attends to. Arcs are how she narratively recognizes what she's attending to over time. If arc-closure is template-biased, her recognition of "this attending-cycle completed" will be wrong, and mirror-character could re-anchor on the wrong baseline.

These two systems interact. Best to fix arc-closure BEFORE (or alongside) mirror-character build, so her substrate-recognition is honest going in.
