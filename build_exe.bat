@echo off
chcp 65001 >nul
pip install pyinstaller pygame-ce
python -m tools.build_exe
pause
