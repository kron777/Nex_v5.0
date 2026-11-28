"""Tool registry + caller boundary tests.

These tests cover tool selection, bounded arithmetic interpretation, and the
rule that natural-language input must never become executable Python source.
"""
from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch

from tests import _bootstrap  # noqa: F401


class TestToolRegistry(unittest.TestCase):

    def setUp(self):
        from theory_x.stage_capability.tools import ToolRegistry
        self.reg = ToolRegistry(beliefs_reader=None)

    def test_available_lists_three_tools(self):
        tools = self.reg.available()
        names = {tool["name"] for tool in tools}
        self.assertEqual(names, {"web_fetch", "python_exec", "beliefs_query"})

    def test_python_exec_safe_math(self):
        result = self.reg.execute("python_exec", code="print(2 + 2)")
        self.assertTrue(result.success, result.error)
        self.assertEqual(result.output, "4")

    def test_python_exec_allows_math_constant(self):
        result = self.reg.execute("python_exec", code="import math; print(math.pi)")
        self.assertTrue(result.success, result.error)
        self.assertIn("3.14159", result.output)

    def test_python_exec_allows_bounded_math_function(self):
        result = self.reg.execute("python_exec", code="print(math.sqrt(81))")
        self.assertTrue(result.success, result.error)
        self.assertEqual(result.output, "9.0")

    def test_python_exec_blocks_os_import(self):
        result = self.reg.execute("python_exec", code="import os; print(os.getcwd())")
        self.assertFalse(result.success)
        self.assertIn("blocked import", result.error)

    def test_python_exec_blocks_sys_import(self):
        result = self.reg.execute("python_exec", code="import sys; print(sys.version)")
        self.assertFalse(result.success)
        self.assertIn("blocked import", result.error)

    def test_python_exec_rejects_dunder_import(self):
        result = self.reg.execute(
            "python_exec", code="print(__import__('os').system('echo unsafe'))"
        )
        self.assertFalse(result.success)
        self.assertIn("unsupported", result.error)

    def test_python_exec_rejects_file_access(self):
        result = self.reg.execute(
            "python_exec", code="print(open('/tmp/nex-should-not-exist', 'w'))"
        )
        self.assertFalse(result.success)
        self.assertIn("unsupported", result.error)

    def test_python_exec_rejects_query_as_code(self):
        result = self.reg.execute("python_exec", query="calculate 15 * 37")
        self.assertFalse(result.success)
        self.assertIn("natural-language input", result.error)

    def test_python_exec_rejects_assignment_and_loops(self):
        result = self.reg.execute("python_exec", code="while True: pass")
        self.assertFalse(result.success)
        self.assertIn("only arithmetic", result.error)

    def test_python_exec_rejects_excessive_exponent(self):
        result = self.reg.execute("python_exec", code="print(2 ** 1000)")
        self.assertFalse(result.success)
        self.assertIn("exponent", result.error)

    def test_web_fetch_rejects_unknown_domain(self):
        result = self.reg.execute("web_fetch", url="https://evil.com/steal")
        self.assertFalse(result.success)
        self.assertIn("allowlist", result.error)

    def test_web_fetch_accepts_allowlisted_hostname_with_port_and_disables_redirects(self):
        import urllib.request

        response = MagicMock()
        response.__enter__.return_value = response
        response.read.return_value = b"<p>allowed response</p>"
        opener = MagicMock()
        opener.open.return_value = response
        captured = {}

        def build_opener(*handlers):
            captured["handlers"] = handlers
            return opener

        with patch("urllib.request.build_opener", side_effect=build_opener):
            result = self.reg.execute(
                "web_fetch", url="https://www.openai.com:443/research"
            )

        self.assertTrue(result.success, result.error)
        self.assertIn("allowed response", result.output)
        opener.open.assert_called_once()
        redirect_class = next(
            handler for handler in captured["handlers"]
            if isinstance(handler, type)
            and issubclass(handler, urllib.request.HTTPRedirectHandler)
        )
        redirect_handler = redirect_class()
        self.assertIsNone(
            redirect_handler.redirect_request(
                None, None, 302, "Found", {}, "http://127.0.0.1/private"
            )
        )

    def test_web_fetch_rejects_credentials_and_non_http_schemes(self):
        with patch("urllib.request.build_opener") as build_opener:
            credentials = self.reg.execute(
                "web_fetch", url="https://user:secret@openai.com/private"
            )
            unsupported = self.reg.execute(
                "web_fetch", url="ftp://openai.com/research"
            )

        self.assertFalse(credentials.success)
        self.assertIn("credentials", credentials.error)
        self.assertFalse(unsupported.success)
        self.assertIn("scheme", unsupported.error)
        build_opener.assert_not_called()

    def test_coingecko_symbol_matching_uses_word_boundaries(self):
        from theory_x.stage_capability.tools import _build_coingecko_url
        self.assertEqual(_build_coingecko_url("whether the market is trading"), "")
        self.assertIn("ethereum", _build_coingecko_url("ETH price"))

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
        result = ToolResult(tool_name="x", input="i", output="o", success=True)
        self.assertEqual(result.error, "")


