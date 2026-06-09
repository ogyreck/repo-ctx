# repo-ctx

CLI-утилита для централизованного развёртывания стандартов AI-агентной разработки в несколько git-репозиториев.

Читает «standards»-репозиторий как единый источник правды и раскатывает контекст, команды, описания субагентов и конфигурацию MCP через систему адаптеров. Поддерживает идемпотентные обновления через маркер-блоки, не затрагивая локальные правки пользователя.

## Возможности

- **`repo-ctx init`** — первичная раскатка standards в целевой репозиторий
- **`repo-ctx sync`** — обновление с сохранением локальных правок
- **`repo-ctx status`** — текущее состояние и обнаружение дрейфа
- Архитектура адаптеров: флаг `--target` выбирает harness (по умолчанию `claude-code`)
- Эвристическое определение профиля (`microservice`, `ansible-role`, `default`)
- Маркер-мёрж: управляемый контент обёртывается в `<!-- repo-ctx:managed:* -->`
- Идемпотентность: повторный запуск не плодит дубликаты
- Только Python 3 stdlib — без внешних зависимостей, работает в air-gapped окружении

## Установка

```bash
git clone https://github.com/your-org/repo-ctx.git
cd repo-ctx
# Запуск напрямую из исходников:
PYTHONPATH=src python3 -m repo_ctx --help

# Или установка через pip (editable mode):
pip install -e .
```

> Зависимостей нет — только Python 3.9+.

## Быстрый старт

```bash
# Инициализировать целевой репозиторий
repo-ctx init /path/to/standards --dest /path/to/my-service

# Обновить standards (сохраняет локальные правки)
repo-ctx sync /path/to/standards --dest /path/to/my-service

# Показать состояние и дрейф
repo-ctx status --dest /path/to/my-service
```

## Примеры команд

### `repo-ctx init`

```
repo-ctx init /path/to/standards \
    --dest /path/to/target-repo \
    --target claude-code \
    --profile microservice
```

Флаги:
- `source` — путь к standards-репозиторию (обязательный позиционный аргумент)
- `--dest DIR` — целевой репозиторий (по умолчанию: `.`)
- `--target NAME` — имя адаптера (по умолчанию: `claude-code`)
- `--profile NAME` — профиль; если не указан, определяется автоматически
- `--dry-run` — показать, что было бы сделано, без записи файлов

### `repo-ctx sync`

```
repo-ctx sync /path/to/standards --dest /path/to/target-repo
```

### `repo-ctx status`

```
repo-ctx status --dest /path/to/target-repo
```

Пример вывода:
```
Профиль:         microservice
Sources:         /path/to/standards
Применён коммит: abc1234567ef
Дата применения: 2026-06-09T20:00:00+00:00
Управляемых файлов: 3

✓ Дрейфа нет
```

## Структура standards-репозитория

```
standards/
├── profiles/
│   └── microservice/
│       └── profile.json          # описание профиля
├── context/
│   └── gitlab-ce-conventions.md  # фрагменты памяти (→ CLAUDE.md)
├── commands/
│   └── ci-kaniko.md              # команды (→ .claude/commands/)
├── agents/
│   └── (*.md)                    # описания агентов (→ .claude/agents/)
└── mcp/
    └── (*.json)                  # шаблоны MCP-серверов (→ .mcp.json)
```

## Формат `profile.json`

```json
{
  "name": "microservice",
  "description": "Профиль для микросервисов с CI/CD через GitLab.",
  "context": ["gitlab-ce-conventions"],
  "commands": ["ci-kaniko"],
  "agents": [],
  "mcp": []
}
```

| Поле | Тип | Описание |
|------|-----|----------|
| `name` | string | Имя профиля (должно совпадать с именем директории) |
| `description` | string | Человекочитаемое описание |
| `context` | string[] | Имена файлов из `context/` (без `.md`) — сливаются в memory-файл |
| `commands` | string[] | Имена файлов из `commands/` (без `.md`) |
| `agents` | string[] | Имена файлов из `agents/` (без `.md`) |
| `mcp` | string[] | Имена JSON-файлов из `mcp/` (без `.json`) |

## Как добавить новый адаптер

Новый target (например, `cursor`) создаётся в три шага:

### 1. Создайте модуль адаптера

```python
# src/repo_ctx/adapters/cursor.py
from repo_ctx.core.adapter import Adapter
from repo_ctx.core.registry import register_adapter
import os, shutil

class CursorAdapter(Adapter):
    def memory_targets(self, profile):
        # Cursor читает правила из .cursorrules
        return {ctx: ".cursorrules" for ctx in profile.get("context", [])}

    def render_commands(self, source_dir, dest_root, dry_run):
        # Cursor не имеет команд-промптов — возвращаем пустой список
        return []

    def render_agents(self, source_dir, dest_root, dry_run):
        return []

    def merge_mcp(self, mcp_templates, dest_root, dry_run):
        # Аналогично claude_code — мёрж по ключам в .mcp.json
        # (можно переиспользовать логику из ClaudeCodeAdapter)
        return []

register_adapter("cursor", CursorAdapter)
```

### 2. Импортируйте адаптер в `cli.py`

В функции `_load_adapters()` добавьте строку:

```python
def _load_adapters() -> None:
    import repo_ctx.adapters.claude_code  # noqa: F401
    import repo_ctx.adapters.cursor       # noqa: F401  ← добавить
```

### 3. Используйте новый адаптер

```bash
repo-ctx init /path/to/standards --dest /path/to/project --target cursor
```

> **Принцип:** ядро (`core/`) не знает о конкретных адаптерах. Адаптер регистрирует себя в реестре при импорте — это единственная точка интеграции.

## Запуск тестов

```bash
PYTHONPATH=src python3 -m unittest discover tests/ -v
```

Покрытие:
- `test_merger.py` — маркер-мёрж, идемпотентность, roundtrip (15 тестов)
- `test_manifest.py` — load/save/dry_run манифеста (6 тестов)
- `test_profile.py` — эвристика, load, list (10 тестов)
- `test_registry.py` — регистрация, поиск, ошибки (6 тестов)
- `test_mcp.py` — мёрж MCP-серверов (7 тестов)
- `test_init_sync_idempotency.py` — end-to-end без сети (10 тестов)

Итого: **54 теста**, только stdlib, без моков файловой системы.

## Архитектура

```
cli.py → core/ ← adapters/
```

- `core/` — чистая бизнес-логика, не знает об адаптерах
- `adapters/` — конкретные реализации; регистрируются при импорте
- `cli.py` — только разбор аргументов и делегирование core

Подробнее: [`.ai-factory/ARCHITECTURE.md`](.ai-factory/ARCHITECTURE.md)
