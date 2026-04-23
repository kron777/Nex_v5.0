"""Tool Caller — decides when NEX should reach for a tool.

Heuristic pattern matching on the query. NEX chooses; it is not forced.
"""
from __future__ import annotations

import re
from typing import Optional

from .tools import ToolRegistry, ToolResult

CAPABILITY_STAGE = "B"

_PRICE_PATTERNS = re.compile(
    r"\b(price|trading|how much|what is .+ worth|btc|eth|bitcoin|ethereum|solana|sol)\b",
    re.I,
)
_CURRENT_PATTERNS = re.compile(
    r"\b(latest|today|right now|current|live|now|just happened|this week)\b",
    re.I,
)
_MATH_PATTERNS = re.compile(
    r"\b(calculate|compute|what is \d|math|formula|result of|evaluate)\b",
    re.I,
)
_BELIEF_PATTERNS = re.compile(
    r"\b(what do i believe|my beliefs about|what does nex think|what have i learned)\b",
    re.I,
)


class ToolCaller:
    def __init__(self, registry: ToolRegistry) -> None:
        self._registry = registry

    def should_use_tool(self, query: str, beliefs: list) -> Optional[str]:
        """Return the tool name to use, or None if no tool needed.

        Order of precedence:
          1. Price / crypto query → web_fetch
          2. "Calculate / compute" → python_exec
          3. Explicit belief query → beliefs_query
          4. "Latest / current / today" → web_fetch
          5. No beliefs found + query looks factual → web_fetch
        """
        q = query.lower()

        if _PRICE_PATTERNS.search(q):
            return "web_fetch"

        if _MATH_PATTERNS.search(q):
            return "python_exec"

        if _BELIEF_PATTERNS.search(q):
            return "beliefs_query"

        if _CURRENT_PATTERNS.search(q):
            return "web_fetch"

        # No beliefs retrieved + looks factual (contains a proper noun or "what is")
        if not beliefs and re.search(r"\bwhat is\b|\bwho is\b|\bwhen did\b|\bhow does\b", q, re.I):
            return "web_fetch"

        return None

    def build_tool_kwargs(self, query: str, tool_name: str) -> dict:
        """Build the kwargs to pass to ToolRegistry.execute()."""
        if tool_name == "web_fetch":
            return {"query": query}
        if tool_name == "python_exec":
            # Try to extract code-like content from the query
            return {"query": query, "code": ""}
        if tool_name == "beliefs_query":
            return {"query": query}
        return {"query": query}

    def build_tool_prompt(self, query: str, tool_result: ToolResult) -> str:
        """Wrap tool output for injection into the voice system prompt."""
        return (
            f"Tool used: {tool_result.tool_name}\n"
            f"Result: {tool_result.output}\n"
            "Answer the question using this information. Be direct."
        )
