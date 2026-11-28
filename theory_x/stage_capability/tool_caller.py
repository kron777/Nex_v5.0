"""Tool Caller — selects a bounded capability from a human query.

The current arithmetic route deliberately accepts only an explicit numeric
expression. A natural-language sentence is never treated as Python source.
"""
from __future__ import annotations

import ast
import re
from typing import Optional

from .tools import ToolRegistry, ToolResult, _extract_url_from_query

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
    r"\b(calculate|compute|what is \d|what's \d|math|formula|result of|evaluate)\b",
    re.I,
)
_BELIEF_PATTERNS = re.compile(
    r"\b(what do i believe|my beliefs about|what does nex think|what have i learned)\b",
    re.I,
)
_SUPPORTED_COIN_PATTERN = re.compile(
    r"\b(btc|bitcoin|eth|ethereum|sol|solana)\b",
    re.I,
)
_MATH_PREFIX = re.compile(
    r"^\s*(?:please\s+)?(?:calculate|compute|evaluate|what\s+is|what's|result\s+of)\s+",
    re.I,
)
_MATH_CHARS = re.compile(r"^[0-9\s.+\-*/()%]+$")
MAX_MATH_EXPRESSION_CHARS = 990  # leaves room for print(...) under the registry's 1000-char cap
MAX_MATH_AST_NODES = 61  # leaves room for the print wrapper under the registry's 64-node cap


def _extract_math_expression(query: str) -> Optional[str]:
    """Extract only a numeric expression from a recognised sentence prefix."""
    match = _MATH_PREFIX.match(query)
    if not match:
        return None
    expression = query[match.end():].strip().rstrip("?.!").strip()
    if (
        not expression
        or len(expression) > MAX_MATH_EXPRESSION_CHARS
        or not _MATH_CHARS.fullmatch(expression)
    ):
        return None
    if not re.search(r"[+*/%]|-(?=\s*\d)|(?<=\d)-", expression):
        return None
    try:
        tree = ast.parse(expression, mode="eval")
        if sum(1 for _ in ast.walk(tree)) > MAX_MATH_AST_NODES:
            return None
    except (SyntaxError, ValueError, TypeError, RecursionError, MemoryError):
        return None
    return expression


class ToolCaller:
    def __init__(self, registry: ToolRegistry) -> None:
        self._registry = registry

    def should_use_tool(self, query: str, beliefs: list) -> Optional[str]:
        """Select only capabilities with a concrete, supported input target.

        web_fetch is an HTTP fetcher, not a general search provider. Do not
        select it for generic current/factual questions that contain no URL or
        supported CoinGecko symbol; the registry cannot satisfy those queries.
        """
        q = query.lower()

        if _MATH_PATTERNS.search(q):
            return "python_exec" if _extract_math_expression(query) else None

        if _BELIEF_PATTERNS.search(q):
            return "beliefs_query"

        if _extract_url_from_query(query):
            return "web_fetch"

        if (
            _SUPPORTED_COIN_PATTERN.search(q)
            and (_PRICE_PATTERNS.search(q) or _CURRENT_PATTERNS.search(q))
        ):
            return "web_fetch"

        return None

    def build_tool_kwargs(self, query: str, tool_name: str) -> dict:
        """Build typed tool inputs; never pass a sentence as executable source."""
        if tool_name == "web_fetch":
            return {"query": query}
        if tool_name == "python_exec":
            expression = _extract_math_expression(query)
            return {"code": f"print({expression})"} if expression else {"code": ""}
        if tool_name == "beliefs_query":
            return {"query": query}
        return {"query": query}

    def build_tool_prompt(self, query: str, tool_result: ToolResult) -> str:
        """Wrap successful tool output for injection into the voice system prompt."""
        return (
            f"Tool used: {tool_result.tool_name}\n"
            f"Result: {tool_result.output}\n"
            "Answer the question using this information. Be direct."
        )
