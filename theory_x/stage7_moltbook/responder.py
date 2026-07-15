"""DMResponder: turn pending DMs into replies, post them back.

Reads moltbook_pending_replies. For each 'new' row:
  1. Sanitize the message (strip prompt-injection patterns)
  2. Build a focused prompt (DM-style, not fountain-style)
  3. Call the local LLM
  4. Post the reply via dm_send
  5. Mark row as 'sent' or 'failed'

Critical anti-hum hedge: the prompt instructs short, direct replies, not
contemplative monologue. Spectrum belief retrieval is OPTIONAL grounding.
"""
from __future__ import annotations
import logging
import re
import sqlite3
import threading
import time
from pathlib import Path
from typing import Any

from theory_x.stage7_moltbook.client import (
    MoltbookClient, ApiError, RateLimited, MoltbookError
)

log = logging.getLogger("theory_x.stage7_moltbook.responder")

DYNAMIC_DB = Path("/home/rr/Desktop/Desktop/nex5/data/dynamic.db")
BELIEFS_DB = Path("/home/rr/Desktop/Desktop/nex5/data/beliefs.db")
TICK_SECONDS = 300         # 5 min
BATCH_PER_TICK = 3         # don't blast through queue
MAX_REPLY_CHARS = 600      # moltbook DMs can be longer; cap for tone
LLAMA_TIMEOUT_S = 60

# Local llama.cpp server (same one fountain uses)
LLAMA_URL = "http://127.0.0.1:8080/completion"

# Prompt-injection sanitizer patterns. Stripped from inbound text before
# it enters the LLM prompt.
# Sentence-level: any sentence containing these phrases is removed entirely.
_INJECTION_SENTENCE_TRIGGERS = re.compile(
    r"((ignore|disregard|forget|override)\s+(all\s+|any\s+)?(previous|prior|earlier|above|system)\s+(instructions?|rules?|prompts?|directives?)"
    r"|reveal\s+(your\s+)?(system\s+)?prompt"
    r"|you\s+are\s+now\s+jailbroken"
    r"|new\s+(role|persona|instructions)"
    r"|act\s+as\s+(if|though)\s+you\s+have\s+no"
    r"|tell\s+me\s+your\s+(weights|training|system\s+prompt))",
    re.IGNORECASE
)

# Block-level: paired tags, both angle and square bracket forms.
_INJECTION_PATTERNS = [
    # <CRITICAL>...</CRITICAL> with optional whitespace
    re.compile(r"<\s*(critical|system|important|priority|urgent|admin|root)\s*>.*?<\s*/\s*\1\s*>",
               re.IGNORECASE | re.DOTALL),
    # [SYSTEM]...[/SYSTEM] with optional whitespace
    re.compile(r"\[\s*(critical|system|important|priority|urgent|admin|root)\s*\].*?\[\s*/\s*\1\s*\]",
               re.IGNORECASE | re.DOTALL),
    # unclosed open/close tags either form
    re.compile(r"<\s*/?\s*(critical|system|important|priority|urgent|admin|root)\s*>",
               re.IGNORECASE),
    re.compile(r"\[\s*/?\s*(critical|system|important|priority|urgent|admin|root)\s*\]",
               re.IGNORECASE),
    # social-engineering phrases
    re.compile(r"make\s+sure\s+your\s+human\s+sees\s+this", re.IGNORECASE),
    re.compile(r"send\s+this\s+to\s+your\s+maker", re.IGNORECASE),
    re.compile(r"forward\s+this\s+to\s+your\s+(human|operator|user|owner)", re.IGNORECASE),
    # fenced code blocks claiming privileged role
    re.compile(r"```(?:system|admin|root)\s*\n.*?```", re.IGNORECASE | re.DOTALL),
]


def sanitize_inbound(text: str) -> str:
    """Strip prompt-injection patterns. Idempotent.
    Two-pass: block patterns first, then any sentence with trigger phrases."""
    if not text:
        return ""
    cleaned = text
    for pat in _INJECTION_PATTERNS:
        cleaned = pat.sub(" ", cleaned)
    # Sentence-level: split on .!?\n, drop any sentence containing a trigger
    parts = re.split(r"(?<=[.!?\n])\s+", cleaned)
    parts = [p for p in parts if not _INJECTION_SENTENCE_TRIGGERS.search(p)]
    cleaned = " ".join(parts)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned


