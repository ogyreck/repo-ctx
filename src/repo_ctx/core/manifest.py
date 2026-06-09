"""Чтение и запись манифеста .repo-ctx.json в целевом репозитории."""

import json
import logging
import os
import subprocess

from repo_ctx.exceptions import ManifestError

logger = logging.getLogger(__name__)

MANIFEST_FILENAME = ".repo-ctx.json"


def load_manifest(repo_path: str) -> dict | None:
    """Читает .repo-ctx.json из repo_path. Возвращает None, если файл отсутствует.

    Raises:
        ManifestError: файл существует, но содержит невалидный JSON.
    """
    manifest_path = os.path.join(repo_path, MANIFEST_FILENAME)
    logger.debug("load_manifest: чтение %s", manifest_path)

    if not os.path.isfile(manifest_path):
        logger.debug("load_manifest: файл не найден, возвращаем None")
        return None

    try:
        with open(manifest_path, encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as exc:
        raise ManifestError(
            f"Невалидный JSON в манифесте: {manifest_path}"
        ) from exc

    logger.debug("load_manifest: загружен манифест, ключи: %s", list(data))
    return data


def save_manifest(repo_path: str, data: dict, dry_run: bool = False) -> None:
    """Записывает data в .repo-ctx.json. При dry_run файл не трогается."""
    manifest_path = os.path.join(repo_path, MANIFEST_FILENAME)
    logger.debug(
        "save_manifest: %s%s",
        manifest_path,
        " [dry-run, пропускаем запись]" if dry_run else "",
    )

    if dry_run:
        logger.info("[dry-run] Манифест не записан: %s", manifest_path)
        return

    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")

    logger.info("Манифест сохранён: %s", manifest_path)


def get_source_commit(source_path: str) -> str | None:
    """Возвращает HEAD-коммит standards-репозитория через git rev-parse.

    Возвращает None, если source_path не является git-репозиторием или git недоступен.
    """
    logger.debug("get_source_commit: git rev-parse HEAD в %s", source_path)
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=source_path,
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode == 0:
            commit = result.stdout.strip()
            logger.debug("get_source_commit: %s", commit)
            return commit
        logger.warning(
            "get_source_commit: git вернул код %d: %s",
            result.returncode,
            result.stderr.strip(),
        )
        return None
    except (FileNotFoundError, subprocess.TimeoutExpired) as exc:
        logger.warning("get_source_commit: не удалось выполнить git: %s", exc)
        return None
