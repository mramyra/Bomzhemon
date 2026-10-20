"""Логика анимации эволюции без pygame: таймлайн фаз, мерцание, частицы. Рисование - в game/scenes/evolution_scene.py.
Параметры берутся из data/animations.json (раздел evolution), недостающие - из DEFAULT_CONFIG."""
import math
import random

DEFAULT_CONFIG = {"intro": 1.6, "flicker": 4.2, "burst": 0.8, "reveal": 1.3, "flicker_hz": [1.5, 12.0],
                  "sprite_size": 128, "fps": 12, "particles": True}
PHASE_ORDER = ("intro", "flicker", "burst", "reveal")
CANCELLABLE = ("intro", "flicker")      # отменить можно только до вспышки


def make_config(raw=None):
    cfg = dict(DEFAULT_CONFIG)
    cfg.update(raw or {})
    return cfg


def validate_config(cfg):
    errs = []
    for k in PHASE_ORDER:
        if not isinstance(cfg.get(k), (int, float)) or cfg[k] <= 0:
            errs.append(f"animations.evolution.{k}: нужна длительность > 0")
    hz = cfg.get("flicker_hz")
    if not (isinstance(hz, list) and len(hz) == 2 and 0 < hz[0] <= hz[1]):
        errs.append("animations.evolution.flicker_hz: нужно [старт, конец], 0 < старт <= конец")
    if not isinstance(cfg.get("sprite_size"), int) or cfg["sprite_size"] < 16:
        errs.append("animations.evolution.sprite_size: целое >= 16")
    if not isinstance(cfg.get("fps"), (int, float)) or cfg["fps"] <= 0:
        errs.append("animations.evolution.fps: > 0")
    return errs


class Timeline:
    """Последовательность фаз intro -> flicker -> burst -> reveal. update() возвращает имена фаз, в которые вошли за этот шаг."""

    def __init__(self, cfg):
        self.phases = [(n, float(cfg[n])) for n in PHASE_ORDER]
        self.i, self.t, self.done = 0, 0.0, False

    @property
    def name(self):
        return self.phases[self.i][0]

    @property
    def duration(self):
        return self.phases[self.i][1]

    @property
    def progress(self):
        return min(1.0, self.t / self.duration)

    @property
    def total(self):
        return sum(d for _, d in self.phases)

    @property
    def elapsed(self):
        return sum(d for _, d in self.phases[:self.i]) + self.t

    def can_cancel(self):
        return not self.done and self.name in CANCELLABLE

    def update(self, dt):
        entered = []
        if self.done:
            return entered
        self.t += dt
        while self.t >= self.phases[self.i][1]:
            self.t -= self.phases[self.i][1]
            if self.i == len(self.phases) - 1:
                self.t, self.done = self.phases[self.i][1], True
                break
            self.i += 1
            entered.append(self.name)
        return entered


def flicker_cycles(t, duration, hz0, hz1):
    """Накопленные циклы мерцания за время t: частота растёт линейно от hz0 до hz1."""
    return hz0 * t + (hz1 - hz0) * t * t / (2 * duration)


def flicker_show_new(t, duration, hz0, hz1):
    """True - в этот момент показываем новую форму, False - старую. Чем дальше, тем чаще смена."""
    return int(flicker_cycles(t, duration, hz0, hz1) * 2) % 2 == 1


def pulse_scale(t, amp=0.07, hz=3.0):
    return 1.0 + amp * math.sin(2 * math.pi * hz * t)


class Particles:
    """Искры вокруг существа: вылетают от центра и гаснут. positions() -> [(x, y, яркость 0..1, размер)] относительно центра."""

    def __init__(self, seed=1, limit=160):
        self.rng, self.limit, self.items, self.acc = random.Random(seed), limit, [], 0.0

    def update(self, dt, rate):
        self.acc += rate * dt
        while self.acc >= 1 and len(self.items) < self.limit:
            self.acc -= 1
            self.items.append({"a": self.rng.uniform(0, math.tau), "r0": self.rng.uniform(20, 60), "v": self.rng.uniform(40, 150),
                               "life": self.rng.uniform(0.6, 1.4), "age": 0.0, "size": self.rng.choice((1, 2, 2, 3))})
        self.acc = min(self.acc, 1.0)
        for p in self.items:
            p["age"] += dt
        self.items = [p for p in self.items if p["age"] < p["life"]]

    def positions(self):
        return [(math.cos(p["a"]) * (p["r0"] + p["v"] * p["age"]), math.sin(p["a"]) * (p["r0"] + p["v"] * p["age"]),
                 1 - p["age"] / p["life"], p["size"]) for p in self.items]
