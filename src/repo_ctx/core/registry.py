"""Реестр адаптеров (targets). Адаптер регистрирует себя при импорте своего модуля."""

import logging
from typing import TYPE_CHECKING

from repo_ctx.exceptions import AdapterNotFoundError

if TYPE_CHECKING:
    from repo_ctx.core.adapter import Adapter

logger = logging.getLogger(__name__)

_registry: dict[str, type["Adapter"]] = {}


def register_adapter(name: str, cls: type["Adapter"]) -> None:
    """Регистрирует адаптер под указанным именем. Повторная регистрация перезаписывает."""
    logger.debug("Регистрация адаптера: %s -> %s", name, cls.__name__)
    _registry[name] = cls


def get_adapter(name: str) -> type["Adapter"]:
    """Возвращает класс адаптера по имени.

    Raises:
        AdapterNotFoundError: если адаптер с таким именем не зарегистрирован.
    """
    logger.debug("Поиск адаптера: %s (зарегистрированы: %s)", name, list(_registry))
    if name not in _registry:
        available = ", ".join(sorted(_registry)) or "(нет)"
        raise AdapterNotFoundError(
            f"Адаптер '{name}' не найден. Доступные: {available}"
        )
    return _registry[name]


def list_adapters() -> list[str]:
    """Возвращает список имён всех зарегистрированных адаптеров."""
    return sorted(_registry)
