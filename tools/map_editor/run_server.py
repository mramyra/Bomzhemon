#!/usr/bin/env python3
"""Запуск локального HTTP сервера для редактора карт (обход CORS)."""
import http.server
import socketserver
import webbrowser
import os
import sys

PORT = 8000
EDITOR_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(os.path.dirname(EDITOR_DIR))

class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=PROJECT_ROOT, **kwargs)

def main():
    os.chdir(PROJECT_ROOT)
    with socketserver.TCPServer(("", PORT), Handler) as httpd:
        url = f"http://localhost:{PORT}/tools/map_editor/bomzhemon_map_editor.html"
        print(f"🗺️  Редактор карт запущен: {url}")
        print(f"📁 Корень проекта: {PROJECT_ROOT}")
        print(f"⏹️  Нажмите Ctrl+C для остановки")
        webbrowser.open(url)
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n👋 Сервер остановлен")

if __name__ == "__main__":
    main()
