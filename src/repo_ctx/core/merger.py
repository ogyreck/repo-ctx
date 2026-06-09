"""Маркер-мёрж: управляемые блоки в текстовых файлах.

Инвариант идемпотентности: apply_marker_block(apply_marker_block(text, c), c) == apply_marker_block(text, c).
"""

import logging

logger = logging.getLogger(__name__)

START = "<!-- repo-ctx:managed:start -->"
END = "<!-- repo-ctx:managed:end -->"


def has_marker_block(text: str) -> bool:
    """Возвращает True, если в тексте есть оба маркера."""
    result = START in text and END in text
    logger.debug("has_marker_block: %s", result)
    return result


def extract_managed_content(text: str) -> str | None:
    """Извлекает содержимое между маркерами. Возвращает None, если маркеров нет."""
    if not has_marker_block(text):
        logger.debug("extract_managed_content: маркеры не найдены")
        return None
    start_idx = text.index(START) + len(START)
    end_idx = text.index(END)
    content = text[start_idx:end_idx]
    # убираем ведущий и завершающий перенос строки, добавленный при записи
    if content.startswith("\n"):
        content = content[1:]
    if content.endswith("\n"):
        content = content[:-1]
    logger.debug("extract_managed_content: извлечено %d символов", len(content))
    return content


def apply_marker_block(existing: str, new_content: str) -> str:
    """Вставляет new_content в маркер-блок внутри existing.

    - Если маркеров нет — добавляет блок в конец файла.
    - Текст вне маркеров не трогает (до и после блока).
    - Идемпотентен: повторный вызов с тем же new_content даёт тот же результат.
    """
    logger.debug(
        "apply_marker_block: existing=%d chars, new_content=%d chars",
        len(existing),
        len(new_content),
    )

    if has_marker_block(existing):
        before = existing[: existing.index(START)]
        after = existing[existing.index(END) + len(END) :]
        result = f"{before}{START}\n{new_content}\n{END}{after}"
        logger.debug("apply_marker_block: обновлён существующий блок")
    else:
        # Добавляем блок в конец; обеспечиваем один перенос строки перед маркером
        separator = "\n" if existing and not existing.endswith("\n") else ""
        result = f"{existing}{separator}{START}\n{new_content}\n{END}\n"
        logger.debug("apply_marker_block: добавлен новый блок в конец")

    return result
