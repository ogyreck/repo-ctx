"""Тесты для ClaudeCodeAdapter.merge_mcp: добавление, skip existing, dry_run, идемпотентность."""

import json
import os
import tempfile
import unittest

from repo_ctx.adapters.claude_code import ClaudeCodeAdapter


MCP_TEMPLATE_A = {
    "mcpServers": {
        "server-a": {"command": "npx", "args": ["-y", "server-a-pkg"]}
    }
}

MCP_TEMPLATE_B = {
    "mcpServers": {
        "server-b": {"command": "npx", "args": ["-y", "server-b-pkg"]}
    }
}


class TestMergeMcp(unittest.TestCase):
    def setUp(self):
        self.adapter = ClaudeCodeAdapter()

    def test_creates_mcp_json_when_absent(self):
        with tempfile.TemporaryDirectory() as d:
            self.adapter.merge_mcp([MCP_TEMPLATE_A], d, dry_run=False)
            mcp_path = os.path.join(d, ".mcp.json")
            self.assertTrue(os.path.isfile(mcp_path))
            with open(mcp_path) as f:
                data = json.load(f)
            self.assertIn("server-a", data["mcpServers"])

    def test_adds_new_server_to_existing(self):
        with tempfile.TemporaryDirectory() as d:
            mcp_path = os.path.join(d, ".mcp.json")
            with open(mcp_path, "w") as f:
                json.dump({"mcpServers": {"existing": {"command": "cmd"}}}, f)
            self.adapter.merge_mcp([MCP_TEMPLATE_A], d, dry_run=False)
            with open(mcp_path) as f:
                data = json.load(f)
            self.assertIn("existing", data["mcpServers"])
            self.assertIn("server-a", data["mcpServers"])

    def test_skips_existing_server_key(self):
        with tempfile.TemporaryDirectory() as d:
            mcp_path = os.path.join(d, ".mcp.json")
            original_cfg = {"command": "original"}
            with open(mcp_path, "w") as f:
                json.dump({"mcpServers": {"server-a": original_cfg}}, f)
            self.adapter.merge_mcp([MCP_TEMPLATE_A], d, dry_run=False)
            with open(mcp_path) as f:
                data = json.load(f)
            # Значение не должно было перезаписаться
            self.assertEqual(data["mcpServers"]["server-a"], original_cfg)

    def test_dry_run_does_not_write(self):
        with tempfile.TemporaryDirectory() as d:
            result = self.adapter.merge_mcp([MCP_TEMPLATE_A], d, dry_run=True)
            # Должен вернуть путь (намерение), но файл не создаётся
            self.assertTrue(len(result) > 0)
            mcp_path = os.path.join(d, ".mcp.json")
            self.assertFalse(os.path.isfile(mcp_path))

    def test_idempotent_repeated_merge(self):
        """Повторный merge с тем же шаблоном не меняет содержимое файла."""
        with tempfile.TemporaryDirectory() as d:
            mcp_path = os.path.join(d, ".mcp.json")
            self.adapter.merge_mcp([MCP_TEMPLATE_A], d, dry_run=False)
            with open(mcp_path) as f:
                first_content = f.read()
            self.adapter.merge_mcp([MCP_TEMPLATE_A], d, dry_run=False)
            with open(mcp_path) as f:
                second_content = f.read()
            self.assertEqual(first_content, second_content)

    def test_empty_templates_returns_empty(self):
        with tempfile.TemporaryDirectory() as d:
            result = self.adapter.merge_mcp([], d, dry_run=False)
            self.assertEqual(result, [])

    def test_multiple_templates_merged(self):
        with tempfile.TemporaryDirectory() as d:
            self.adapter.merge_mcp([MCP_TEMPLATE_A, MCP_TEMPLATE_B], d, dry_run=False)
            mcp_path = os.path.join(d, ".mcp.json")
            with open(mcp_path) as f:
                data = json.load(f)
            self.assertIn("server-a", data["mcpServers"])
            self.assertIn("server-b", data["mcpServers"])


if __name__ == "__main__":
    unittest.main()
