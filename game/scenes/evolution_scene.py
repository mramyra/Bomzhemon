"""Экран эволюции: «Что? X эволюционирует!» -> мерцание силуэтов (всё чаще) -> вспышка -> новая форма -> «Поздравляем!».
Заготовка анимации - рисуется кодом из data/animations.json. Свои кадры: assets/anim/evolution/ (см. README.txt там же).
События для звука: evolution_start / _intro / _flicker / _burst / _reveal / _cancelled / _done (app.events)."""
import math

import pygame

from game.core import paths
from game.scenes.base import Scene
from game.systems import evolution
from game.systems.evolution_anim import Particles, Timeline, flicker_show_new, make_config, pulse_scale
from game.ui.sprites import creature_sprite
from game.ui.widgets import INK, panel, text, wrap, arrow

CX, CY = 240, 112
BG = (14, 16, 30)


class EvolutionScene(Scene):
    blocks_console = True

    def __init__(self, app, creature, into_id, on_done=None, cancellable=True, cause="level", preview=False):
        """cancellable: X отменяет эволюцию до вспышки (для уровня - да, для предмета/обмена - нет).
        preview: только показать анимацию, существо не меняется (консоль: evoanim)."""
        super().__init__(app)
        d = app.data
        self.c, self.into, self.on_done = creature, into_id, on_done
        self.cancellable, self.cause, self.preview = cancellable, cause, preview
        self.old_id, self.old_name = creature.species_id, creature.name
        self.new_name = d.species[into_id]["name"]
        self.cfg = make_config(d.animations.get("evolution"))
        self.tl = Timeline(self.cfg)
        self.particles = Particles(seed=hash(self.old_id + into_id) & 0xFFFF)
        self.stage = "anim"             # anim | message | cancelled
        self.committed = False
        self.text = f"Что? {self.old_name} эволюционирует!"
        self.time, self.evolved = 0.0, False
        self._sil = {}
        self.frames = self._load_frames()
        self._emit("evolution_start", creature=creature, into=into_id, cause=cause)

    # ------------------------------------------------------------ события и своя анимация
    def _emit(self, name, **kw):
        bus = getattr(self.app, "events", None)
        if bus:
            bus.emit(name, **kw)

    def _load_frames(self):
        """PNG-кадры из assets/anim/evolution/<старый>_<новый>/ или default/ (если есть)."""
        for rel in (f"assets/anim/evolution/{self.old_id}_{self.into}", "assets/anim/evolution/default"):
            folder = paths.asset(rel)
            if folder.is_dir():
                files = sorted(folder.glob("*.png"))
                if files:
                    try:
                        return [pygame.image.load(str(f)).convert_alpha() for f in files]
                    except pygame.error:
                        return None
        return None

    # ------------------------------------------------------------ логика
    def update(self, dt):
        self.time += dt
        if self.stage != "anim":
            return
        for name in self.tl.update(dt):
            self._emit(f"evolution_{name}", creature=self.c, into=self.into)
            if name == "reveal":
                self._commit()
        if self.cfg["particles"]:
            ph = self.tl.name
            rate = {"intro": 0, "flicker": 6 + 50 * self.tl.progress, "burst": 120, "reveal": 20 * (1 - self.tl.progress)}[ph]
            self.particles.update(dt, rate)
        if self.tl.done:
            self.stage = "message"
            self.text = f"Поздравляем! {self.old_name} эволюционировал в {self.new_name}!" if not self.preview else f"(Просмотр) {self.old_name} -> {self.new_name}."

    def _commit(self):
        if self.committed:
            return
        self.committed = True
        if not self.preview:
            evolution.apply(self.app.data, self.app.state, self.c, self.into)
            self.evolved = True

    def _cancel(self):
        if self.cause == "level" and not self.preview:
            self.c.declined_evolution_level = self.c.level
        self.stage = "cancelled"
        self.text = f"Что? {self.old_name} перестал эволюционировать!"
        self._emit("evolution_cancelled", creature=self.c, into=self.into)

    def handle(self, a):
        if self.stage == "anim":
            if a == "back" and self.cancellable and self.tl.can_cancel():
                self._cancel()
        elif a in ("ok", "back"):
            self._emit("evolution_done", creature=self.c, evolved=self.evolved)
            self.app.pop()
            if self.on_done:
                self.on_done(self.evolved)

    # ------------------------------------------------------------ рисование
    def _silhouette(self, sid, size, color=(255, 255, 255)):
        key = (sid, size, color)
        if key not in self._sil:
            base = pygame.transform.smoothscale(creature_sprite(self.app.data, sid, size), (size, size))
            self._sil[key] = pygame.mask.from_surface(base).to_surface(setcolor=color + (255,), unsetcolor=(0, 0, 0, 0))
        return self._sil[key]

    def _blit_center(self, surf, img, scale=1.0, dy=0):
        w, h = img.get_size()
        if scale != 1.0:
            img = pygame.transform.smoothscale(img, (max(1, int(w * scale)), max(1, int(h * scale))))
            w, h = img.get_size()
        surf.blit(img, (CX - w // 2, CY - h // 2 + dy))

    def draw(self, surf):
        cfg, tl, size = self.cfg, self.tl, self.cfg["sprite_size"]
        name, p = (tl.name, tl.progress) if self.stage == "anim" else ("reveal", 1.0)
        if self.stage == "cancelled":
            name, p = "intro", 0.0
        # фон: лёгкая пульсация, к концу мерцания светлеет
        glow = {"intro": 0.0, "flicker": 0.35 * p, "burst": 1.0, "reveal": 1.0 - p}[name]
        surf.fill(tuple(int(c + (200 - c) * glow * 0.45) for c in BG))
        t = self.time
        if name in ("flicker", "burst", "reveal") and self.stage == "anim":      # лучи
            for i in range(14):
                ang = t * 0.6 + i * math.tau / 14
                length = 90 + 140 * (0.4 + 0.6 * glow)
                end = (CX + math.cos(ang) * length, CY + math.sin(ang) * length)
                pygame.draw.line(surf, (120, 150, 230) if name != "burst" else (255, 255, 255), (CX, CY), end, 2)
        pygame.draw.circle(surf, tuple(int(c + (230 - c) * glow) for c in (40, 50, 90)), (CX, CY), int(size * (0.55 + 0.35 * glow)))
        # существо
        if self.stage == "anim" and name == "flicker":
            hz0, hz1 = cfg["flicker_hz"]
            new = flicker_show_new(tl.t, tl.duration, hz0, hz1)
            self._blit_center(surf, self._silhouette(self.into if new else self.old_id, size), pulse_scale(t) * (1 + 0.1 * p))
        elif self.stage == "anim" and name == "burst":
            self._blit_center(surf, self._silhouette(self.into, size), 1.0 + 0.25 * p)
        elif self.stage == "anim" and name == "reveal":
            self._blit_center(surf, creature_sprite(self.app.data, self.into, size), 1.0 + 0.25 * (1 - p) * (1 - p))
        elif self.stage == "message":
            self._blit_center(surf, creature_sprite(self.app.data, self.into if (self.evolved or self.preview) else self.old_id, size))
        else:       # intro / отменено
            self._blit_center(surf, creature_sprite(self.app.data, self.old_id, size), 1.0 + 0.03 * math.sin(t * 4))
        # свои кадры поверх
        if self.frames and self.stage == "anim" and name in ("flicker", "burst"):
            fr = self.frames[int(t * cfg["fps"]) % len(self.frames)]
            surf.blit(fr, (CX - fr.get_width() // 2, CY - fr.get_height() // 2))
        # искры
        if cfg["particles"] and self.stage == "anim":
            for x, y, a, r in self.particles.positions():
                c = int(120 + 135 * a)
                pygame.draw.circle(surf, (c, c, 255), (int(CX + x), int(CY + y)), r)
        # вспышка
        if self.stage == "anim" and name == "burst":
            overlay = pygame.Surface((480, 320), pygame.SRCALPHA)
            overlay.fill((255, 255, 255, int(255 * (p if p < 0.5 else 1 - (p - 0.5) * 0.3))))
            surf.blit(overlay, (0, 0))
        # текст
        panel(surf, (8, 232, 464, 80))
        for k, ln in enumerate(wrap(self.text, 440)[:3]):
            text(surf, ln, 20, 242 + k * 22)
        if self.stage != "anim":
            arrow(surf, 452, 292, 6)
        elif self.cancellable and tl.can_cancel():
            text(surf, "X - отмена", 394, 292, 12, (110, 110, 110))


def evolve_chain(app, on_done=None):
    """Предлагает по очереди все эволюции по уровню у команды (с учётом отказов). После успешной эволюции проверяет снова."""
    def step(_=None):
        for c in app.state.party:
            into = evolution.pending_level_evolution(c)
            if into:
                app.push(EvolutionScene(app, c, into, on_done=step, cancellable=True, cause="level"))
                return
        if on_done:
            on_done()
    step()
