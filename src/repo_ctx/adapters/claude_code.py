"""Адаптер Claude Code — размещает контент в CLAUDE.md, .claude/, .mcp.json."""

import json
import logging
import os
import shutil
from typing import Any

from repo_ctx.core.adapter import Adapter
from repo_ctx.core.merger import apply_marker_block
from repo_ctx.core.registry import register_adapter

logger = logging.getLogger(__name__)


class ClaudeCodeAdapter(Adapter):
    """Реализация Adapter для Claude Code harness."""

    def memory_targets(self, profile: dict[str, Any]) -> dict[str, str]:
        """Все context-файлы профиля сливаются в единый CLAUDE.md через маркер-блок."""
        logger.debug("memory_targets: профиль содержит context=%s", profile.get("context"))
        return {ctx: "CLAUDE.md" for ctx in profile.get("context", [])}

    def render_commands(self, source_dir: str, dest_root: str, dry_run: bool) -> list[str]:
        """Копирует *.md из source_dir в dest_root/.claude/commands/."""
        dest = os.path.join(dest_root, ".claude", "commands")
        logger.debug("render_commands: %s → %s (dry_run=%s)", source_dir, dest, dry_run)
        return self._copy_md_files(source_dir, dest, dry_run)

    def render_agents(self, source_dir: str, dest_root: str, dry_run: bool) -> list[str]:
        """Копирует *.md из source_dir в dest_root/.claude/agents/."""
        dest = os.path.join(dest_root, ".claude", "agents")
        logger.debug("render_agents: %s → %s (dry_run=%s)", source_dir, dest, dry_run)
        return self._copy_md_files(source_dir, dest, dry_run)

    def merge_mcp(self, mcp_templates: list[dict], dest_root: str, dry_run: bool) -> list[str]:
        """Мёржит серверы из mcp_templates в dest_root/.mcp.json по ключам.

        Существующие ключи не перезаписываются. Новые — добавляются.
        При dry_run файл не трогается.
        """
        mcp_path = os.path.join(dest_root, ".mcp.json")
        logger.debug("merge_mcp: %s (dry_run=%s), шаблонов=%d", mcp_path, dry_run, len(mcp_templates))

        if not mcp_templates:
            logger.debug("merge_mcp: шаблонов нет, пропускаем")
            return []

        # Читаем существующий .mcp.json или начинаем с пустой структуры
        existing: dict[str, Any] = {}
        if os.path.isfile(mcp_path):
            try:
                with open(mcp_path, encoding="utf-8") as f:
                    existing = json.load(f)
                logger.debug("merge_mcp: загружен существующий %s", mcp_path)
            except (json.JSONDecodeError, OSError) as exc:
                logger.warning("merge_mcp: не удалось прочитать %s: %s — начинаем заново", mcp_path, exc)
                existing = {}

        servers: dict[str, Any] = existing.get("mcpServers", {})
        added: list[str] = []
        skipped: list[str] = []

        for template in mcp_templates:
            template_servers = template.get("mcpServers", {})
            for server_name, server_cfg in template_servers.items():
                if server_name in servers:
                    logger.debug("merge_mcp: сервер '%s' уже существует, пропускаем", server_name)
                    skipped.append(server_name)
                else:
                    logger.info("merge_mcp: добавляем сервер '%s'", server_name)
                    servers[server_name] = server_cfg
                    added.append(server_name)

        if not added:
            logger.info("merge_mcp: новых серверов нет, %s не изменён", mcp_path)
            return []

        merged = {**existing, "mcpServers": servers}

        if dry_run:
            logger.info("[dry-run] merge_mcp: добавлено бы серверов: %s", added)
            return [mcp_path]

        # Создаём директорию при необходимости
        os.makedirs(os.path.dirname(mcp_path) if os.path.dirname(mcp_path) else ".", exist_ok=True)
        with open(mcp_path, "w", encoding="utf-8") as f:
            json.dump(merged, f, ensure_ascii=False, indent=2)
            f.write("\n")

        logger.info("merge_mcp: сохранён %s (добавлено: %s)", mcp_path, added)
        return [mcp_path]

    def write_memory(self, context_files: list[str], dest_root: str, dry_run: bool) -> list[str]:
        """Сливает список context_files в CLAUDE.md через маркер-блок.

        Все файлы склеиваются через разделитель и записываются единым управляемым блоком.
        """
        claude_md_path = os.path.join(dest_root, "CLAUDE.md")
        logger.debug(
            "write_memory: %d файлов контекста → %s (dry_run=%s)",
            len(context_files),
            claude_md_path,
            dry_run,
        )

        if not context_files:
            logger.debug("write_memory: нет файлов контекста, пропускаем")
            return []

        # Читаем все файлы контекста и склеиваем
        parts: list[str] = []
        for ctx_path in context_files:
            if not os.path.isfile(ctx_path):
                logger.warning("write_memory: файл контекста не найден: %s", ctx_path)
                continue
            with open(ctx_path, encoding="utf-8") as f:
                content = f.read().rstrip()
            parts.append(content)
            logger.debug("write_memory: прочитан %s (%d символов)", ctx_path, len(content))

        if not parts:
            logger.warning("write_memory: ни один файл контекста не удалось прочитать")
            return []

        new_content = "\n\n---\n\n".join(parts)

        # Читаем существующий CLAUDE.md
        existing = ""
        if os.path.isfile(claude_md_path):
            with open(claude_md_path, encoding="utf-8") as f:
                existing = f.read()
            logger.debug("write_memory: прочитан существующий CLAUDE.md (%d символов)", len(existing))

        result = apply_marker_block(existing, new_content)

        if dry_run:
            logger.info("[dry-run] write_memory: CLAUDE.md не записан")
            return [claude_md_path]

        with open(claude_md_path, "w", encoding="utf-8") as f:
            f.write(result)

        logger.info("write_memory: CLAUDE.md обновлён (%d символов)", len(result))
        return [claude_md_path]

    # ------------------------------------------------------------------
    # Внутренние методы
    # ------------------------------------------------------------------

    def _copy_md_files(self, src: str, dest: str, dry_run: bool) -> list[str]:
        """Копирует все *.md файлы из src в dest. Возвращает список путей назначения."""
        if not os.path.isdir(src):
            logger.debug("_copy_md_files: директория-источник не существует: %s", src)
            return []

        md_files = sorted(f for f in os.listdir(src) if f.endswith(".md"))
        logger.debug("_copy_md_files: найдено %d файлов в %s", len(md_files), src)

        if not md_files:
            return []

        if not dry_run:
            os.makedirs(dest, exist_ok=True)

        touched: list[str] = []
        for filename in md_files:
            src_path = os.path.join(src, filename)
            dest_path = os.path.join(dest, filename)
            if dry_run:
                logger.info("[dry-run] _copy_md_files: скопировано бы %s → %s", src_path, dest_path)
            else:
                shutil.copy2(src_path, dest_path)
                logger.info("_copy_md_files: скопирован %s → %s", src_path, dest_path)
            touched.append(dest_path)

        return touched


register_adapter("claude-code", ClaudeCodeAdapter)
