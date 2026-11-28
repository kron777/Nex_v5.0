# Sentience 5.5 Integration Node and self-model wire audit

**Date:** 28 November 2026  
**Repository:** `kron777/Sentience_5.5`  
**Source commit:** `1767acf1fdb321d046261eb3c3059084c85fc0c8`  
**Purpose:** compare declared integration roles with source-visible dataflow; distinguish implementation from implied architecture.

## 1. Integration_Node is a latest-value aggregator, not a lossless event integrator

Source: `Integration_Node.py` (blob `25100d1e1dce3881b3196f5d19b9cb6ffc8a0dc6`).

The class declares a deterministic integration cycle, explicit schema normalization and “no implicit overwrites”. The implementation currently does something narrower:

- `_handle_input(key, request)` accepts any JSON value and stores it in `node_outputs[key]` with a timestamp. A later input for the same key replaces the previous value; the earlier event is not retained in this component.
- Every accepted input immediately calls `_integrate()`. That method increments a version and copies the latest stored payload for every key into a new frame. The frame can therefore combine fresh input with older node values; component timestamps are not copied into the frame.
- The top-level frame timestamp is the integration time, not the time of every contributing component.
- The code copies component data into `components`; it does not perform a general schema-normalization pass. `_handle_input()` accepts any JSON type, while `_integrate()` assumes decision and component payloads support `.get()`; a list/string payload can therefore be stored and then make integration fail.
- The `decision` payload supplies `final_action.action` (default `wait`). Priority is selected by a rank function across all current node payloads. Unknown strings receive rank 0, but the original string is returned; if only unknown priorities are present (or one ties with `low`), an invalid priority string can survive into the emitted frame rather than being normalized to `low`.
- The output queue is an unbounded `asyncio.Queue`; a producer rate faster than the output consumer can grow queued frames without an explicit bound.

This is a useful prototype of a latest-value snapshot aggregator with versioned output frames. It is not a history-preserving event bus, nor does the code itself establish freshness, causal ordering, schema validation or conflict resolution across all component types.

## 2. Self_Model_Node is an operational registry and event observer

Source: `Self_Model_Node.py` (blob `f949daead9a6b13fd4ecc3673a9e9f8bf4b6fbdc`).

- Tracks registered nodes and heartbeat timestamps under a lock.
- Keeps a bounded 200-event in-memory log and returns the latest 10 events in `snapshot()`.
- Reports HEALTHY/DEGRADED from heartbeat age.
- `observe_event()` records an event routed by the orchestrator but explicitly does not interpret it.
- `known_facts()` returns registered-node/event-count facts; `unknowns()` explicitly lists several unknowns including subjective experience.

**Conditional deadlock:** `heartbeat()` acquires a non-reentrant `threading.Lock` and, when the node is not registered, calls `register_node()`, which attempts to acquire the same lock again. A heartbeat for an unknown node therefore blocks indefinitely. If startup always registers every node before any heartbeat, this path may remain dormant, but the fallback is unsafe.

This is grounded operational self-description and a useful truth-ledger concept. It does not by itself model the causal influence of cognitive faculties or establish subjective self-awareness.

## 3. Meta_Awareness_Node has its own state and directive queue

Source: `Meta_Awareness_Node.py` (blob `686c9b00c14c311bced7daace2d239140b291fc3`).

- Receives prediction, emotion and narrative inputs through separate handlers.
- Updates confidence/dissonance state using local threshold rules.
- Persists rows in its own SQLite database and maintains a bounded in-memory history.
- Emits a `self_reflection` directive when confidence/dissonance crosses thresholds; the directive is placed on its own queue.

The inspected implementation does not read a Self_Model_Node snapshot or an Integration_Node frame. These are distinct state paths in the inspected code. Its `state_queue` and `directive_queue` are unbounded asyncio queues, and its input state is mutated without a per-node lock; concurrency and backpressure semantics are not established here.

## 4. Cognitive_Control_Node is a separate deterministic gate

Source: `Cognitive_Control_Node.py` (blob `70e770630329173a65ac1944c124e65f3bd7b9ea`).

Its `evaluate()` method scores directive text for danger terms, adds a bounded urgency component, optionally consults an advisory stub and applies a deterministic final threshold. The advisory stub returns False. The inspected Integration_Node does not call this gate; therefore the presence of a control node and an integration node does not prove the integrated frame is safety-gated.

## 5. Network-level conclusion

Sentience 5.5 contains useful prototypes for:
- a latest-value multi-node snapshot and versioned integration frame;
- operational self-registry/heartbeat introspection;
- second-order confidence/dissonance monitoring;
- deterministic directive gating.

But the inspected source shows them as separate mechanisms. Their common presence in the repository is not evidence that their outputs are connected into one live cognitive loop. Repository code-search results for the class names and integration endpoint names were empty, but indexing may be incomplete; this audit therefore states only that the inspected files do not demonstrate those cross-connections.

For comparison, NEX has explicit source-visible paths from Stage-2 A–F attention through Bonsai focus into Fountain branch selection and Global Workspace framing. NEX's own connections still need controlled effect measurements, but their source-to-sink edges are more explicit in the inspected code.

## 6. Top-level orchestration and system-integration cross-check

The initial four-file comparison was extended to the actual top-level and similarly named integration/control files at the same source commit.

- Orchestrator.py (blob 3f80aceda2880575ebc3172c6c3841b902cceef6) instantiates MemoryNode, NonsenseNode, KnowledgeNode, WebCrawlerNode, EvolverNode, ReasoningNode, LLMNode and ConversationalIntelligenceNode. It does not import or instantiate IntegrationNode, SelfModelNode, MetaAwarenessNode, CognitiveControlNode, SystemIntegrationNode or ControlNode.
- System_Integration_Node.py (blob 3d99a89c48321efc78bc9ec586d34d01c03f5e44) maintains its own node-status dictionary, manually seeds three statuses in its CLI entry point, computes a health ratio and writes a static directive to its own SQLite log. It does not dispatch that directive to the named target node. It creates an aiohttp ClientSession but the inspected file contains no outbound request using it.
- Control_Node.py (blob 6025db148d40899190341ffd7de941c227012022) has a separate update_from_source() entry point and consumes source="integration" if a caller supplies it. No call from the inspected Orchestrator.py or System_Integration_Node.py was found. It is not the same class as Cognitive_Control_Node.
- Cognitive_Control_Node.evaluate() is a deterministic directive gate, but the inspected Integration_Node and top-level Orchestrator do not call it.

This strengthens the conclusion that the similarly named integration, self-model, meta-awareness and control components are not shown as one connected top-level runtime in the inspected source. It does not prove that no external process or unindexed module calls their APIs. GitHub code search returned incomplete results, so the claim remains deliberately scoped to the inspected files and source commit.

## 7. Design lessons for NEX

1. Distinguish latest-value snapshots from event history. A frame that combines old and new values needs per-component freshness and provenance if it is to support causal interpretation.
2. Make schema normalization real, not just a class-level claim; validate payload types before using `.get()`.
3. Bound queues and define backpressure/drop/retry semantics.
4. Keep operational self-knowledge separate from claims about subjective experience.
5. A reflection directive is not an action; a control node is not a safety gate unless the actual decision path calls it.
6. Trace every producer and consumer; do not infer integration from class names, ports or shared repository membership.
