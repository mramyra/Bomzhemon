"""Мелкие UI-кирпичики: шрифты, рамки, текст, полоска HP, меню."""
from pathlib import Path

import pygame

INK = (34, 34, 48)
PAPER = (246, 244, 236)
PANEL = (255, 255, 255)
SHADE = (214, 210, 196)
ACCENT = (200, 70, 60)
GREEN, YELLOW, RED = (80, 190, 90), (230, 190, 50), (220, 70, 60)

FONT_DIR = Path(__file__).resolve().parents[2] / "assets" / "fonts"
_fonts = {}


def font(size=16, bold=False):
    key = (size, bold)
    if key not in _fonts:
        ttf = sorted(FONT_DIR.glob("*.ttf"))
        if ttf:
            _fonts[key] = pygame.font.Font(str(ttf[0]), size)
        else:   # на Windows есть segoeui/arial с кириллицей
            _fonts[key] = pygame.font.SysFont("segoeui,arial,calibri,dejavusans,liberationsans", size, bold=bold)
    return _fonts[key]


def text(surf, s, x, y, size=16, color=INK, bold=False):
    surf.blit(font(size, bold).render(str(s), True, color), (x, y))


def wrap(s, width, size=16):
    f, lines, cur = font(size), [], ""
    for w in str(s).split(" "):
        t = (cur + " " + w).strip()
        if f.size(t)[0] > width and cur:
            lines.append(cur)
            cur = w
        else:
            cur = t
    return lines + [cur]


def panel(surf, rect, fill=PANEL):
    pygame.draw.rect(surf, fill, rect, border_radius=6)
    pygame.draw.rect(surf, INK, rect, 2, border_radius=6)


def hp_bar(surf, x, y, w, hp, mx, h=7):
    frac = max(0.0, min(1.0, hp / mx)) if mx else 0
    pygame.draw.rect(surf, SHADE, (x, y, w, h), border_radius=3)
    col = GREEN if frac > 0.5 else YELLOW if frac > 0.2 else RED
    if frac > 0:
        pygame.draw.rect(surf, col, (x, y, max(2, int(w * frac)), h), border_radius=3)
    pygame.draw.rect(surf, INK, (x, y, w, h), 1, border_radius=3)


def arrow(surf, x, y, size=8):
    pygame.draw.polygon(surf, INK, [(x, y), (x, y + size * 1.5), (x + size, y + size * 0.75)])


class Menu:
    """Вертикальное или сеточное меню с курсором. handle() возвращает 'ok' / 'back' / None."""

    def __init__(self, items, cols=1):
        self.items, self.cols, self.i = list(items), cols, 0

    def handle(self, a):
        n, c = len(self.items), self.cols
        if a == "up":
            self.i = self.i - c if self.i - c >= 0 else (n - 1 if c == 1 else self.i)
        elif a == "down":
            self.i = self.i + c if self.i + c < n else (0 if c == 1 else self.i)
        elif a == "left" and c > 1 and self.i % c > 0:
            self.i -= 1
        elif a == "right" and c > 1 and self.i % c < c - 1 and self.i + 1 < n:
            self.i += 1
        elif a in ("ok", "back"):
            return a
        return None

    def draw(self, surf, x, y, col_w=200, row_h=24, size=16):
        for k, item in enumerate(self.items):
            cx, cy = x + (k % self.cols) * col_w, y + (k // self.cols) * row_h
            if k == self.i:
                arrow(surf, cx, cy + 3, 7)
            text(surf, item, cx + 16, cy, size)
