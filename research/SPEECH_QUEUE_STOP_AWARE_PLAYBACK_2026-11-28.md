# Speech queue shutdown and active playback — 28 November 2026

**Base:** main at 55fd635bd535d15ece3e3878bf1e71621f56fa7c.  
**Scope:** cooperative speech-queue shutdown, interrupt active sounddevice playback, and finalize a queue row if shutdown interrupts synthesis/playback. No voice choice, speech policy, quiet-hours setting, queue ordering, synthesis model or retry policy changed.

## 1. Source evidence

- SpeechQueueConsumer is a managed AppState producer and is enabled by default through SpeechConfig unless explicitly disabled.
- The worker's idle/paused/quiet-hours branches used time.sleep(), so stop could not wake those waits.
- stop() previously only set the Event. An active Player.play() uses sounddevice blocking playback, and Player exposed no stop method.
- _speak_one() marked a row speaking, synchronously synthesized audio, played it, then marked it spoken. If shutdown arrived during synthesis or playback, the active operation continued and the row could be marked spoken even if playback was interrupted by process termination.
- Kokoro synthesis itself is synchronous and has no cancellation API in this worker.

## 2. Bounded correction

- Add Player.stop() using sounddevice.stop(), with safe handling when no stream/device is available.
- SpeechQueueConsumer.stop() sets the Event and requests immediate player stop.
- Replace paused/quiet-hours/empty/error polling sleeps with Event.wait(), so stop wakes the worker immediately.
- Check stop before starting a queue item, before marking it speaking, before synthesis, after synthesis, after playback and before marking it spoken.
- If shutdown arrives during synthesis, allow the synchronous synthesis call to return, skip playback and mark the in-flight row skipped.
- If shutdown arrives during playback, stop the audio stream and mark the row skipped, including when the player raises during interruption.
- Leave rows pending if stop is observed before the item begins; they remain available for the next startup.
- Add deterministic tests for stop during synthesis, stop during playback and waking a paused polling loop.

## 3. Boundaries and residuals

- Kokoro synthesis cannot be forcibly cancelled by the current backend interface. If it blocks longer than the producer join budget, the worker can still outlive the join; when it returns, it will skip playback and finalize the queue row as skipped.
- Player.stop() stops the active sounddevice stream; it does not cancel synthesis.
- A queue-status update already started may complete after stop. Marking an interrupted in-flight row skipped is intentional finalization, not new speech work.
- This does not change AppState join budgets or host service-manager timeouts.

## 4. Validation

Exact-head full-suite CI and baseline verification are required before merge. Tests use deterministic Events and mocked synthesis/playback; no audio device or Kokoro model is required.
