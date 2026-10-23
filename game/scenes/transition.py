"""Затемнение при переходе между локациями: экран темнеет, в середине вызывается on_mid (смена карты), потом светлеет."""
import pygame

from game.scenes.base import Scene


class TransitionScene(Scene):
    transparent = True
    blocks_console = True

    def __init__(self, app, on_mid, duration=0.55):
        super().__init__(app)
        self.on_mid, self.duration, self.t, self.mid_done = on_mid, duration, 0.0, False

    def update(self, dt):
        self.t += dt
        if not self.mid_done and self.t >= self.duration / 2:
            self.mid_done = True
            self.on_mid()
        if self.t >= self.duration:
            if not self.mid_done:       # на случай огромного шага времени
                self.mid_done = True
                self.on_mid()
            self.app.pop()

    def draw(self, surf):
        half = self.duration / 2
        k = self.t / half if self.t < half else max(0.0, 2 - self.t / half)
        overlay = pygame.Surface((480, 320), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, int(255 * min(1.0, k))))
        surf.blit(overlay, (0, 0))
