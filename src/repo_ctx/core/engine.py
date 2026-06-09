"""Бизнес-логика: init_repo, sync_repo, get_status.

Оркестрирует core-модули и вызывает методы адаптера. Ядро не знает о конкретных адаптерах.
"""

import datetime
import logging
import os
from typing import Any

from repo_ctx.core.adapter import Adapter
from repo_ctx.core.manifest import get_source_commit, load_manifest, save_manifest
from repo_ctx.core.merger import has_marker_block
from repo_ctx.core.profile import detect_profile, load_profile
from repo_ctx.exceptions import ProfileNotFoundError, SourceNotFoundError

logger = logging.getLogger(__name__)


def init_repo(
    source_dir: str,
    dest_root: str,
    adapter: Adapter,
    *,
    profile_name: str | None = None,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Первичная раскатка standards в целевой репозиторий.

    Определяет профиль (или использует переданный), загружает profile.json,
    вызывает методы адаптера для каждого типа контента, сохраняет манифест.

    Returns:
        Словарь с результатами: profile, managed_files, source_commit.
    """
    logger.info(
        "init_repo: source=%s, dest=%s, profile=%s, dry_run=%s",
        source_dir,
        dest_root,
        profile_name,
        dry_run,
    )

    _check_source(source_dir)

    # Определяем профиль
    if profile_name is None:
        profile_name = detect_profile(dest_root)
        logger.info("init_repo: определён профиль: %s", profile_name)

    profile = load_profile(profile_name, source_dir)
    logger.debug("init_repo: профиль загружен: %s", profile)

    managed_files: list[str] = []

    # Контекст → memory (CLAUDE.md у claude-code адаптера)
    context_files = _resolve_context_files(profile, source_dir)
    logger.debug("init_repo: файлы контекста: %s", context_files)
    if hasattr(adapter, "write_memory"):
        touched = adapter.write_memory(context_files, dest_root, dry_run)  # type: ignore[attr-defined]
        managed_files.extend(touched)
        logger.info("init_repo: write_memory затронул: %s", touched)

    # Команды
    commands_dir = os.path.join(source_dir, "commands")
    touched = adapter.render_commands(commands_dir, dest_root, dry_run)
    managed_files.extend(touched)
    logger.info("init_repo: render_commands затронул: %s", touched)

    # Агенты
    agents_dir = os.path.join(source_dir, "agents")
    touched = adapter.render_agents(agents_dir, dest_root, dry_run)
    managed_files.extend(touched)
    logger.info("init_repo: render_agents затронул: %s", touched)

    # MCP
    mcp_templates = _load_mcp_templates(profile, source_dir)
    touched = adapter.merge_mcp(mcp_templates, dest_root, dry_run)
    managed_files.extend(touched)
    logger.info("init_repo: merge_mcp затронул: %s", touched)

    source_commit = get_source_commit(source_dir)
    manifest = _build_manifest(source_dir, profile_name, source_commit, managed_files)

    save_manifest(dest_root, manifest, dry_run=dry_run)
    logger.info("init_repo: завершено. Управляемых файлов: %d", len(managed_files))

    return {
        "profile": profile_name,
        "managed_files": managed_files,
        "source_commit": source_commit,
    }


def sync_repo(
    source_dir: str,
    dest_root: str,
    adapter: Adapter,
    *,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Обновление standards в целевом репозитории с сохранением локальных правок.

    Читает профиль из манифеста. Повторно применяет все методы адаптера.
    Идемпотентен: повторный вызов без изменений source не меняет файлы.

    Returns:
        Словарь с результатами: profile, managed_files, source_commit.
    """
    logger.info("sync_repo: source=%s, dest=%s, dry_run=%s", source_dir, dest_root, dry_run)

    _check_source(source_dir)

    manifest = load_manifest(dest_root)
    if manifest is None:
        logger.info("sync_repo: манифест не найден, выполняем init_repo")
        return init_repo(source_dir, dest_root, adapter, dry_run=dry_run)

    profile_name = manifest.get("profile", "default")
    logger.info("sync_repo: профиль из манифеста: %s", profile_name)

    profile = load_profile(profile_name, source_dir)

    managed_files: list[str] = []

    context_files = _resolve_context_files(profile, source_dir)
    if hasattr(adapter, "write_memory"):
        touched = adapter.write_memory(context_files, dest_root, dry_run)  # type: ignore[attr-defined]
        managed_files.extend(touched)
        logger.info("sync_repo: write_memory: %s", touched)

    commands_dir = os.path.join(source_dir, "commands")
    touched = adapter.render_commands(commands_dir, dest_root, dry_run)
    managed_files.extend(touched)
    logger.info("sync_repo: render_commands: %s", touched)

    agents_dir = os.path.join(source_dir, "agents")
    touched = adapter.render_agents(agents_dir, dest_root, dry_run)
    managed_files.extend(touched)
    logger.info("sync_repo: render_agents: %s", touched)

    mcp_templates = _load_mcp_templates(profile, source_dir)
    touched = adapter.merge_mcp(mcp_templates, dest_root, dry_run)
    managed_files.extend(touched)
    logger.info("sync_repo: merge_mcp: %s", touched)

    source_commit = get_source_commit(source_dir)
    updated_manifest = _build_manifest(source_dir, profile_name, source_commit, managed_files)

    save_manifest(dest_root, updated_manifest, dry_run=dry_run)
    logger.info("sync_repo: завершено. Управляемых файлов: %d", len(managed_files))

    return {
        "profile": profile_name,
        "managed_files": managed_files,
        "source_commit": source_commit,
    }


def get_status(dest_root: str) -> dict[str, Any]:
    """Возвращает состояние целевого репозитория: профиль, дата применения, дрейф.

    Дрейф: файлы в манифесте, которые больше не управляются маркерами (удалены или изменены).
    """
    logger.info("get_status: dest=%s", dest_root)

    manifest = load_manifest(dest_root)
    if manifest is None:
        logger.info("get_status: манифест не найден — репозиторий не инициализирован")
        return {"initialized": False}

    managed_files: list[str] = manifest.get("managed_files", [])
    drifted: list[str] = []

    for rel_path in managed_files:
        abs_path = os.path.join(dest_root, rel_path)
        if not os.path.isfile(abs_path):
            logger.warning("get_status: файл отсутствует (дрейф): %s", abs_path)
            drifted.append(rel_path)
            continue
        # Маркеры проверяем только в memory-файлах (CLAUDE.md).
        # Файлы команд/агентов — обычные копии, маркеров не содержат.
        if os.path.basename(abs_path) == "CLAUDE.md":
            with open(abs_path, encoding="utf-8") as f:
                content = f.read()
            if not has_marker_block(content):
                logger.warning("get_status: маркеры удалены (дрейф): %s", abs_path)
                drifted.append(rel_path)

    status = {
        "initialized": True,
        "profile": manifest.get("profile"),
        "source": manifest.get("source"),
        "applied_commit": manifest.get("applied_commit"),
        "timestamp": manifest.get("timestamp"),
        "managed_files": managed_files,
        "drifted": drifted,
    }
    logger.debug("get_status: результат: %s", status)
    return status


# ------------------------------------------------------------------
# Вспомогательные функции
# ------------------------------------------------------------------

def _check_source(source_dir: str) -> None:
    """Проверяет доступность standards-директории."""
    if not os.path.isdir(source_dir):
        raise SourceNotFoundError(
            f"Standards-репозиторий не найден: {source_dir}"
        )
    logger.debug("_check_source: OK %s", source_dir)


def _resolve_context_files(profile: dict, source_dir: str) -> list[str]:
    """Строит список абсолютных путей context-файлов по именам в профиле."""
    context_names: list[str] = profile.get("context", [])
    paths = []
    for name in context_names:
        # Ищем файл в standards/context/
        ctx_path = os.path.join(source_dir, "context", name)
        if not ctx_path.endswith(".md"):
            ctx_path += ".md"
        paths.append(ctx_path)
    logger.debug("_resolve_context_files: %s", paths)
    return paths


def _load_mcp_templates(profile: dict, source_dir: str) -> list[dict]:
    """Загружает MCP-шаблоны, перечисленные в профиле."""
    import json

    mcp_names: list[str] = profile.get("mcp", [])
    templates: list[dict] = []
    for name in mcp_names:
        mcp_path = os.path.join(source_dir, "mcp", name)
        if not mcp_path.endswith(".json"):
            mcp_path += ".json"
        if not os.path.isfile(mcp_path):
            logger.warning("_load_mcp_templates: MCP-файл не найден: %s", mcp_path)
            continue
        try:
            with open(mcp_path, encoding="utf-8") as f:
                templates.append(json.load(f))
            logger.debug("_load_mcp_templates: загружен %s", mcp_path)
        except json.JSONDecodeError as exc:
            logger.error("_load_mcp_templates: невалидный JSON в %s: %s", mcp_path, exc)

    return templates


def _build_manifest(
    source_dir: str,
    profile_name: str,
    source_commit: str | None,
    managed_files: list[str],
) -> dict:
    """Формирует словарь манифеста."""
    return {
        "source": os.path.abspath(source_dir),
        "profile": profile_name,
        "applied_commit": source_commit,
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "managed_files": managed_files,
    }
