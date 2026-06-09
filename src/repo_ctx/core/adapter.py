"""Абстрактный интерфейс Adapter — единственное место, где ядро знает о форме адаптеров."""

import logging
from abc import ABC, abstractmethod
from typing import Any

logger = logging.getLogger(__name__)


class Adapter(ABC):
    """Базовый класс для всех targets. Ядро работает только через этот интерфейс."""

    @abstractmethod
    def memory_targets(self, profile: dict[str, Any]) -> dict[str, str]:
        """Возвращает {имя_исходного_файла_контекста: путь_назначения_в_репо}."""

    @abstractmethod
    def render_commands(self, source_dir: str, dest_root: str, dry_run: bool) -> list[str]:
        """Размещает файлы команд из source_dir в dest_root. Возвращает список затронутых путей."""

    @abstractmethod
    def render_agents(self, source_dir: str, dest_root: str, dry_run: bool) -> list[str]:
        """Размещает описания субагентов из source_dir в dest_root. Возвращает список затронутых путей."""

    @abstractmethod
    def merge_mcp(self, mcp_templates: list[dict], dest_root: str, dry_run: bool) -> list[str]:
        """Мёржит MCP-серверы по ключам в dest_root. Возвращает список затронутых путей."""
