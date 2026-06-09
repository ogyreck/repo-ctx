"""Тесты для core/registry.py: регистрация, поиск, ошибки."""

import unittest

from repo_ctx.core.adapter import Adapter
from repo_ctx.core.registry import (
    _registry,
    get_adapter,
    list_adapters,
    register_adapter,
)
from repo_ctx.exceptions import AdapterNotFoundError


class _DummyAdapter(Adapter):
    def memory_targets(self, profile):
        return {}

    def render_commands(self, source_dir, dest_root, dry_run):
        return []

    def render_agents(self, source_dir, dest_root, dry_run):
        return []

    def merge_mcp(self, mcp_templates, dest_root, dry_run):
        return []


class _AnotherAdapter(_DummyAdapter):
    pass


class TestRegistry(unittest.TestCase):
    def setUp(self):
        # Сохраняем и очищаем реестр перед каждым тестом
        self._saved = dict(_registry)
        _registry.clear()

    def tearDown(self):
        _registry.clear()
        _registry.update(self._saved)

    def test_register_and_get(self):
        register_adapter("test-dummy", _DummyAdapter)
        cls = get_adapter("test-dummy")
        self.assertIs(cls, _DummyAdapter)

    def test_unknown_adapter_raises(self):
        with self.assertRaises(AdapterNotFoundError):
            get_adapter("nonexistent")

    def test_overwrite_registration(self):
        register_adapter("test-dummy", _DummyAdapter)
        register_adapter("test-dummy", _AnotherAdapter)
        self.assertIs(get_adapter("test-dummy"), _AnotherAdapter)

    def test_list_adapters_returns_sorted(self):
        register_adapter("zzz", _DummyAdapter)
        register_adapter("aaa", _DummyAdapter)
        names = list_adapters()
        self.assertEqual(names, ["aaa", "zzz"])

    def test_list_adapters_empty(self):
        self.assertEqual(list_adapters(), [])

    def test_error_message_contains_available_adapters(self):
        register_adapter("available-one", _DummyAdapter)
        with self.assertRaises(AdapterNotFoundError) as ctx:
            get_adapter("missing")
        self.assertIn("available-one", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
