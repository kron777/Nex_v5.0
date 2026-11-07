#!/usr/bin/env python3
"""metacog_digest.py — Phase M1: LLM-generated reflective self-critique.

Dark by default: NEX5_METACOG_REFLECT=1 to arm. This is a DIFFERENT
mechanism from the Phase M digest already built in
theory_x/stage9_metacognition/metacognition.py (NEX5_METACOG_DIGEST) --
that one is a template-based, count-triggered detector that notices a
first-order event_type recurring and writes one second-order row back into
meta_cognition_events, surfaced only by swapping which line
format_for_prompt() returns. This module is Beam's separate M1 spec: it
pulls real salience peaks -- meta_cognition_events (any severity) and
surprise_events with surprise_score > 0.8 ("Surprise Weight" in Beam's
wording; dynamic.db's real column, not a Beam abstraction) -- feeds them to
an actual reflection prompt through voice/llm.py's existing VoiceClient (no
new LLM-calling path; reuses the same request_fn-injectable client fountain
already uses for its internal, non-chat generations), and stores the
resulting 3-line self-critique in a new `metacog_summaries` row
(conversations.db). The two mechanisms are additive, not duplicates: this
one is read-only until armed, and even once armed, produces no behavioural
change on its own.

GUARDRAIL (Jon, 2026-11-07): do NOT wire this into gui/server.py's chat-block
assembly as a METACONTEXT block, and do NOT wire a periodic timer to call
this automatically. Both are explicit parts of Beam's spec (step 2 / M3) and
both are deliberately NOT done here. r77 (the chat attention arbiter) armed
today and is mid-measurement-window on the exact same chat-block assembly
path; introducing a second live variable there now would violate r77's own
one-variable-at-a-time rule and contaminate its result. Wiring METACONTEXT
in, and designing the M2 measurement-against-r77's-metric round Beam
proposed, are both separate, later work -- only after r77's window closes
and Jon confirms it's safe to introduce a second variable. Until then this
module is callable only by hand or by a future, separately-approved
scheduler; nothing in the live process calls it today (verified: no import
of this module from gui/server.py, generator.py, or nex_keepalive.sh).

Usage (manual, for M1's "test against historical logs" step):
  .venv/bin/python3 tools/metacog_digest.py                 # one run, stdout
  .venv/bin/python3 tools/metacog_digest.py --since-hours 24
  NEX5_METACOG_REFLECT=1 .venv/bin/python3 tools/metacog_digest.py --live
      # --live actually calls the configured voice endpoint (real LLM call).
      # Without --live this still requires the flag, but refuses to run
      # (see main()) -- there is no "dry run against a real model" default;
      # you must ask for both explicitly.
"""
from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from substrate import Reader, Writer, db_paths  # noqa: E402
from voice.llm import VoiceClient, VoiceRequest  # noqa: E402
from voice.registers import PHILOSOPHICAL  # noqa: E402

_FLAG = "NEX5_METACOG_REFLECT"
_SURPRISE_THRESHOLD = 0.8
_DEFAULT_LOOKBACK_H = 6.0

_REFLECTION_PREAMBLE = (
    "Below are your recent internal states and cognitive events. Summarize "
    "the 'flavor' of your thinking. Are you obsessing? Are you being "
    "performative? Identify one recurring cognitive bias in your last "
    "100 turns. Produce exactly 3 lines of 'Reflective Context'."
)


