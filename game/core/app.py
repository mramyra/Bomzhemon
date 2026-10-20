"""Приложение: окно, полный экран, стек сцен, главный цикл."""

import pygame

from game.core.data import GameData
from game.core.events import EventBus
from game.core.input import key_action

INTERNAL = (480, 320)   # внутреннее разрешение (3:2); дальше масштабируется на окно/экран
WINDOW_SCALE = 2


class App:
    def __init__(self):
        pygame.init()
        pygame.display.set_caption("Бомжемон")
        self.fullscreen = False
        self.integer_scale = True       # True: целый множитель + чёрные поля (чёткие пиксели); False: во весь экран с сохранением пропорций
        self._set_mode()
        self.canvas = pygame.Surface(INTERNAL)
        self.clock = pygame.time.Clock()
        self.data = GameData()
        self.events = EventBus()        # шина событий (звук и эффекты подписываются здесь)
        self.state = None               # PlayerState, появляется после новой игры / загрузки
        self.stack = []
        self.held = set()               # удерживаемые направления (для ходьбы)

    # ---- окно
    def _set_mode(self):
        if self.fullscreen:
            self.window = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
        else:
            self.window = pygame.display.set_mode((INTERNAL[0] * WINDOW_SCALE, INTERNAL[1] * WINDOW_SCALE), pygame.RESIZABLE)

    def toggle_fullscreen(self):
        self.fullscreen = not self.fullscreen
        self._set_mode()

    def _present(self):
        win = pygame.display.get_surface()
        ww, wh = win.get_size()
        sc = min(ww / INTERNAL[0], wh / INTERNAL[1])
        if self.integer_scale and sc >= 1:
            sc = int(sc)
        size = (int(INTERNAL[0] * sc), int(INTERNAL[1] * sc))
        img = pygame.transform.scale(self.canvas, size) if self.integer_scale else pygame.transform.smoothscale(self.canvas, size)
        win.fill((0, 0, 0))
        win.blit(img, ((ww - size[0]) // 2, (wh - size[1]) // 2))
        pygame.display.flip()

    # ---- стек сцен
    def push(self, scene):
        self.stack.append(scene)

    def pop(self):
        if self.stack:
            self.stack.pop()

    def replace(self, scene):
        self.stack = [scene]

    def quit(self):
        """Выйти из игры: главный цикл завершится."""
        self.stack.clear()

    def run(self):
        while self.stack:
            dt = min(self.clock.tick(60) / 1000, 0.1)
            for e in pygame.event.get():
                if e.type == pygame.QUIT:
                    from game.scenes.exit_flow import request_quit
                    request_quit(self)
                    continue
                if e.type == pygame.KEYDOWN and (e.key == pygame.K_F11 or (e.key == pygame.K_RETURN and e.mod & pygame.KMOD_ALT)):
                    self.toggle_fullscreen()
                    continue
                if e.type == pygame.KEYDOWN and e.key == pygame.K_F10:
                    self.integer_scale = not self.integer_scale
                    continue
                top = self.stack[-1] if self.stack else None
                if top is not None and getattr(top, "wants_text", False):   # консоль: сырой ввод текста
                    if e.type == pygame.KEYDOWN:
                        top.on_key(e)
                    continue
                if e.type == pygame.KEYDOWN and e.key in (pygame.K_BACKQUOTE, pygame.K_F1) and top is not None and not getattr(top, "blocks_console", False):
                    from game.scenes.console_scene import ConsoleScene
                    self.held.clear()
                    self.push(ConsoleScene(self))
                    continue
                a, down = key_action(e)
                if a in ("up", "down", "left", "right"):
                    (self.held.add if down else self.held.discard)(a)
                if a and down and self.stack:
                    self.stack[-1].handle(a)
            if not self.stack:
                break
            self.stack[-1].update(dt)
            if self.state:
                self.state.play_seconds += dt
            start = len(self.stack) - 1
            while start > 0 and self.stack[start].transparent:
                start -= 1
            for s in self.stack[start:]:
                s.draw(self.canvas)
            self._present()
        pygame.quit()
