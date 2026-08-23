# Model/Poetics.py
# Свод правил о смысле стиха (resources/poetics.md) для системного промпта.
# Вынесен из генератора: тот же текст нужен любому провайдеру, а не только Claude.
import sys
from pathlib import Path

_cache = None


def poetics_path() -> Path:
    if getattr(sys, "frozen", False):            # сборка PyInstaller
        root = Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
    else:
        root = Path(__file__).resolve().parents[2]   # корень репозитория
    return root / "resources" / "poetics.md"


def poetics_text() -> str:
    """Текст свода. Пустая строка, если файла нет — генерация не должна падать."""
    global _cache
    if _cache is None:
        try:
            _cache = poetics_path().read_text(encoding="utf-8").strip()
        except OSError:
            _cache = ""
    return _cache