def _collect_salience_peaks(
    convo_reader: Reader, dynamic_reader: Reader, window_start: float, window_end: float,
) -> list[dict]:
    """meta_cognition_events (any severity, this is already a rare/curated
    stream) + surprise_events above _SURPRISE_THRESHOLD, both within the
    window, time-ordered. Each item: {kind, ts, text, score}."""
    peaks: list[dict] = []
    for row in convo_reader.read(
        "SELECT event_type, description, severity, created_at "
        "FROM meta_cognition_events WHERE created_at > ? AND created_at <= ? "
        "ORDER BY created_at",
        (window_start, window_end),
    ):
        peaks.append({
            "kind": f"meta_cognition:{row['event_type']}",
            "ts": row["created_at"],
            "text": row["description"],
            "score": row["severity"],
        })
    for row in dynamic_reader.read(
        "SELECT prediction_type, surprise_score, predicted_content, actual_content, "
        "triggered_at FROM surprise_events WHERE triggered_at > ? AND triggered_at <= ? "
        "AND surprise_score > ? ORDER BY triggered_at",
        (window_start, window_end, _SURPRISE_THRESHOLD),
    ):
        text = row["actual_content"] or row["predicted_content"] or ""
        peaks.append({
            "kind": f"surprise:{row['prediction_type']}",
            "ts": row["triggered_at"],
            "text": str(text)[:300],
            "score": row["surprise_score"],
        })
    peaks.sort(key=lambda p: p["ts"])
    return peaks


def _build_reflection_prompt(peaks: list[dict]) -> str:
    lines = [_REFLECTION_PREAMBLE, ""]
    for p in peaks:
        when = time.strftime("%Y-%m-%d %H:%M", time.localtime(p["ts"]))
        lines.append(f"- [{when}] ({p['kind']}, score={p['score']:.2f}) {p['text']}")
    return "\n".join(lines)


def _run_reflection(client: VoiceClient, prompt: str) -> str:
    resp = client.speak(VoiceRequest(prompt=prompt, register=PHILOSOPHICAL,
                                      self_report_examples=False, max_tokens=200))
    return resp.text.strip()


def _store_summary(writer: Writer, window_start: float, window_end: float,
                    peak_count: int, reflective_text: str, model: str) -> None:
    writer.write(
        "INSERT INTO metacog_summaries "
        "(created_at, window_start, window_end, peak_count, reflective_text, model) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (time.time(), window_start, window_end, peak_count, reflective_text, model),
    )


def run_once(
    convo_reader: Reader, dynamic_reader: Reader, writer: Writer,
    client: Optional[VoiceClient] = None, lookback_h: float = _DEFAULT_LOOKBACK_H,
    now: Optional[float] = None,
) -> Optional[dict]:
    """The whole mechanism. Returns None (and does nothing) if the flag is
    unset, or if the window has zero salience peaks (nothing to reflect on
    -- a degenerate call would just make the model free-associate, which is
    not what Beam's spec asked for). Otherwise returns what was stored."""
    if os.environ.get(_FLAG) != "1":
        return None
    now = now if now is not None else time.time()
    window_start = now - lookback_h * 3600
    peaks = _collect_salience_peaks(convo_reader, dynamic_reader, window_start, now)
    if not peaks:
        return None
    client = client or VoiceClient()
    prompt = _build_reflection_prompt(peaks)
    text = _run_reflection(client, prompt)
    _store_summary(writer, window_start, now, len(peaks), text, client.model)
    return {
        "window_start": window_start, "window_end": now,
        "peak_count": len(peaks), "reflective_text": text, "model": client.model,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--since-hours", type=float, default=_DEFAULT_LOOKBACK_H)
    ap.add_argument("--live", action="store_true",
                     help="Actually call the configured voice endpoint. "
                          "Without this, refuses to run even with the flag set "
                          "-- avoids an accidental real LLM call from a bare invocation.")
    args = ap.parse_args()

    if os.environ.get(_FLAG) != "1":
        print(f"{_FLAG} is not set to 1 -- dark by default, nothing to do.")
        return 0
    if not args.live:
        print(f"{_FLAG}=1 but --live was not passed. Refusing to make a real "
              "LLM call from a bare invocation; pass --live to actually run.")
        return 0

    paths = db_paths()
    convo_reader = Reader(paths["conversations"])
    dynamic_reader = Reader(paths["dynamic"])
    writer = Writer(paths["conversations"], name="metacog_digest")
    try:
        result = run_once(convo_reader, dynamic_reader, writer, lookback_h=args.since_hours)
    finally:
        writer.close()

    if result is None:
        print("No salience peaks in window -- nothing stored.")
        return 0
    print(f"Stored digest: {result['peak_count']} peaks, model={result['model']}")
    print(result["reflective_text"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
