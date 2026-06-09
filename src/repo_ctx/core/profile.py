"""Загрузка профиля из standards-репо и эвристическое определение профиля проекта."""

import json
import logging
import os

from repo_ctx.exceptions import ManifestError, ProfileNotFoundError

logger = logging.getLogger(__name__)


def load_profile(profile_name: str, standards_dir: str) -> dict:
    """Загружает profile.json для указанного профиля.

    Raises:
        ProfileNotFoundError: директория профиля или profile.json не существует.
        ManifestError: profile.json содержит невалидный JSON.
    """
    profile_path = os.path.join(standards_dir, "profiles", profile_name, "profile.json")
    logger.debug("load_profile: чтение %s", profile_path)

    if not os.path.isfile(profile_path):
        raise ProfileNotFoundError(
            f"Профиль '{profile_name}' не найден: {profile_path}"
        )

    try:
        with open(profile_path, encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as exc:
        raise ManifestError(
            f"Невалидный JSON в профиле '{profile_name}': {profile_path}"
        ) from exc

    logger.debug("load_profile: загружен профиль '%s' (%d ключей)", profile_name, len(data))
    return data


def detect_profile(repo_path: str) -> str:
    """Эвристически определяет тип проекта по содержимому директории.

    Эвристики (в порядке приоритета):
    1. Dockerfile → microservice
    2. roles/ директория → ansible-role
    3. Иначе → default
    """
    logger.debug("detect_profile: анализ %s", repo_path)

    if os.path.isfile(os.path.join(repo_path, "Dockerfile")):
        logger.info("detect_profile: обнаружен Dockerfile → microservice")
        return "microservice"

    if os.path.isdir(os.path.join(repo_path, "roles")):
        logger.info("detect_profile: обнаружена директория roles/ → ansible-role")
        return "ansible-role"

    logger.info("detect_profile: специфика не обнаружена → default")
    return "default"


def list_profiles(standards_dir: str) -> list[str]:
    """Возвращает список доступных профилей в standards-репо."""
    profiles_dir = os.path.join(standards_dir, "profiles")
    logger.debug("list_profiles: поиск профилей в %s", profiles_dir)

    if not os.path.isdir(profiles_dir):
        logger.warning("list_profiles: директория profiles/ не найдена в %s", standards_dir)
        return []

    profiles = [
        entry
        for entry in os.listdir(profiles_dir)
        if os.path.isfile(os.path.join(profiles_dir, entry, "profile.json"))
    ]
    profiles.sort()
    logger.debug("list_profiles: найдено %d профилей: %s", len(profiles), profiles)
    return profiles
