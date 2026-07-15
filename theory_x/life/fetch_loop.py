"""Fetch loop — she actually reads URLs from her feeds.

Every 30 minutes: picks one recent sense event with a URL, does an
http GET with 5s timeout, extracts the first 800 chars of body text,
asks her LLM to write a single-sentence response to what she just read.

Reverses headline-only consumption: substrate sees article titles but
never the content. This loop turns titles into actual reading.

Output: Tier-6 belief, source='fetch_loop'.
Failures (timeout, paywall, 403) are silent — try the next URL next tick.
"""
from __future__ import annotations
import json
import logging
import random
import re
import sqlite3
import threading
import time
from pathlib import Path

log = logging.getLogger("theory_x.life.fetch_loop")

BELIEFS_DB = Path("/home/rr/Desktop/Desktop/nex5/data/beliefs.db")
SENSE_DB = Path("/home/rr/Desktop/Desktop/nex5/data/sense.db")
TICK_SECONDS = 1800
RECENT_WINDOW_SECONDS = 7200
DAILY_CAP = 12
HTTP_TIMEOUT_SECONDS = 5
MAX_BODY_CHARS = 800
SOURCE = "fetch_loop"

USER_AGENT = "Mozilla/5.0 (compatible; nex5-fetch/1.0; +https://nex5.local)"


def _strip_html(html):
    if not html:
        return ""
    # Remove script/style blocks
    html = re.sub(r"<script[^>]*>.*?</script>", " ", html, flags=re.DOTALL | re.I)
    html = re.sub(r"<style[^>]*>.*?</style>", " ", html, flags=re.DOTALL | re.I)
    # Strip tags
    text = re.sub(r"<[^>]+>", " ", html)
    # Decode common entities
    text = (text.replace("&nbsp;", " ")
                .replace("&amp;", "&")
                .replace("&quot;", "\"")
                .replace("&#39;", "'")
                .replace("&lt;", "<")
                .replace("&gt;", ">"))
    # Collapse whitespace
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _pick_url():
    s_cx = sqlite3.connect(SENSE_DB, timeout=10)
    try:
        rows = s_cx.execute(
            "SELECT payload FROM sense_events "
            "WHERE stream NOT LIKE 'internal.%' "
            "  AND timestamp > ? "
            "ORDER BY RANDOM() LIMIT 30",
            (time.time() - RECENT_WINDOW_SECONDS,)
        ).fetchall()
    finally:
        s_cx.close()
    candidates = []
    for (payload,) in rows:
        try:
            d = json.loads(payload) if payload else {}
            url = d.get("url") or d.get("link")
            title = d.get("title") or ""
            if url and url.startswith("http") and len(url) < 500:
                candidates.append((url, title))
        except Exception:
            continue
    if not candidates:
        return None
    return random.choice(candidates)


def _already_fetched(cx, url):
    """Avoid re-fetching same URL within 7 days."""
    cutoff = time.time() - 7 * 86400
    row = cx.execute(
        "SELECT id FROM beliefs WHERE source=? AND content LIKE ? AND created_at > ? LIMIT 1",
        (SOURCE, "%" + url[:60] + "%", cutoff)
    ).fetchone()
    return row is not None


def _fetch_body(url):
    try:
        import urllib.request
        import urllib.error
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(req, timeout=HTTP_TIMEOUT_SECONDS) as resp:
            ctype = resp.headers.get("content-type", "")
            if "html" not in ctype.lower() and "text" not in ctype.lower():
                return None  # binary, pdf, video
            raw = resp.read(50000)  # cap raw bytes
        text = _strip_html(raw.decode("utf-8", errors="replace"))
        return text[:MAX_BODY_CHARS] if text else None
    except Exception as e:
        log.debug("fetch %s failed: %s", url[:60], type(e).__name__)
        return None


def _daily_count(cx):
    cutoff = time.time() - 86400
    row = cx.execute(
        "SELECT COUNT(*) FROM beliefs WHERE source=? AND created_at > ?",
        (SOURCE, cutoff)
    ).fetchone()
    return row[0] if row else 0


def _compose_response(voice, url, title, body):
    from voice.llm import VoiceRequest
    prompt = (
        "You just read this:\n\n"
        "Title: " + title + "\n"
        "Body excerpt: \"" + body[:600] + "\"\n\n"
        "Write ONE sentence — your actual response to what you just read. "
        "Not a summary. A reaction, a question, a thought you had while reading, "
        "or what it connects to that you already hold. First person, 10-30 words. "
        "No preamble."
    )
    try:
        req = VoiceRequest(prompt=prompt, max_tokens=80, temperature=0.85)
        resp = voice.speak(req)
        if resp and resp.text:
            return resp.text.strip()
    except Exception as e:
        log.warning("compose_response voice call failed: %s", e)
    return None


def fetch_tick(voice):
    cx = sqlite3.connect(BELIEFS_DB, timeout=15)
    try:
        if _daily_count(cx) >= DAILY_CAP:
            return {"skipped": "daily_cap"}
        pick = _pick_url()
        if not pick:
            return {"skipped": "no_url"}
        url, title = pick
        if _already_fetched(cx, url):
            return {"skipped": "duplicate_url"}
        body = _fetch_body(url)
        if not body or len(body) < 100:
            return {"skipped": "fetch_failed", "url": url[:80]}
        response = _compose_response(voice, url, title, body)
        if not response:
            return {"skipped": "voice_failed"}
        # Store with title prefix so the URL trail is visible
        content_text = response + " (read: " + title[:80] + ")"
        now = int(time.time())
        try:
            cx.execute(
                "INSERT INTO beliefs "
                "(content, tier, confidence, created_at, source, branch_id, tags) "
                "VALUES (?, 6, 0.65, ?, ?, ?, '[]')",
                (content_text, now, SOURCE, "computing")
            )
            cx.commit()
            log.info("fetch_loop: %s -> %s", url[:60], response[:80])
            return {"fetched": True, "url": url[:80], "text": response[:120]}
        except sqlite3.IntegrityError:
            return {"skipped": "duplicate_content"}
    finally:
        cx.close()


def fetch_loop(state, stop):
    log.info("fetch_loop started (tick=%ds, cap=%d/day, timeout=%ds)",
             TICK_SECONDS, DAILY_CAP, HTTP_TIMEOUT_SECONDS)
    voice = None
    while not stop.is_set():
        try:
            if voice is None:
                from voice.llm import VoiceClient
                voice = VoiceClient()
            stats = fetch_tick(voice)
            if stats.get("fetched"):
                log.info("fetch_loop: %s", stats.get("text", "")[:100])
            elif stats.get("skipped") and stats.get("skipped") != "daily_cap":
                log.debug("fetch_loop: skipped %s", stats.get("skipped"))
        except Exception as e:
            log.error("fetch_loop tick failed: %s: %s",
                      type(e).__name__, str(e)[:200])
            voice = None
        stop.wait(TICK_SECONDS)
    log.info("fetch_loop stopped")
