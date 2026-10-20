"""Пути: ресурсы (data/maps/assets) и папка для записи (saves). Работает и из исходников, и из собранного .exe (PyInstaller).
Папка assets рядом с .exe имеет приоритет над встроенной - так можно подкладывать спрайты, не пересобирая игру."""
import sys
from pathlib import Path


def compute_paths(frozen, meipass, executable, source_root):
    """-> (папка ресурсов, папка приложения). Чистая функция - проверяется тестами."""
    if frozen:
        return (Path(meipass) if meipass else Path(executable).parent), Path(executable).parent
    return Path(source_root), Path(source_root)


RESOURCES, APP_DIR = compute_paths(getattr(sys, "frozen", False), getattr(sys, "_MEIPASS", None), sys.executable,
                                   Path(__file__).resolve().parents[2])
SAVE_DIR = APP_DIR / "saves"
CRASH_LOG = APP_DIR / "crash.log"


def asset(rel):
    """Файл рядом с приложением, если он есть, иначе встроенный."""
    external = APP_DIR / rel
    return external if external.exists() else RESOURCES / rel
