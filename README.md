# Бомжемон

Покемоны, только ты бомж, а вместо покебола - картонная коробка.

    pip install -r requirements.txt
    python main.py

Управление: стрелки/WASD, Z/Enter/Space - ок, X/Esc/Backspace - назад.

## Управление
Стрелки/WASD - ходить, Z/Enter/Space - действие, X/Esc/Backspace - назад (на карте открывает меню).
F11 или Alt+Enter - полный экран, F10 - режим масштаба (целый множитель с полями / во весь экран).

## Тесты (без pygame)
    python -m tests.run_tests         # данные, типы, баланс, бой, ловля, эволюции, крафт, сохранения, карта
    python -m tests.smoke_ui          # прогон сцен и прогулок по карте на заглушке pygame
    python -m tools.type_report       # таблица типов
    python -m tools.balance_report    # нормированный турнир + лестница стадий (после правок статов)
    python -m tools.make_placeholder_map [seed]   # пересобрать карту-заглушку и тайлсет

## Куда класть файлы
    data/*.json                          весь контент: существа, приёмы, типы, предметы, тренеры, крафт, районы
    assets/sprites/creatures/<id>.png    спрайт существа (id = ключ в species.json, напр. rat.png). Рекомендуем 96x96, прозрачный фон
    assets/sprites/creatures/<id>_back.png  со спины (необязательно, иначе зеркалится передний)
    assets/tiles/*.png                   тайлсеты для карты (тайл 32x32)
    assets/fonts/*.ttf                   шрифт игры (берётся первый по алфавиту; нужна кириллица)
    assets/audio/                        музыка и звуки (подключим позже)
    maps/dump.tmj                        карта района из Tiled (JSON)
    saves/                               сохранения (создаются сами)

## Структура кода
    game/core/     окно, полный экран, стек сцен, загрузка данных
    game/battle/   Creature и движок боя (без pygame, возвращает события)
    game/world/    загрузчик карты Tiled (без pygame)
    game/systems/  эволюции, крафт, состояние игрока, сохранения
    game/ui/       виджеты и спрайты
    game/scenes/   title, world (карта + меню паузы), battle_scene, screens (команда/сумка/декс/крафт), debug_hub
    tools/ tests/  отчёты по балансу, генератор карты, тесты
    prototype_v0/  первый быстрый прототип (для истории)

## Как добавлять контент
- Существо: запись в `data/species.json` + спрайт `assets/sprites/creatures/<id>.png`.
- Приём: `data/moves.json` (эффекты: status / confuse / flinch / stat). Эволюция: поле `evolutions` (level | item). Крафт: `data/fusions.json`.
- Тренер/лидер: `data/trainers.json`, на карте - объект типа trainer/leader с `trainer_id`.
- Карта в Tiled: слой `ground`, группа объектов `objects` (player_start, barrel, dumpster, item_spot, trainer, leader),
  свойства тайлов `solid` и `encounter`. Tile Layer Format = CSV. Подробности в game/world/mapdata.py.

## План
Неделя 2: (сделано) карта-заглушка, ходьба, баки, бочка, предметы по сиду, тренеры, лидер, окно команды (опыт, статы, приёмы). Дальше: взгляд тренеров, свой тайлсет.
Неделя 3: контент района и лидера, экран замены приёма, баланс.
Неделя 4: полировка, сборка .exe (PyInstaller), звук и спрайты.
