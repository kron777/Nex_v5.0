"""Tool registry + tool caller tests.

Covers:
- ToolRegistry.available() lists three tools
- ToolRegistry.execute() returns ToolResult with success/failure
- _python_exec() runs safe math code
- _python_exec() blocks dangerous imports
- _web_fetch() rejects domains not in allowlist
- _beliefs_query() returns no-reader error when reader is None
- ToolCaller.should_use_tool() returns correct tool for each heuristic
- ToolCaller.build_tool_prompt() returns a non-empty string
- Unknown tool returns success=False
"""
from __future__ import annotations

import unittest

from tests import _bootstrap  # noqa: F401


class TestToolRegistry(unittest.TestCase):

    def setUp(self):
        from theory_x.stage_capability.tools import ToolRegistry
        self.reg = ToolRegistry(beliefs_reader=None)

    def test_available_lists_three_tools(self):
        tools = self.reg.available()
        names = {t["name"] for t in tools}
        self.assertEqual(names, {"web_fetch", "python_exec", "beliefs_query"})

    def test_python_exec_safe_math(self):
        result = self.reg.execute("python_exec", code="print(2 + 2)")
        self.assertTrue(result.success, result.error)
        self.assertIn("4", result.output)

    def test_python_exec_blocks_os_import(self):
        result = self.reg.execute("python_exec", code="import os; print(os.getcwd())")
        self.assertFalse(result.success)
        self.assertIn("blocked import", result.error)

    def test_python_exec_blocks_sys_import(self):
        result = self.reg.execute("python_exec", code="import sys; print(sys.version)")
        self.assertFalse(result.success)
        self.assertIn("blocked import", result.error)

    def test_python_exec_allows_math(self):
        result = self.reg.execute("python_exec", code="import math; print(math.pi)")
        self.assertTrue(result.success, result.error)
        self.assertIn("3.14", result.output)

    def test_web_fetch_rejects_unknown_domain(self):
        result = self.reg.execute("web_fetch", url="https://evil.com/steal")
        self.assertFalse(result.success)
        self.assertIn("allowlist", result.error)

    def test_web_fetch_no_url_no_query(self):
        result = self.reg.execute("web_fetch")
        self.assertFalse(result.success)

    def test_beliefs_query_no_reader(self):
        result = self.reg.execute("beliefs_query", query="what do I believe?")
        self.assertFalse(result.success)
        self.assertIn("no beliefs reader", result.error)

    def test_unknown_tool_returns_failure(self):
        result = self.reg.execute("nonexistent_tool", query="test")
        self.assertFalse(result.success)
        self.assertIn("unknown tool", result.error)

    def test_tool_result_fields(self):
        from theory_x.stage_capability.tools import ToolResult
        r = ToolResult(tool_name="x", input="i", output="o", success=True)
        self.assertEqual(r.tool_name, "x")
        self.assertEqual(r.error, "")


class TestToolCaller(unittest.TestCase):

    def setUp(self):
        from theory_x.stage_capability.tools import ToolRegistry
        from theory_x.stage_capability.tool_caller import ToolCaller
        self.reg = ToolRegistry(beliefs_reader=None)
        self.caller = ToolCaller(self.reg)

    def test_price_query_returns_web_fetch(self):
        tool = self.caller.should_use_tool("what is the bitcoin price?", [])
        self.assertEqual(tool, "web_fetch")

    def test_math_query_returns_python_exec(self):
        tool = self.caller.should_use_tool("calculate 15 * 37", [])
        self.assertEqual(tool, "python_exec")

    def test_belief_query_returns_beliefs_query(self):
        tool = self.caller.should_use_tool("what do I believe about consciousness?", [])
        self.assertEqual(tool, "beliefs_query")

    def test_current_query_returns_web_fetch(self):
        tool = self.caller.should_use_tool("what is happening right now in AI?", [])
        self.assertEqual(tool, "web_fetch")

    def test_factual_no_beliefs_returns_web_fetch(self):
        tool = self.caller.should_use_tool("what is the Cambrian explosion?", beliefs=[])
        self.assertEqual(tool, "web_fetch")

    def test_factual_with_beliefs_returns_none(self):
        tool = self.caller.should_use_tool("tell me something", beliefs=["a belief"])
        self.assertIsNone(tool)

    def test_plain_query_returns_none(self):
        tool = self.caller.should_use_tool("hello", beliefs=["some belief"])
        self.assertIsNone(tool)

    def test_build_tool_prompt_non_empty(self):
        from theory_x.stage_capability.tools import ToolResult
        result = ToolResult("web_fetch", "query", "some output", True)
        prompt = self.caller.build_tool_prompt("query", result)
        self.assertIn("web_fetch", prompt)
        self.assertIn("some output", prompt)

    def test_build_tool_kwargs_web_fetch(self):
        kwargs = self.caller.build_tool_kwargs("btc price", "web_fetch")
        self.assertIn("query", kwargs)

    def test_build_tool_kwargs_python_exec(self):
        kwargs = self.caller.build_tool_kwargs("calculate 2+2", "python_exec")
        self.assertIn("query", kwargs)


if __name__ == "__main__":
    unittest.main()
