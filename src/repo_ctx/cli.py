"""CLI точка входа: разбор аргументов и делегирование core.

Содержит только presentation-логику — никакой бизнес-логики.
"""

import argparse
import logging
import sys

from repo_ctx.exceptions import RepoctxError

logger = logging.getLogger(__name__)


def _setup_logging(log_level: str) -> None:
    """Настраивает logging с указанным уровнем."""
    numeric_level = getattr(logging, log_level.upper(), None)
    if not isinstance(numeric_level, int):
        print(f"Неверный уровень логирования: {log_level}", file=sys.stderr)
        sys.exit(1)
    logging.basicConfig(
        level=numeric_level,
        format="%(levelname)s %(name)s: %(message)s",
    )
    logger.debug("Логирование настроено на уровень %s", log_level.upper())


def _load_adapters() -> None:
    """Импортирует все адаптеры для активации их регистрации в реестре."""
    import repo_ctx.adapters.claude_code  # noqa: F401


def _make_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="repo-ctx",
        description="Централизованное развёртывание стандартов AI-разработки в git-репозитории.",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        metavar="LEVEL",
        help="Уровень логирования: DEBUG, INFO, WARNING, ERROR (по умолчанию: INFO)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Выполнить все проверки без записи файлов",
    )

    sub = parser.add_subparsers(dest="command", metavar="команда")
    sub.required = True

    # repo-ctx init
    init_p = sub.add_parser("init", help="Первичная раскатка standards в репозиторий")
    init_p.add_argument("source", help="Путь к standards-репозиторию")
    init_p.add_argument(
        "--dest",
        default=".",
        metavar="DIR",
        help="Целевой репозиторий (по умолчанию: текущая директория)",
    )
    init_p.add_argument(
        "--target",
        default="claude-code",
        metavar="NAME",
        help="Имя адаптера (target). По умолчанию: claude-code",
    )
    init_p.add_argument(
        "--profile",
        default=None,
        metavar="NAME",
        help="Имя профиля (по умолчанию: определяется автоматически)",
    )
    init_p.add_argument("--dry-run", action="store_true", help="Без записи файлов")

    # repo-ctx sync
    sync_p = sub.add_parser("sync", help="Обновление standards с сохранением локальных правок")
    sync_p.add_argument("source", help="Путь к standards-репозиторию")
    sync_p.add_argument(
        "--dest",
        default=".",
        metavar="DIR",
        help="Целевой репозиторий (по умолчанию: текущая директория)",
    )
    sync_p.add_argument(
        "--target",
        default="claude-code",
        metavar="NAME",
        help="Имя адаптера (target). По умолчанию: claude-code",
    )
    sync_p.add_argument("--dry-run", action="store_true", help="Без записи файлов")

    # repo-ctx status
    status_p = sub.add_parser("status", help="Отображение текущего состояния и дрейфа")
    status_p.add_argument(
        "--dest",
        default=".",
        metavar="DIR",
        help="Целевой репозиторий (по умолчанию: текущая директория)",
    )

    return parser


def _cmd_init(args: argparse.Namespace) -> None:
    from repo_ctx.core.engine import init_repo
    from repo_ctx.core.registry import get_adapter

    adapter_cls = get_adapter(args.target)
    adapter = adapter_cls()
    logger.debug("init: адаптер=%s, source=%s, dest=%s", args.target, args.source, args.dest)

    result = init_repo(
        args.source,
        args.dest,
        adapter,
        profile_name=args.profile,
        dry_run=args.dry_run,
    )

    dry_tag = " [dry-run]" if args.dry_run else ""
    print(f"✓ init завершён{dry_tag}")
    print(f"  Профиль: {result['profile']}")
    print(f"  Управляемых файлов: {len(result['managed_files'])}")
    if result.get("source_commit"):
        print(f"  Коммит standards: {result['source_commit'][:12]}")
    for f in result["managed_files"]:
        print(f"    • {f}")


def _cmd_sync(args: argparse.Namespace) -> None:
    from repo_ctx.core.engine import sync_repo
    from repo_ctx.core.registry import get_adapter

    adapter_cls = get_adapter(args.target)
    adapter = adapter_cls()
    logger.debug("sync: адаптер=%s, source=%s, dest=%s", args.target, args.source, args.dest)

    result = sync_repo(
        args.source,
        args.dest,
        adapter,
        dry_run=args.dry_run,
    )

    dry_tag = " [dry-run]" if args.dry_run else ""
    print(f"✓ sync завершён{dry_tag}")
    print(f"  Профиль: {result['profile']}")
    print(f"  Управляемых файлов: {len(result['managed_files'])}")
    if result.get("source_commit"):
        print(f"  Коммит standards: {result['source_commit'][:12]}")


def _cmd_status(args: argparse.Namespace) -> None:
    from repo_ctx.core.engine import get_status

    logger.debug("status: dest=%s", args.dest)
    status = get_status(args.dest)

    if not status.get("initialized"):
        print("Репозиторий не инициализирован. Выполните: repo-ctx init <source>")
        return

    print(f"Профиль:         {status['profile']}")
    print(f"Sources:         {status['source']}")
    print(f"Применён коммит: {status.get('applied_commit') or '(неизвестно)'}")
    print(f"Дата применения: {status.get('timestamp') or '(неизвестно)'}")
    print(f"Управляемых файлов: {len(status['managed_files'])}")

    if status["drifted"]:
        print(f"\n⚠ Дрейф обнаружен ({len(status['drifted'])} файлов):")
        for f in status["drifted"]:
            print(f"  ✗ {f}")
    else:
        print("\n✓ Дрейфа нет")


def main(argv: list[str] | None = None) -> None:
    """Главная функция CLI. Ловит RepoctxError и выходит с кодом 1."""
    parser = _make_parser()
    args = parser.parse_args(argv)

    _setup_logging(args.log_level)
    _load_adapters()

    logger.debug("Команда: %s, аргументы: %s", args.command, vars(args))

    try:
        if args.command == "init":
            _cmd_init(args)
        elif args.command == "sync":
            _cmd_sync(args)
        elif args.command == "status":
            _cmd_status(args)
        else:
            parser.print_help()
            sys.exit(1)
    except RepoctxError as exc:
        print(f"Ошибка: {exc}", file=sys.stderr)
        logger.debug("RepoctxError", exc_info=True)
        sys.exit(1)
