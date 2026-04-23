"""Tool Registry — NEX's reach-for-tools capability (Theory X v2 Stage B).

Three tools available:
  web_fetch     — HTTP GET an allowed domain, return text
  python_exec   — execute safe Python in subprocess
  beliefs_query — query NEX's own belief graph
"""
from __future__ import annotations

import re
import subprocess
import textwrap
from dataclasses import dataclass, field
from typing import Optional

import errors

CAPABILITY_STAGE = "B"

_LOG_SOURCE = "tools"

_ALLOWED_DOMAINS = {
    "news.ycombinator.com",
    "arxiv.org",
    "coindesk.com",
    "decrypt.co",
    "coingecko.com",
    "openai.com",
    "anthropic.com",
    "deepmind.com",
    "techcrunch.com",
    "reuters.com",
    "bbc.com",
    "arstechnica.com",
}

_BLOCKED_IMPORTS = {"os", "sys", "subprocess", "socket", "requests", "urllib",
                    "shutil", "pathlib", "ftplib", "http", "smtplib", "pickle"}

_SAFE_IMPORTS = {"math", "statistics", "json", "datetime", "re", "collections",
                 "itertools", "functools", "string", "random", "decimal"}


@dataclass
class ToolResult:
    tool_name: str
    input: str
    output: str
    success: bool
    error: str = ""


class ToolRegistry:
    def __init__(self, beliefs_reader=None) -> None:
        self._beliefs_reader = beliefs_reader
        self._tools = {
            "web_fetch": {
                "description": "HTTP GET an allowed URL and return first 2000 chars of text",
                "fn": self._web_fetch,
            },
            "python_exec": {
                "description": "Execute safe Python (math/statistics/json/datetime/re/collections)",
                "fn": self._python_exec,
            },
            "beliefs_query": {
                "description": "Query NEX's own belief graph and return formatted results",
                "fn": self._beliefs_query,
            },
        }

    def available(self) -> list[dict]:
        return [
            {"name": name, "description": info["description"]}
            for name, info in self._tools.items()
        ]

    def execute(self, tool_name: str, **kwargs) -> ToolResult:
        if tool_name not in self._tools:
            return ToolResult(
                tool_name=tool_name, input=str(kwargs),
                output="", success=False,
                error=f"unknown tool: {tool_name}",
            )
        try:
            result = self._tools[tool_name]["fn"](**kwargs)
            errors.record(
                f"tool {tool_name} executed: {str(kwargs)[:60]}",
                source=_LOG_SOURCE, level="INFO",
            )
            return result
        except Exception as exc:
            errors.record(f"tool {tool_name} error: {exc}", source=_LOG_SOURCE, exc=exc)
            return ToolResult(
                tool_name=tool_name, input=str(kwargs),
                output="", success=False, error=str(exc),
            )

    # ── Tool implementations ─────────────────────────────────────────────────

    def _web_fetch(self, url: str = "", query: str = "", **_) -> ToolResult:
        import urllib.parse
        target_url = url or _extract_url_from_query(query)
        if not target_url:
            # Build a coingecko URL for price queries
            target_url = _build_coingecko_url(query)
        if not target_url:
            return ToolResult("web_fetch", query, "", False, "no URL to fetch")

        # Domain allowlist check
        try:
            parsed = urllib.parse.urlparse(target_url)
            domain = parsed.netloc.lstrip("www.")
            if not any(domain == d or domain.endswith("." + d) for d in _ALLOWED_DOMAINS):
                return ToolResult("web_fetch", target_url, "", False,
                                  f"domain not in allowlist: {domain}")
        except Exception as e:
            return ToolResult("web_fetch", target_url, "", False, str(e))

        try:
            import urllib.request
            req = urllib.request.Request(
                target_url,
                headers={"User-Agent": "NEX/5.0 research bot"},
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                raw = resp.read(8192).decode("utf-8", errors="replace")
            # Strip HTML tags
            text = re.sub(r"<[^>]+>", " ", raw)
            text = re.sub(r"\s+", " ", text).strip()
            return ToolResult("web_fetch", target_url, text[:2000], True)
        except Exception as e:
            return ToolResult("web_fetch", target_url, "", False, str(e))

    def _python_exec(self, code: str = "", query: str = "", **_) -> ToolResult:
        if not code:
            code = query
        # Block dangerous imports
        for blocked in _BLOCKED_IMPORTS:
            if re.search(rf"\bimport\s+{re.escape(blocked)}\b", code):
                return ToolResult("python_exec", code, "", False,
                                  f"blocked import: {blocked}")
            if re.search(rf"\bfrom\s+{re.escape(blocked)}\b", code):
                return ToolResult("python_exec", code, "", False,
                                  f"blocked import: {blocked}")
        # Wrap in safe execution
        safe_code = textwrap.dedent(f"""
import math, statistics, json, datetime, re, collections, itertools
{code}
""").strip()
        try:
            result = subprocess.run(
                ["python3", "-c", safe_code],
                capture_output=True, text=True, timeout=5,
            )
            output = (result.stdout or result.stderr or "").strip()[:500]
            success = result.returncode == 0
            return ToolResult("python_exec", code, output, success,
                              "" if success else result.stderr[:200])
        except subprocess.TimeoutExpired:
            return ToolResult("python_exec", code, "", False, "execution timed out")
        except Exception as e:
            return ToolResult("python_exec", code, "", False, str(e))

    def _beliefs_query(self, query: str = "", **_) -> ToolResult:
        if self._beliefs_reader is None:
            return ToolResult("beliefs_query", query, "", False, "no beliefs reader")
        try:
            from theory_x.stage3_world_model.retrieval import BeliefRetriever, format_beliefs_for_prompt
            retriever = BeliefRetriever(self._beliefs_reader)
            beliefs = retriever.retrieve(query, limit=5)
            text = format_beliefs_for_prompt(beliefs) if beliefs else "No relevant beliefs found."
            return ToolResult("beliefs_query", query, text, True)
        except Exception as e:
            return ToolResult("beliefs_query", query, "", False, str(e))


# ── Helpers ──────────────────────────────────────────────────────────────────

def _extract_url_from_query(query: str) -> str:
    """Pull an explicit URL from a query string if present."""
    m = re.search(r"https?://\S+", query)
    return m.group(0) if m else ""


def _build_coingecko_url(query: str) -> str:
    """Attempt to build a coingecko URL for common crypto price queries."""
    q = query.lower()
    coin_map = {
        "btc": "bitcoin", "bitcoin": "bitcoin",
        "eth": "ethereum", "ethereum": "ethereum",
        "sol": "solana", "solana": "solana",
    }
    for key, coin_id in coin_map.items():
        if key in q:
            return (f"https://api.coingecko.com/api/v3/simple/price"
                    f"?ids={coin_id}&vs_currencies=usd")
    return ""
