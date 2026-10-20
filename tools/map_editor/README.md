# Редактор карт Бомжемон

## Запуск

**Важно**: Редактор должен работать через HTTP сервер, а не напрямую через `file://` (из-за CORS ограничений браузера).

### Способ 1: Через Python скрипт (рекомендуется)

```bash
cd tools/map_editor
python run_server.py
```

Или на Windows:
```bash
run_server.bat
```

Браузер откроется автоматически по адресу `http://localhost:8000/bomzhemon_map_editor.html`

### Способ 2: Любой локальный сервер

```bash
cd tools/map_editor
python -m http.server 8000
```

Или с Node.js:
```bash
cd tools/map_editor
npx serve
```

Затем откройте `http://localhost:8000/bomzhemon_map_editor.html` в браузере.

## Особенности

- Автоматическая загрузка предметов из `data/items.json`
- Быстрый выбор карт из папки `maps/`
- Указание конкретного предмета для `item_spot`
- Drag & drop для карт и тайлсетов
- Автосохранение в localStorage
