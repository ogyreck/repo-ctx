"""Иерархия исключений repo-ctx."""


class RepoctxError(Exception):
    """Базовое исключение для всех ошибок repo-ctx."""


class ProfileNotFoundError(RepoctxError):
    """Профиль не найден в standards-репозитории."""


class AdapterNotFoundError(RepoctxError):
    """Запрошенный адаптер (target) не зарегистрирован."""


class SourceNotFoundError(RepoctxError):
    """Standards-репозиторий (source) не найден или недоступен."""


class ManifestError(RepoctxError):
    """Ошибка чтения или записи манифеста .repo-ctx.json."""