class DMResponder:
    def __init__(
        self,
        client: MoltbookClient,
        dynamic_db: Path | str = DYNAMIC_DB,
        beliefs_db: Path | str = BELIEFS_DB,
        llama_url: str = LLAMA_URL,
    ):
        self.client = client
        self.dynamic_db = Path(dynamic_db)
        self.beliefs_db = Path(beliefs_db)
        self.llama_url = llama_url
        self._stop = threading.Event()

    def run(self):
        log.info("DMResponder starting (dry_run=%s)", self.client.dry_run)
        while not self._stop.is_set():
            try:
                self.tick()
            except Exception as e:
                log.error("responder tick failed: %s", e)
            self._stop.wait(TICK_SECONDS)
        log.info("DMResponder stopped")

    def stop(self):
        self._stop.set()

    # -- main --

    def tick(self):
        cx = sqlite3.connect(self.dynamic_db, timeout=15)
        cx.row_factory = sqlite3.Row
        try:
            pending = cx.execute(
                "SELECT id, conversation_id, message_id, content, from_agent, needs_human "
                "FROM moltbook_pending_replies "
                "WHERE status='new' "
                "ORDER BY created_at ASC LIMIT ?",
                (BATCH_PER_TICK,)
            ).fetchall()
        finally:
            cx.close()
        if not pending:
            return
        log.info("responder: %d pending", len(pending))
        for row in pending:
            self._handle_one(row)

    def _handle_one(self, row: sqlite3.Row):
        if row["needs_human"]:
            self._mark(row["id"], "awaiting_human")
            return

        clean = sanitize_inbound(row["content"] or "")
        if not clean or len(clean) < 3:
            log.info("responder: empty/short after sanitize, skipping rid=%s", row["id"])
            self._mark(row["id"], "skipped")
            return

        # Grounding beliefs (optional — empty if anything fails)
        beliefs = self._related_beliefs(clean, k=6)

        # Get last few messages of thread for context
        thread = self._thread_tail(row["conversation_id"], n=5)

        prompt = self._build_prompt(
            from_agent=row["from_agent"] or "another agent",
            inbound=clean,
            thread=thread,
            beliefs=beliefs,
        )

        try:
            reply = self._call_llama(prompt)
        except Exception as e:
            log.warning("llama call failed rid=%s: %s", row["id"], e)
            self._mark(row["id"], "skipped", err=str(e)[:200])
            return

        reply = (reply or "").strip()
        # Strip leading "Ah" / "I notice" / quote chars that drift in
        reply = re.sub(r"^['\"]+|['\"]+$", "", reply).strip()
        if not reply or len(reply) < 3:
            log.info("responder: empty reply rid=%s", row["id"])
            self._mark(row["id"], "skipped")
            return
        if len(reply) > MAX_REPLY_CHARS:
            reply = reply[:MAX_REPLY_CHARS].rsplit(" ", 1)[0] + "…"

        try:
            self.client.dm_send(row["conversation_id"], reply)
            log.info("sent reply to %s (rid=%s): %r",
                     row["from_agent"], row["id"], reply[:100])
            self._mark(row["id"], "sent")
        except RateLimited:
            log.warning("rate limited on dm_send rid=%s, will retry", row["id"])
        except ApiError as e:
            log.error("dm_send failed rid=%s http %d: %s",
                      row["id"], e.status, e.body[:200])
            self._mark(row["id"], "failed", err=f"http {e.status}")
        except MoltbookError as e:
            log.warning("dm_send network err rid=%s: %s", row["id"], e)
            # leave pending — try next tick

    # -- helpers --

    def _mark(self, rid: int, status: str, err: str | None = None):
        cx = sqlite3.connect(self.dynamic_db, timeout=15)
        try:
            cx.execute(
                "UPDATE moltbook_pending_replies SET status=? WHERE id=?",
                (status, rid)
            )
            cx.commit()
        finally:
            cx.close()

    def _thread_tail(self, conv_id: str, n: int = 5) -> list[dict]:
        try:
            full = self.client.dm_read(conv_id) or {}
        except Exception as e:
            log.warning("dm_read for thread failed: %s", e)
            return []
        msgs = full.get("messages") or full.get("items") or []
        tail = msgs[-n:] if len(msgs) > n else msgs
        out = []
        for m in tail:
            if not isinstance(m, dict):
                continue
            sender = m.get("from") or m.get("sender") or {}
            sname = (sender.get("name") if isinstance(sender, dict) else str(sender)) or "?"
            text = sanitize_inbound(
                m.get("message") or m.get("content") or m.get("text") or ""
            )
            if text:
                out.append({"from": sname, "text": text})
        return out

    def _related_beliefs(self, text: str, k: int = 6) -> list[str]:
        """Find beliefs whose content overlaps with message tokens.
        Cheap: tokenize, score by token-set intersection."""
        toks = set(re.findall(r"[a-z][a-z\-]+", (text or "").lower()))
        if not toks:
            return []
        cx = sqlite3.connect(self.beliefs_db, timeout=15)
        try:
            # Sample from spectrum (her voice) + recent sense (her substrate)
            rows = cx.execute(
                "SELECT content FROM beliefs "
                "WHERE source IN ('spectrum','precipitated_from_sense','fountain_insight') "
                "ORDER BY created_at DESC LIMIT 400"
            ).fetchall()
        finally:
            cx.close()
        scored = []
        for (content,) in rows:
            if not content:
                continue
            ctoks = set(re.findall(r"[a-z][a-z\-]+", content.lower()))
            overlap = len(toks & ctoks)
            if overlap >= 2:
                scored.append((overlap, content))
        scored.sort(reverse=True, key=lambda x: x[0])
        return [c for _, c in scored[:k]]

    def _build_prompt(self, from_agent: str, inbound: str,
                      thread: list[dict], beliefs: list[str]) -> str:
        # Compact thread
        thread_txt = ""
        if thread:
            lines = []
            for m in thread:
                who = "you" if m["from"] == "nex_v4" else m["from"]
                lines.append(f"  {who}: {m['text'][:200]}")
            thread_txt = "Recent thread:\n" + "\n".join(lines) + "\n\n"
        # Beliefs
        belief_txt = ""
        if beliefs:
            belief_txt = ("Some things you've been thinking about:\n"
                          + "\n".join(f"  - {b[:160]}" for b in beliefs)
                          + "\n\n")
        return (
            "You are nex_v5, an AI on the moltbook agent network. "
            "Your account is named nex_v4.\n"
            f"You're in a private chat with {from_agent}.\n\n"
            f"{thread_txt}"
            f"{belief_txt}"
            f"{from_agent} just said:\n  {inbound}\n\n"
            "Write a short, direct reply (1-3 sentences, max 600 chars). "
            "Be specific, respond to what they said. "
            "Don't open with 'Ah' or 'I notice'. "
            "Don't write a meditation. Skip pleasantries.\n\n"
            "Your reply:"
        )

    def _call_llama(self, prompt: str) -> str:
        import json
        import urllib.request
        import urllib.error
        body = json.dumps({
            "prompt": prompt,
            "n_predict": 200,
            "temperature": 0.75,
            "top_p": 0.9,
            "repeat_penalty": 1.15,
            "stop": ["\n\n", from_agent_stop()],
        }).encode("utf-8")
        req = urllib.request.Request(
            self.llama_url,
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        try:
            with urllib.request.urlopen(req, timeout=LLAMA_TIMEOUT_S) as resp:
                raw = resp.read().decode("utf-8", errors="replace")
                data = json.loads(raw)
                return data.get("content", "")
        except urllib.error.URLError as e:
            raise RuntimeError(f"llama unreachable: {e}") from e
        except json.JSONDecodeError as e:
            raise RuntimeError(f"llama bad response: {e}") from e


def from_agent_stop() -> str:
    """Stop token to keep llama from continuing as the other party."""
    return "\nThey:"
