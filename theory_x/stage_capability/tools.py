"""Tool Registry — NEX's reach-for-tools capability (Theory X v2 Stage B).

Three tools available:
  web_fetch     — HTTP GET an allowed domain, return text
  python_exec   — evaluate a deliberately small, non-executable arithmetic language
  beliefs_query — query NEX's own belief graph

The arithmetic tool does not run Python source. It parses a tiny AST allowlist and
interprets numeric expressions in-process; natural-language input is never a
fallback source-code argument.
"""
from __future__ import annotations

import ast
import math
import operator
import re
from dataclasses import dataclass
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

_BINARY_OPERATORS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
}
_UNARY_OPERATORS = {ast.UAdd: operator.pos, ast.USub: operator.neg}
_MATH_CONSTANTS = {"pi": math.pi, "e": math.e, "tau": math.tau}
_MATH_FUNCTIONS = {
    "sqrt": math.sqrt, "ceil": math.ceil, "floor": math.floor,
    "fabs": math.fabs, "log": math.log, "log10": math.log10,
    "exp": math.exp, "sin": math.sin, "cos": math.cos, "tan": math.tan,
    "degrees": math.degrees, "radians": math.radians,
}


@dataclass
class ToolResult:
    tool_name: str
    input: str
    output: str
    success: bool
    error: str = ""


def _bounded_number(value):
    """Reject booleans, non-numbers, non-finite values and unbounded results."""
    if type(value) not in (int, float):
        raise ValueError("only numeric results are supported")
    if isinstance(value, int):
        if value.bit_length() > 256:
            raise ValueError("integer result exceeds the safety bound")
    elif not math.isfinite(value) or abs(value) > 1e100:
        raise ValueError("numeric result exceeds the safety bound")
    return value


def _eval_numeric(node):
    """Interpret only numeric AST nodes; never evaluate or compile Python code."""
    if isinstance(node, ast.Constant):
        if type(node.value) not in (int, float):
            raise ValueError("only numeric literals are supported")
        return _bounded_number(node.value)

    if isinstance(node, ast.UnaryOp) and type(node.op) in _UNARY_OPERATORS:
        return _bounded_number(_UNARY_OPERATORS[type(node.op)](_eval_numeric(node.operand)))

    if isinstance(node, ast.BinOp) and type(node.op) in _BINARY_OPERATORS:
        left = _eval_numeric(node.left)
        right = _eval_numeric(node.right)
        if isinstance(node.op, ast.Pow) and abs(right) > 100:
            raise ValueError("exponent exceeds the safety bound")
        return _bounded_number(_BINARY_OPERATORS[type(node.op)](left, right))

    if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name):
        if node.value.id == "math" and node.attr in _MATH_CONSTANTS:
            return _MATH_CONSTANTS[node.attr]

    if isinstance(node, ast.Call):
        if (isinstance(node.func, ast.Name) and node.func.id == "print"
                and len(node.args) == 1 and not node.keywords):
            return _eval_numeric(node.args[0])
        if (isinstance(node.func, ast.Attribute)
                and isinstance(node.func.value, ast.Name)
                and node.func.value.id == "math"
                and node.func.attr in _MATH_FUNCTIONS
                and not node.keywords):
            args = [_eval_numeric(arg) for arg in node.args]
            return _bounded_number(_MATH_FUNCTIONS[node.func.attr](*args))

    raise ValueError(f"unsupported expression element: {type(node).__name__}")


class ToolRegistry:
    def __init__(self, beliefs_reader=None) -> None:
        self._beliefs_reader = beliefs_reader
        self._tools = {
            "web_fetch": {
                "description": "HTTP GET an allowed URL and return first 2000 chars of text",
                "fn": self._web_fetch,
            },
            "python_exec": {
                "description": "Evaluate bounded arithmetic expressions (not arbitrary Python)",
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

    def _web_fetch(self, url: str = "", query: str = "", **_) -> ToolResult:
        import urllib.parse
        target_url = url or _extract_url_from_query(query)
        if not target_url:
            target_url = _build_coingecko_url(query)
        if not target_url:
            return ToolResult("web_fetch", query, "", False, "no URL to fetch")

        try:
            parsed = urllib.parse.urlparse(target_url)
            domain = parsed.netloc.lstrip("www.")
            if not any(domain == d or domain.endswith("." + d) for d in _ALLOWED_DOMAINS):
                return ToolResult("web_fetch", target_url, "", False,
                                  f"domain not in allowlist: {domain}")
        except Exception as exc:
            return ToolResult("web_fetch", target_url, "", False, str(exc))

        try:
            import urllib.request
            req = urllib.request.Request(
                target_url, headers={"User-Agent": "NEX/5.0 research bot"}
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                raw = resp.read(8192).decode("utf-8", errors="replace")
            page_text = re.sub(r"<[^>]+>", " ", raw)
            page_text = re.sub(r"\s+", " ", page_text).strip()
            return ToolResult("web_fetch", target_url, page_text[:2000], True)
        except Exception as exc:
            return ToolResult("web_fetch", target_url, "", False, str(exc))

    def _python_exec(self, code: str = "", query: str = "", **_) -> ToolResult:
        # A query is not source code. Requiring an explicit code argument prevents
        # natural-language sentences from silently crossing this execution boundary.
        if not code or not code.strip():
            return ToolResult(
                "python_exec", query, "", False,
                "no arithmetic expression supplied; natural-language input is not executable",
            )
        if len(code) > 1000:
            return ToolResult("python_exec", code[:1000], "", False, "expression exceeds length limit")

        try:
            tree = ast.parse(code, mode="exec")
            if len(list(ast.walk(tree))) > 64:
                raise ValueError("expression exceeds complexity limit")

            outputs = []
            for statement in tree.body:
                if isinstance(statement, ast.Import):
                    if (len(statement.names) != 1
                            or statement.names[0].name != "math"
                            or statement.names[0].asname not in (None, "math")):
                        imported = statement.names[0].name if statement.names else "unknown"
                        raise ValueError(f"blocked import: {imported}")
                    continue
                if not isinstance(statement, ast.Expr):
                    raise ValueError("only arithmetic expressions and print(expression) are supported")
                outputs.append(_eval_numeric(statement.value))

            if not outputs:
                raise ValueError("no arithmetic expression supplied")
            output = str(outputs[-1])[:500]
            return ToolResult("python_exec", code, output, True)
        except Exception as exc:
            return ToolResult("python_exec", code, "", False, str(exc)[:200])

    def _beliefs_query(self, query: str = "", **_) -> ToolResult:
        if self._beliefs_reader is None:
            return ToolResult("beliefs_query", query, "", False, "no beliefs reader")
        try:
            from theory_x.stage3_world_model.retrieval import BeliefRetriever, format_beliefs_for_prompt
            retriever = BeliefRetriever(self._beliefs_reader)
            beliefs = retriever.retrieve(query, limit=5)
            result_text = format_beliefs_for_prompt(beliefs) if beliefs else "No relevant beliefs found."
            return ToolResult("beliefs_query", query, result_text, True)
        except Exception as exc:
            return ToolResult("beliefs_query", query, "", False, str(exc))


def _extract_url_from_query(query: str) -> str:
    """Pull an explicit URL from a query string if present."""
    match = re.search(r"https?://\S+", query)
    return match.group(0) if match else ""


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