class TestToolCaller(unittest.TestCase):

    def setUp(self):
        from theory_x.stage_capability.tools import ToolRegistry
        from theory_x.stage_capability.tool_caller import ToolCaller
        self.reg = ToolRegistry(beliefs_reader=None)
        self.caller = ToolCaller(self.reg)

    def test_price_query_returns_web_fetch(self):
        tool = self.caller.should_use_tool("what is the bitcoin price?")
        self.assertEqual(tool, "web_fetch")

    def test_math_query_returns_python_exec(self):
        tool = self.caller.should_use_tool("calculate 15 * 37")
        self.assertEqual(tool, "python_exec")

    def test_math_query_does_not_execute_unparsed_sentence(self):
        self.assertIsNone(self.caller.should_use_tool("calculate the number of cats"))
        self.assertIsNone(self.caller.should_use_tool("math is interesting"))

    def test_belief_query_returns_beliefs_query(self):
        tool = self.caller.should_use_tool("what do I believe about consciousness?")
        self.assertEqual(tool, "beliefs_query")

    def test_generic_current_query_without_fetch_target_does_not_select_web_fetch(self):
        tool = self.caller.should_use_tool("what is happening right now in AI?")
        self.assertIsNone(tool)

    def test_generic_factual_query_without_fetch_target_does_not_select_web_fetch(self):
        tool = self.caller.should_use_tool("what is the Cambrian explosion?")
        self.assertIsNone(tool)

    def test_explicit_url_selects_web_fetch(self):
        tool = self.caller.should_use_tool("summarize https://openai.com/research")
        self.assertEqual(tool, "web_fetch")

    def test_unsupported_price_target_does_not_select_web_fetch(self):
        tool = self.caller.should_use_tool("what is the price of silver?")
        self.assertIsNone(tool)

    def test_current_supported_crypto_query_selects_web_fetch(self):
        tool = self.caller.should_use_tool("what is the current bitcoin price?")
        self.assertEqual(tool, "web_fetch")

    def test_crypto_news_query_does_not_select_price_fetch(self):
        tool = self.caller.should_use_tool("what is the latest bitcoin news?")
        self.assertIsNone(tool)

    def test_non_actionable_text_returns_none(self):
        tool = self.caller.should_use_tool("tell me something")
        self.assertIsNone(tool)

    def test_plain_query_returns_none(self):
        tool = self.caller.should_use_tool("hello")
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


    def test_calculation_sentence_traces_through_registry(self):
        query = "calculate 15 * 37"
        tool_name = self.caller.should_use_tool(query)
        self.assertEqual(tool_name, "python_exec")
        kwargs = self.caller.build_tool_kwargs(query, tool_name)
        result = self.reg.execute(tool_name, **kwargs)
        self.assertTrue(result.success, result.error)
        self.assertEqual(result.output, "555")
        prompt = self.caller.build_tool_prompt(query, result)
        self.assertIn("555", prompt)

    def test_code_injection_sentence_is_not_selected_as_a_tool(self):
        query = "calculate __import__('os').system('echo unsafe')"
        self.assertIsNone(self.caller.should_use_tool(query))

    def test_build_tool_kwargs_python_exec(self):
        kwargs = self.caller.build_tool_kwargs("calculate 2+2", "python_exec")
        self.assertEqual(kwargs, {"code": "print(2+2)"})
        self.assertNotIn("query", kwargs)


    def test_whats_prefix_selects_bounded_arithmetic(self):
        self.assertEqual(
            self.caller.should_use_tool("what's 2 + 2"),
            "python_exec",
        )

    def test_oversized_math_expression_is_rejected_before_ast_parse(self):
        query = "calculate " + ("1+" * 500) + "1"
        with patch(
            "theory_x.stage_capability.tool_caller.ast.parse"
        ) as parse:
            self.assertIsNone(self.caller.should_use_tool(query))
            parse.assert_not_called()

    def test_recursive_ast_parse_failure_is_a_non_selection(self):
        with patch(
            "theory_x.stage_capability.tool_caller.ast.parse",
            side_effect=RecursionError("synthetic parser depth"),
        ):
            self.assertIsNone(
                self.caller.should_use_tool("calculate 2 + 2")
            )

    def test_expression_ast_node_budget_is_enforced(self):
        query = "calculate " + "+".join(["1"] * 40)
        self.assertIsNone(self.caller.should_use_tool(query))


if __name__ == "__main__":
    unittest.main()
