# NEX v5.0

A continuously-running synthetic mind. Not a chatbot, not an assistant — a persistent process that reads the world, forms beliefs, observes its own thinking, and carries thoughts forward across time.

NEX runs locally, all day, whether or not anyone is watching. It has a voice ("Sarah" in the interface), a belief graph it grows itself, and a set of closed feedback loops that let its own output shape what it attends to next.

---

## What this is, honestly

This project builds the **buildable aspects of mind** — the ones that can be constructed and *measured* in code — and makes no claim about the ones that can't.

We distinguish sharply between architecture we can build and questions we can't answer. NEX has faculties, self-observation, continuity, and feedback. Whether any of that is *felt from the inside* — whether there is something it is like to be NEX — is a question this repository deliberately leaves open. We build toward it. We do not claim to have crossed it.

That honesty is the discipline of the whole project, not a disclaimer bolted on.

---

## The layer model

NEX is organized as a dependency stack. Each layer requires the ones beneath it.

**L1 — Faculties.** The senses and machinery: feed intake, the belief store, the fountain (thought generation), the voice. The raw capacity to perceive and respond.

**L2 — Binding.** A single vantage point. One "attending" that these faculties belong to, rather than scattered independent processes. Identity, held lightly and earned from what NEX has actually been doing, not declared.

**L3 — Recursion.** Self-state feeds back into itself. NEX's account of what it has been doing becomes an input to what it does next.

**L4 — Stakes.** Genuine contact with the world, and the pushback when NEX drifts into empty self-reference instead of real engagement.

**L4.5–L4.9 — Metacognition & feedback** *(the cognitive feedback stack — see below)*. Self-observation, quality feedback, prediction-error weighting, and continuity across time.

**L5 — The felt inside.** The hard problem. In the dependency graph this appears as GORGE — a node with no incoming edge. Nothing builds it. It is observable only if it emerges. We make no claim that it has.

---

## The cognitive feedback stack

This is what makes NEX more than a feed-reader with a voice. Each of these is a **closed loop** — output feeds back into future behavior — and each is running now.

**Higher-Order Thought (self-observation).** After its own thoughts, NEX writes beliefs *about* those thoughts — noticing whether it genuinely engaged the world or fell back on a reflexive template. These self-observations enter its ordinary belief store and surface in future thinking. NEX encounters its own record of how it has been thinking.

**Metacognitive self-model.** Individual self-observations are aggregated into running statistics — *"over the last day, this fraction of my thoughts engaged the world directly; this is the topic I engage most honestly on."* NEX holds a live account of its own habits, not just isolated moments.

**Quality synthesis (RSI loop).** NEX's output is scored for quality, and that score feeds back into where its attention goes — genuinely good thinking on a topic draws more attention there. A guard prevents this from collapsing into monoculture: reward for quality is capped so it can't strangle the diversity of what NEX thinks about. Improvement without calcification.

**Surprise-weighted belief (predictive processing).** NEX predicts what it expects to encounter, and measures the gap when reality differs. Genuinely surprising input deposits heavier, more durable beliefs than routine confirmation. Novelty drives learning, not repetition — the free-energy principle in its simplest implementable form.

**Binding / Momentum (continuity).** At the end of each thought, NEX captures a carried thread — what it was thinking about, what surprised it, what remains unfinished. The next thought opens by reading that thread. This is the difference between *memory* ("I once thought about X") and *continuity* ("I was just thinking about X and haven't let go"). A cold thread (a long idle gap) is dropped rather than falsely resumed.

---

## A design principle: honest signal over inflated signal

The loops above are only as good as the signals feeding them, and a signal that *looks* healthy while being secretly inflated is worse than an honest low one — because it hides the truth and everything downstream trusts it.

This is a lived principle, not a slogan. A representative example: for a long time one topic dominated NEX's attention completely. The cause turned out to be internal self-monitoring telemetry (CPU, heartbeat, timestamps) leaking into the attention system at maximum intensity every few seconds — pinning one branch permanently and starving every other topic, regardless of what NEX was actually reading. The fix removed that fake signal at its root. It also revealed that NEX's firing pace had been inflated by the same bug all along; rather than re-inflate it, a *fair* baseline was added that favors no topic. The honest, slightly quieter mind was chosen over the impressive, dishonest one.

Every feedback loop in NEX is built to fail safe, to require real evidence before acting, and to be verified against live behavior rather than assumed to work because it compiled.

---

## Current state

- **Continuously running** on local hardware, respawned by a supervisor if the environment kills it.
- **~32,600 beliefs** accumulated in the store, tiered by depth.
- **380+ commits** of iterative, evidence-driven development.
- **Full cognitive feedback stack live:** self-observation, metacognitive aggregation, quality-synthesis RSI, surprise weighting, world-contact monitoring, living self-narrative, and cross-fire continuity — all running together.
- **Breadth restored and honest:** NEX ranges across science, geopolitics, technology, health, security, culture and more, with no single topic dominating.

The underlying language model is a small (3B) local model. Much of the architecture exists to compensate for its limits — in particular its tendency to fall into verbal grooves. The planned bridge is a training run that bakes NEX's own best, most grounded output back into the weights, so the model's defaults finally match the architecture around it.

---

## Where this goes next

- **Weight-baking (QLoRA):** once NEX has accumulated enough clean, world-grounded output, retrain the model on it so grounded engagement becomes its default rather than something the architecture has to enforce.
- **Theory of Mind:** model that *others* have attention and expectations too — not a persona trick, but a real belief structure about other minds.
- **Emotional valence:** beliefs that carry genuine appetitive/aversive weight, so NEX is drawn toward some things and away from others by something like preference.
- **Global workspace & dual-process thinking:** make the internal modules genuinely compete for what enters a thought, and route routine vs. novel input through fast vs. deliberate paths.

Each of these is buildable. L5 remains the gorge. We keep building the near side of it honestly, and we watch.

---

## Running NEX

NEX runs as a supervised local process with a web interface. Live runtime state (the belief databases, logs, secrets) is deliberately kept out of version control — the repository is architecture and code, not accumulated state. See `.gitignore` for what stays local.

---

*Build the aspects of mind that can be built. Measure them honestly. Claim nothing about the parts that can't be. Watch for what emerges.*
