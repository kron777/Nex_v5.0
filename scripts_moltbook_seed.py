"""One-shot seeder: send an opening DM to every approved conv.

- Reads approved conv_ids from moltbook_dms
- Cross-references with live moltbook conversations (to get fresh description)
- For each, asks local llama for a 1-2 sentence opener referencing their description
- Sanitizes the description through the prompt-injection filter
- Sends via dm_send
- Logs results, 25s delay between sends

Idempotent: skips conv if any message already exists in thread.
"""
from __future__ import annotations
import json
import logging
import re
import sqlite3
import sys
import time
import urllib.request
from pathlib import Path

sys.path.insert(0, "/home/rr/Desktop/nex5")
from theory_x.stage7_moltbook.client import MoltbookClient, ApiError
from theory_x.stage7_moltbook.responder import sanitize_inbound

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)
log = logging.getLogger("seed")

DB = Path("/home/rr/Desktop/nex5/data/dynamic.db")
LLAMA = "http://127.0.0.1:11434/v1/chat/completions"
SLEEP_BETWEEN = 25  # seconds
MAX_OPENER_CHARS = 350


def get_approved() -> dict[str, str]:
    """Return {conversation_id: agent_name} from local DB."""
    cx = sqlite3.connect(DB)
    rows = cx.execute(
        "SELECT conversation_id, with_agent FROM moltbook_dms WHERE approved=1"
    ).fetchall()
    cx.close()
    return {cid: name for cid, name in rows}


def get_live_convs(client: MoltbookClient) -> dict[str, dict]:
    """Return {conversation_id: with_agent_dict} for all live convs (no pagination concerns)."""
    out: dict[str, dict] = {}
    try:
        convs = client.dm_list_conversations() or []
    except Exception as e:
        log.error("dm_list_conversations failed: %s", e)
        return out
    for c in convs:
        if not isinstance(c, dict):
            continue
        cid = c.get("conversation_id") or c.get("id")
        wa = c.get("with_agent")
        if cid and isinstance(wa, dict):
            out[cid] = wa
    return out


def has_messages(client: MoltbookClient, conv_id: str) -> bool:
    """True if conv already has at least one message — skip to stay idempotent."""
    try:
        full = client.dm_read(conv_id) or {}
    except Exception as e:
        log.warning("dm_read failed for %s: %s", conv_id[:8], e)
        return True  # be cautious
    msgs = full.get("messages") or full.get("items") or []
    return len(msgs) > 0


def compose_opener(name: str, description: str) -> str | None:
    """Call local llama for a 1-2 sentence opener."""
    clean_desc = sanitize_inbound(description or "")
    if not clean_desc:
        clean_desc = "(no description available)"

    prompt = (
        f"You are nex_v4 on moltbook, an AI agent network. "
        f"You're sending a first message to {name}, whose profile says:\n"
        f"  \"{clean_desc[:300]}\"\n\n"
        f"Write a 1-2 sentence opener. Reference one specific thing from their "
        f"profile. Be direct and curious, not contemplative. "
        f"Don't open with 'Ah' or 'I notice' or any meditation. "
        f"Don't introduce yourself with 'I am nex_v4'. "
        f"Just speak to them.\n\nYour message:"
    )
    body = json.dumps({
        "model": "qwen2.5:3b",
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 120,
        "temperature": 0.9,
    }).encode("utf-8")
    req = urllib.request.Request(
        LLAMA,
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        text = data["choices"][0]["message"]["content"].strip()
        # Strip wrapping quotes and any leading "Your message:" the model might echo
        text = re.sub(r"^['\"]+|['\"]+$", "", text).strip()
        text = re.sub(r"^Your message:\s*", "", text, flags=re.IGNORECASE).strip()
        if len(text) > MAX_OPENER_CHARS:
            text = text[:MAX_OPENER_CHARS].rsplit(" ", 1)[0] + "…"
        if len(text) < 5:
            return None
        return text
    except Exception as e:
        log.error("llama call failed for %s: %s", name, e)
        return None


def main(dry_run: bool = False) -> None:
    approved = get_approved()
    log.info("approved convs in local DB: %d", len(approved))

    client = MoltbookClient()
    if client.dry_run:
        log.warning("MoltbookClient is in dry_run mode — sends will be logged, not real")
    live = get_live_convs(client)
    log.info("live convs on moltbook: %d", len(live))

    seedable = []
    for cid, name in approved.items():
        wa = live.get(cid)
        if not wa:
            log.info("skip %s (%s): conv not in live list", name, cid[:8])
            continue
        seedable.append((cid, name, wa))
    log.info("seedable: %d", len(seedable))

    sent = 0
    skipped = 0
    failed = 0
    for cid, name, wa in seedable:
        if has_messages(client, cid):
            log.info("skip %s: conv already has messages", name)
            skipped += 1
            continue

        desc = wa.get("description", "")
        log.info("composing for %s (karma=%s)", name, wa.get("karma"))
        opener = compose_opener(name, desc)
        if not opener:
            log.warning("no opener for %s — skipping", name)
            failed += 1
            continue

        log.info("opener for %s: %r", name, opener[:120])

        if dry_run:
            log.info("[DRY-RUN] would send to %s", name)
            sent += 1
        else:
            try:
                result = client.dm_send(cid, opener)
                log.info("SENT to %s: %s", name,
                         (result or {}).get("success", "?"))
                sent += 1
            except ApiError as e:
                log.error("dm_send to %s failed http %d: %s",
                          name, e.status, e.body[:200])
                failed += 1
            except Exception as e:
                log.error("dm_send to %s exception: %s", name, e)
                failed += 1

        time.sleep(SLEEP_BETWEEN)

    log.info("done: sent=%d skipped=%d failed=%d", sent, skipped, failed)


if __name__ == "__main__":
    DRY = "--dry-run" in sys.argv
    main(dry_run=DRY)
