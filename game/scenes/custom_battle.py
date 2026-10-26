"""Сцена кастомного боя: выбор своего юнита и врага."""
import pygame

from game.scenes.base import Scene
from game.scenes import flow
from game.ui.widgets import INK, PAPER, Menu, text, panel


class CustomBattleScene(Scene):
    def __init__(self, app):
        super().__init__(app)
        self.phase = "player_species"  # player_species -> player_level -> enemy_species -> enemy_level
        self.player_species = None
        self.player_level = 10
        self.enemy_species = None
        self.enemy_level = 10
        self.scroll_offset = 0  # прокрутка для списков
        
        # Для автоскролла и изменения уровня
        self._scroll_timer = 0
        self._scroll_delay = 0.3  # задержка перед началом быстрого скролла
        self._scroll_interval = 0.08  # интервал между шагами скролла
        
        # Меню выбора вида игрока (по алфавиту)
        species_list = sorted(app.data.species.keys())
        self.player_menu = Menu([app.data.species[s]["name"] for s in species_list])
        self.species_list = species_list
        self.player_menu.i = 0  # первый вид по умолчанию
        
        # Меню выбора вида врага (по алфавиту)
        self.enemy_menu = Menu([app.data.species[s]["name"] for s in species_list])

    def handle(self, a):
        if self.phase == "player_species":
            r = self.player_menu.handle(a)
            # Обновляем прокрутку при одиночных нажатиях
            visible_count = 8
            if self.player_menu.i < self.scroll_offset:
                self.scroll_offset = self.player_menu.i
            elif self.player_menu.i >= self.scroll_offset + visible_count:
                self.scroll_offset = self.player_menu.i - visible_count + 1
            
            if r == "back":
                self.app.pop()
            elif r == "ok":
                self.player_species = self.species_list[self.player_menu.i]
                self.phase = "player_level"
                self.scroll_offset = 0
        elif self.phase == "player_level":
            if a == "up":
                self.player_level = min(100, self.player_level + 1)
            elif a == "down":
                self.player_level = max(1, self.player_level - 1)
            elif a == "left":
                self.player_level = max(1, self.player_level - 10)
            elif a == "right":
                self.player_level = min(100, self.player_level + 10)
            elif a == "back":
                self.phase = "player_species"
            elif a == "ok":
                self.phase = "enemy_species"
                self.scroll_offset = 0
        elif self.phase == "enemy_species":
            r = self.enemy_menu.handle(a)
            # Обновляем прокрутку при одиночных нажатиях
            visible_count = 8
            if self.enemy_menu.i < self.scroll_offset:
                self.scroll_offset = self.enemy_menu.i
            elif self.enemy_menu.i >= self.scroll_offset + visible_count:
                self.scroll_offset = self.enemy_menu.i - visible_count + 1
            
            if r == "back":
                self.phase = "player_level"
            elif r == "ok":
                self.enemy_species = self.species_list[self.enemy_menu.i]
                self.phase = "enemy_level"
                self.scroll_offset = 0
        elif self.phase == "enemy_level":
            if a == "up":
                self.enemy_level = min(100, self.enemy_level + 1)
            elif a == "down":
                self.enemy_level = max(1, self.enemy_level - 1)
            elif a == "left":
                self.enemy_level = max(1, self.enemy_level - 10)
            elif a == "right":
                self.enemy_level = min(100, self.enemy_level + 10)
            elif a == "back":
                self.phase = "enemy_species"
            elif a == "ok":
                self._start_battle()
    
    def update(self, dt):
        """Автоскролл при зажатии клавиш и изменение уровня"""
        # Проверяем зажатые клавиши через app.held
        has_held = False
        
        if self.phase in ("player_species", "enemy_species"):
            menu = self.player_menu if self.phase == "player_species" else self.enemy_menu
            
            for action in self.app.held:
                if action in ("up", "down"):
                    has_held = True
                    self._scroll_timer += dt
                    if self._scroll_timer > self._scroll_delay:
                        # После задержки скроллим с интервалом
                        remaining = self._scroll_timer - self._scroll_delay
                        steps = int(remaining / self._scroll_interval)
                        if steps > 0:
                            for _ in range(steps):
                                menu.handle(action)
                                visible_count = 8
                                if menu.i < self.scroll_offset:
                                    self.scroll_offset = menu.i
                                elif menu.i >= self.scroll_offset + visible_count:
                                    self.scroll_offset = menu.i - visible_count + 1
                            self._scroll_timer = self._scroll_delay + (remaining % self._scroll_interval)
                            
        elif self.phase == "player_level":
            for action in self.app.held:
                if action in ("up", "down", "left", "right"):
                    has_held = True
                    self._scroll_timer += dt
                    if self._scroll_timer > self._scroll_delay:
                        remaining = self._scroll_timer - self._scroll_delay
                        steps = int(remaining / self._scroll_interval)
                        if steps > 0:
                            change = 0
                            if action == "up":
                                change = 1
                            elif action == "down":
                                change = -1
                            elif action == "right":
                                change = 10
                            elif action == "left":
                                change = -10
                            for _ in range(steps):
                                self.player_level = max(1, min(100, self.player_level + change))
                            self._scroll_timer = self._scroll_delay + (remaining % self._scroll_interval)
                            
        elif self.phase == "enemy_level":
            for action in self.app.held:
                if action in ("up", "down", "left", "right"):
                    has_held = True
                    self._scroll_timer += dt
                    if self._scroll_timer > self._scroll_delay:
                        remaining = self._scroll_timer - self._scroll_delay
                        steps = int(remaining / self._scroll_interval)
                        if steps > 0:
                            change = 0
                            if action == "up":
                                change = 1
                            elif action == "down":
                                change = -1
                            elif action == "right":
                                change = 10
                            elif action == "left":
                                change = -10
                            for _ in range(steps):
                                self.enemy_level = max(1, min(100, self.enemy_level + change))
                            self._scroll_timer = self._scroll_delay + (remaining % self._scroll_interval)
        
        # Сбрасываем таймер если клавиши отпущены
        if not has_held:
            self._scroll_timer = 0

    def _start_battle(self):
        # Создаём игрока и врага
        from game.battle.creature import Creature
        player = Creature.create(
            self.app.data,
            self.player_species,
            self.player_level,
            flat=True  # для отладки - сбалансированные статы
        )
        enemy = Creature.create(
            self.app.data,
            self.enemy_species,
            self.enemy_level,
            flat=True  # для отладки - сбалансированные статы
        )
        
        # Запускаем бой
        flow.start_custom(
            self.app,
            [player],
            [enemy],
            on_finish=lambda result: self._on_battle_done()
        )

    def _on_battle_done(self):
        self.app.pop()

    def draw(self, surf):
        surf.fill(PAPER)
        
        if self.phase == "player_species":
            text(surf, "Кастомный бой", 20, 14, 20, INK, True)
            text(surf, "Выбери вид своего бойца:", 20, 42, 15)
            panel(surf, (10, 70, 460, 260))
            
            # Рисуем список с прокруткой
            visible_count = 8
            start_idx = self.scroll_offset
            end_idx = min(start_idx + visible_count, len(self.species_list))
            
            for k in range(start_idx, end_idx):
                y = 80 + (k - start_idx) * 30
                item_idx = k
                if item_idx == self.player_menu.i:
                    pygame.draw.rect(surf, (226, 232, 214), (10, y - 2, 460, 26))
                text(surf, self.player_menu.items[item_idx], 20, y, 15)
            
            # Показываем индикатор прокрутки
            if len(self.species_list) > visible_count:
                text(surf, f"{self.player_menu.i + 1}/{len(self.species_list)}", 20, 320, 12, (110, 110, 110))
            
            text(surf, "← Назад  ▲▼ Выбор  → Выбрать уровень", 20, 346, 13, INK)
            
        elif self.phase == "player_level":
            text(surf, "Кастомный бой", 20, 14, 20, INK, True)
            player_name = self.app.data.species[self.player_species]["name"]
            text(surf, f"Твой боец: {player_name}", 20, 42, 15)
            text(surf, "Выбери уровень:", 20, 62, 15)
            panel(surf, (10, 90, 460, 240))
            # Большой счётчик уровня
            text(surf, str(self.player_level), 240, 160, 60, INK, True)
            text(surf, "▲▼ ±1  ←→ ±10", 240, 240, 14, (110, 110, 110))
            text(surf, "← Назад  → Выбрать врага", 20, 346, 13, INK)
            
        elif self.phase == "enemy_species":
            text(surf, "Кастомный бой", 20, 14, 20, INK, True)
            text(surf, "Выбери вид врага:", 20, 42, 15)
            panel(surf, (10, 70, 460, 260))
            
            # Рисуем список с прокруткой
            visible_count = 8
            start_idx = self.scroll_offset
            end_idx = min(start_idx + visible_count, len(self.species_list))
            
            for k in range(start_idx, end_idx):
                y = 80 + (k - start_idx) * 30
                item_idx = k
                if item_idx == self.enemy_menu.i:
                    pygame.draw.rect(surf, (226, 232, 214), (10, y - 2, 460, 26))
                text(surf, self.enemy_menu.items[item_idx], 20, y, 15)
            
            # Показываем индикатор прокрутки
            if len(self.species_list) > visible_count:
                text(surf, f"{self.enemy_menu.i + 1}/{len(self.species_list)}", 20, 320, 12, (110, 110, 110))
            
            text(surf, "← Назад  ▲▼ Выбор  → Выбрать уровень", 20, 346, 13, INK)
            
        elif self.phase == "enemy_level":
            text(surf, "Кастомный бой", 20, 14, 20, INK, True)
            enemy_name = self.app.data.species[self.enemy_species]["name"]
            text(surf, f"Враг: {enemy_name}", 20, 42, 15)
            text(surf, "Выбери уровень:", 20, 62, 15)
            panel(surf, (10, 90, 460, 240))
            # Большой счётчик уровня
            text(surf, str(self.enemy_level), 240, 160, 60, INK, True)
            text(surf, "▲▼ ±1  ←→ ±10", 240, 240, 14, (110, 110, 110))
            text(surf, "← Назад  → Начать бой", 20, 346, 13, INK)
