"""Дымовой тест UI без pygame (pygame подменён заглушкой): гоняет сцены скриптом и проверяет, что ничего не падает.
Запуск: python -m tests.smoke_ui"""
import random
import sys
from pathlib import Path


class MagicMock:   # заглушка без записи вызовов (настоящий Mock копит историю и съедает память)
    def __getattr__(self, n): return MagicMock()
    def __call__(self, *a, **k): return MagicMock()
    def __iter__(self): return iter(())
    def __getitem__(self, i): return MagicMock()

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.modules["pygame"] = MagicMock()

import game.ui.widgets as W  # noqa: E402


class FakeFont:
    def size(self, t): return (len(str(t)) * 7, 14)
    def render(self, *a, **k): return MagicMock()


W.font = lambda size=16, bold=False: FakeFont()

import game.ui.sprites as SP  # noqa: E402
SP.creature_sprite = lambda *a, **k: MagicMock()
import game.scenes.battle_scene as BS  # noqa: E402
BS.creature_sprite = SP.creature_sprite
import game.scenes.screens as SCR  # noqa: E402
SCR.creature_sprite = SP.creature_sprite
import game.scenes.debug_hub as HUB  # noqa: E402
import game.scenes.world as WORLD  # noqa: E402
import game.scenes.screens as SCREENS  # noqa: E402
import game.systems.save as SAVE  # noqa: E402
SAVE.save = lambda *a, **k: None   # тест не пишет на диск

from game.core.data import GameData  # noqa: E402
from game.systems.state import PlayerState  # noqa: E402


class FakeApp:
    def __init__(self):
        self.data, self.state, self.stack = GameData(), PlayerState(), []
        self.held, self.fullscreen = set(), False
        self.state.add_creature(self.data.make_creature("stray_dog", 12))
        self.state.add_creature(self.data.make_creature("rat", 10))
        self.state.add_item("moldy_cheese", 1)

    def toggle_fullscreen(self): self.fullscreen = not self.fullscreen
    def push(self, s): self.stack.append(s)
    def pop(self): self.stack.pop()
    def replace(self, s): self.stack = [s]


def drive(app, rng, steps=4000):
    surf = MagicMock()
    for _ in range(steps):
        if not app.stack:
            return True
        top = app.stack[-1]
        top.update(0.05)
        top.draw(surf)
        top.handle(rng.choice(["ok", "ok", "ok", "down", "up", "left", "right", "back"]))
    return False


def main():
    rng = random.Random(42)
    for i in range(150):
        app = FakeApp()
        hub = HUB.HubScene(app)
        app.push(hub)
        hub.draw(MagicMock())
        # случайно бродим по хабу: бои, сумка, крафт, команда, бомждекс
        for _ in range(300):
            top = app.stack[-1]
            top.update(0.05); top.draw(MagicMock())
            if top is hub:   # в хабе только открываем разделы (без сохранения и выхода в меню)
                hub.menu.i = rng.choice([0, 0, 0, 1, 2, 3, 4, 5, 6])
                top.handle("ok")
            else:
                top.handle(rng.choice(["ok", "ok", "ok", "down", "up", "left", "right", "back"]))
            if not app.state.has_usable():
                app.state.heal_party()
    print("OK: 150 сессий хаба по 300 действий, без падений")
    # окно команды: детали, перестановки, выучка приёмов (цепочка с ждущими приёмами)
    for i in range(200):
        app = FakeApp()
        app.state.add_creature(app.data.make_creature("tramp", 25))
        app.state.party[0].pending_moves = ["peck", "bark"]
        app.state.party[2].pending_moves = ["gnaw"]
        SCREENS.learn_chain(app, [c for c in app.state.party if c.pending_moves], None)
        app.push(SCREENS.PartyScene(app))
        for _ in range(250):
            top = app.stack[-1]
            top.update(0.05); top.draw(MagicMock())
            top.handle(rng.choice(["ok", "ok", "down", "up", "left", "right", "back"]))
            if len(app.stack) == 0:
                break
        assert all(len(c.moves) <= 4 for c in app.state.party)
    print("OK: окно команды, 200 сессий")
    # мир: бродим по карте, удерживая случайные направления; бои проходят скриптом
    for i in range(40):
        app = FakeApp()
        app.state.bag["box"] = 10
        w = WORLD.WorldScene(app)
        app.push(w)
        for step in range(1500):
            top = app.stack[-1]
            if top is w and step % 15 == 0:
                app.held = {rng.choice(["up", "down", "left", "right"])} if rng.random() < 0.9 else set()
                w.last_dir = next(iter(app.held), None)
            if top is not w:
                app.held = set()
            top.update(0.05)
            top.draw(MagicMock())
            if top is w:
                if rng.random() < 0.08:
                    top.handle(rng.choice(["ok", "back"]))
            else:
                top.handle(rng.choice(["ok", "ok", "ok", "down", "up", "left", "right", "back"]))
            if not app.state.has_usable():
                app.state.heal_party()
        assert (w.x, w.y) != (0, 0)
    print("OK: 40 прогулок по карте по 1500 тиков, без падений")


if __name__ == "__main__":
    main()
