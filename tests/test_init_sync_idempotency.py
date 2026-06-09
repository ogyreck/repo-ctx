"""End-to-end тесты: init создаёт файлы, sync идемпотентен, локальный текст сохраняется."""

import json
import os
import tempfile
import unittest

from repo_ctx.adapters.claude_code import ClaudeCodeAdapter
from repo_ctx.core.engine import get_status, init_repo, sync_repo
from repo_ctx.core.manifest import MANIFEST_FILENAME
from repo_ctx.core.merger import START, END, has_marker_block


def _build_standards(base: str) -> str:
    """Создаёт минимальный standards-репозиторий для тестов."""
    std = os.path.join(base, "standards")
    os.makedirs(os.path.join(std, "profiles", "microservice"))
    os.makedirs(os.path.join(std, "context"))
    os.makedirs(os.path.join(std, "commands"))
    os.makedirs(os.path.join(std, "agents"))
    os.makedirs(os.path.join(std, "mcp"))

    # profile.json
    profile = {"context": ["conventions"], "commands": ["deploy"], "agents": [], "mcp": []}
    with open(os.path.join(std, "profiles", "microservice", "profile.json"), "w") as f:
        json.dump(profile, f)

    # context file
    with open(os.path.join(std, "context", "conventions.md"), "w") as f:
        f.write("# Project Conventions\n\nFollow these rules.")

    # command file
    with open(os.path.join(std, "commands", "deploy.md"), "w") as f:
        f.write("# /deploy\n\nDeploy the service.")

    return std


class TestInitRepo(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.base = self.tmp.name
        self.standards = _build_standards(self.base)
        self.dest = os.path.join(self.base, "target")
        os.makedirs(self.dest)
        # Создаём Dockerfile, чтобы профиль определился как microservice
        open(os.path.join(self.dest, "Dockerfile"), "w").close()
        self.adapter = ClaudeCodeAdapter()

    def tearDown(self):
        self.tmp.cleanup()

    def test_init_creates_manifest(self):
        init_repo(self.standards, self.dest, self.adapter)
        self.assertTrue(os.path.isfile(os.path.join(self.dest, MANIFEST_FILENAME)))

    def test_init_creates_claude_md_with_markers(self):
        init_repo(self.standards, self.dest, self.adapter)
        claude_md = os.path.join(self.dest, "CLAUDE.md")
        self.assertTrue(os.path.isfile(claude_md))
        with open(claude_md) as f:
            content = f.read()
        self.assertTrue(has_marker_block(content))
        self.assertIn("Project Conventions", content)

    def test_init_copies_commands(self):
        init_repo(self.standards, self.dest, self.adapter)
        cmd_path = os.path.join(self.dest, ".claude", "commands", "deploy.md")
        self.assertTrue(os.path.isfile(cmd_path))

    def test_init_manifest_contains_profile(self):
        init_repo(self.standards, self.dest, self.adapter)
        with open(os.path.join(self.dest, MANIFEST_FILENAME)) as f:
            manifest = json.load(f)
        self.assertEqual(manifest["profile"], "microservice")

    def test_dry_run_creates_no_files(self):
        init_repo(self.standards, self.dest, self.adapter, dry_run=True)
        self.assertFalse(os.path.isfile(os.path.join(self.dest, MANIFEST_FILENAME)))
        self.assertFalse(os.path.isfile(os.path.join(self.dest, "CLAUDE.md")))


class TestSyncIdempotency(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.base = self.tmp.name
        self.standards = _build_standards(self.base)
        self.dest = os.path.join(self.base, "target")
        os.makedirs(self.dest)
        open(os.path.join(self.dest, "Dockerfile"), "w").close()
        self.adapter = ClaudeCodeAdapter()
        # Первичный init
        init_repo(self.standards, self.dest, self.adapter)

    def tearDown(self):
        self.tmp.cleanup()

    def test_sync_is_idempotent(self):
        """Повторный sync с теми же standards не меняет файлы."""
        claude_md = os.path.join(self.dest, "CLAUDE.md")
        with open(claude_md) as f:
            after_init = f.read()

        sync_repo(self.standards, self.dest, self.adapter)
        with open(claude_md) as f:
            after_sync = f.read()

        # Содержимое управляемого блока не изменилось
        self.assertEqual(after_init, after_sync)

    def test_sync_preserves_user_text_before_markers(self):
        """Текст пользователя до маркеров остаётся нетронутым после sync."""
        claude_md = os.path.join(self.dest, "CLAUDE.md")
        with open(claude_md) as f:
            existing = f.read()
        user_prefix = "# My Project\n\nCustom header added by user.\n\n"
        with open(claude_md, "w") as f:
            f.write(user_prefix + existing)

        sync_repo(self.standards, self.dest, self.adapter)
        with open(claude_md) as f:
            result = f.read()

        self.assertTrue(result.startswith(user_prefix))
        self.assertIn("Project Conventions", result)

    def test_sync_preserves_user_text_after_markers(self):
        """Текст пользователя после маркеров остаётся нетронутым после sync."""
        claude_md = os.path.join(self.dest, "CLAUDE.md")
        user_suffix = "\n\n## My personal notes\n\nSome custom content."
        with open(claude_md, "a") as f:
            f.write(user_suffix)

        sync_repo(self.standards, self.dest, self.adapter)
        with open(claude_md) as f:
            result = f.read()

        self.assertIn("## My personal notes", result)
        self.assertIn("Project Conventions", result)


class TestGetStatus(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.base = self.tmp.name
        self.standards = _build_standards(self.base)
        self.dest = os.path.join(self.base, "target")
        os.makedirs(self.dest)
        open(os.path.join(self.dest, "Dockerfile"), "w").close()
        self.adapter = ClaudeCodeAdapter()

    def tearDown(self):
        self.tmp.cleanup()

    def test_status_not_initialized(self):
        status = get_status(self.dest)
        self.assertFalse(status["initialized"])

    def test_status_after_init(self):
        init_repo(self.standards, self.dest, self.adapter)
        status = get_status(self.dest)
        self.assertTrue(status["initialized"])
        self.assertEqual(status["profile"], "microservice")
        self.assertEqual(status["drifted"], [])


if __name__ == "__main__":
    unittest.main()
