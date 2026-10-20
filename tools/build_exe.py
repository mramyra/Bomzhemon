"""Сборка игры в папку с .exe (PyInstaller). Запускать на Windows из корня проекта:
    python -m tools.build_exe            (или двойной клик по build_exe.bat)
Результат: dist/Bomzhemon/Bomzhemon.exe. Рядом создаются:
    assets/   - сюда кладёшь свои спрайты/шрифты (приоритет над встроенными, пересобирать не нужно)
    saves/    - сохранения
    crash.log - появится, если игра упала (в оконной сборке консоли нет)"""
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    try:
        import PyInstaller  # noqa: F401
    except ImportError:
        sys.exit("Нужен PyInstaller: pip install pyinstaller pygame-ce")
    sep = os.pathsep    # ';' на Windows, ':' на Linux/macOS
    cmd = [sys.executable, "-m", "PyInstaller", "--noconfirm", "--clean", "--onedir", "--windowed", "--name", "Bomzhemon",
           "--add-data", f"data{sep}data", "--add-data", f"maps{sep}maps", "--add-data", f"assets{sep}assets", "main.py"]
    print(" ".join(cmd))
    subprocess.check_call(cmd, cwd=ROOT)
    out = ROOT / "dist" / "Bomzhemon"
    (out / "saves").mkdir(exist_ok=True)
    ext = out / "assets" / "sprites" / "creatures"
    ext.mkdir(parents=True, exist_ok=True)
    names = ROOT / "assets" / "sprites" / "creatures" / "NAMES.txt"
    if names.exists():
        shutil.copy2(names, ext / "NAMES.txt")
    (out / "assets" / "fonts").mkdir(parents=True, exist_ok=True)
    shutil.copy2(ROOT / "README.md", out / "README.md")
    print(f"\nГотово: {out / 'Bomzhemon.exe'}")


if __name__ == "__main__":
    main()
