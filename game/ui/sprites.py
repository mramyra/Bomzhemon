"""Спрайты существ. Есть assets/sprites/creatures/<id>.png - берём его, иначе рисуем заглушку по типам."""
import pygame

from game.core import paths

from game.ui.widgets import INK, font

REL = "assets/sprites/creatures/"
_cache = {}


def _placeholder(data, sid, size):
    sp = data.species[sid]
    c1 = tuple(data.types[sp["types"][0]]["color"])
    c2 = tuple(data.types[sp["types"][-1]]["color"])
    s = pygame.Surface((size, size), pygame.SRCALPHA)
    dark = tuple(max(0, v - 70) for v in c1)
    pygame.draw.ellipse(s, c2, (size * .62, size * .45, size * .34, size * .22))      # хвост / "второй тип"
    pygame.draw.ellipse(s, c1, (size * .12, size * .38, size * .66, size * .52))      # тело
    pygame.draw.ellipse(s, dark, (size * .12, size * .38, size * .66, size * .52), 2)
    pygame.draw.circle(s, c1, (int(size * .36), int(size * .34)), int(size * .2))     # голова
    pygame.draw.circle(s, dark, (int(size * .36), int(size * .34)), int(size * .2), 2)
    for ex in (.29, .43):
        pygame.draw.circle(s, INK, (int(size * ex), int(size * .32)), max(2, size // 28))
    abbr = sp["name"][:2].upper()
    t = font(max(10, size // 7), True).render(abbr, True, INK)
    s.blit(t, (size * .4 - t.get_width() / 2, size * .62))
    return s


def creature_sprite(data, sid, size, back=False):
    """back=True: спрайт со спины (<id>_back.png); если файла нет - зеркало переднего."""
    key = (sid, size, back)
    if key not in _cache:
        p, pb = paths.asset(f"{REL}{sid}.png"), paths.asset(f"{REL}{sid}_back.png")
        if back and pb.exists():
            img = pygame.transform.smoothscale(pygame.image.load(str(pb)).convert_alpha(), (size, size))
        else:
            img = pygame.transform.smoothscale(pygame.image.load(str(p)).convert_alpha(), (size, size)) if p.exists() else _placeholder(data, sid, size)
            if back:
                img = pygame.transform.flip(img, True, False)
        _cache[key] = img
    return _cache[key]
