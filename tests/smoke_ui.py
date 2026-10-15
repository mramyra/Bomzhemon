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
import types  # noqa: E402
_pg = sys.modules["pygame"]
for _n, _v in dict(K_BACKQUOTE=96, K_F1=1073741882, K_ESCAPE=27, K_RETURN=13, K_KP_ENTER=1073741912, K_BACKSPACE=8,
                   K_TAB=9, K_UP=1073741906, K_DOWN=1073741905, K_PAGEUP=1073741899, K_PAGEDOWN=1073741902).items():
    setattr(_pg, _n, _v)
_pg.time = types.SimpleNamespace(get_ticks=lambda: 0)

import game.ui.widgets as W  # noqa: E402


class FakeFont:
    def size(self, t): return (len(str(t)) * 7, 14)
    def render(self, *a, **k): return MagicMock()


W.font = lambda size=16, bold=False: FakeFont()
W.mono = lambda size=12: FakeFont()

import game.ui.sprites as SP  # noqa: E402
SP.creature_sprite = lambda *a, **k: MagicMock()
import game.scenes.battle_scene as BS  # noqa: E402
BS.creature_sprite = SP.creature_sprite
import game.scenes.screens as SCR  # noqa: E402
SCR.creature_sprite = SP.creature_sprite
import game.scenes.debug_hub as HUB  # noqa: E402
import game.scenes.world as WORLD  # noqa: E402
import game.scenes.screens as SCREENS  # noqa: E402
import game.scenes.console_scene as CONSOLE  # noqa: E402
CONSOLE.mono = W.mono
import game.systems.save as SAVE  # noqa: E402
SAVE.save = lambda *a, **k: None   # тест не пишет на диск

from game.core.data import GameData  # noqa: E402
from game.systems.state import PlayerState  # noqa: E402


class FakeApp:
    def __init__(self):
        self.data, self.state, self.stack = GameData(), PlayerState(), []
        self.held, self.fullscreen = set(), False
        self.state.add_creature(self.data.make_creature("shchenok", 12))
        self.state.add_creature(self.data.make_creature("krysa", 10))
        self.state.add_item("palto", 1)

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
        app.state.add_creature(app.data.make_creature("dikiy", 25))
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
    # Меняла и бомждекс (с легендарными)
    for i in range(150):
        app = FakeApp()
        for sid in ("ptenets", "pleshipes", "cheremshkot", "bingus"):
            app.state.add_creature(app.data.make_creature(sid, 10 + i % 20))
        app.state.seen |= set(app.data.species)
        for make in (SCREENS.TradeScene, SCREENS.DexScene, SCREENS.TradeScene):
            scene = make(app)
            app.push(scene)
            for _ in range(120):
                if not app.stack:
                    break
                top = app.stack[-1]
                top.update(0.05); top.draw(MagicMock())
                top.handle(rng.choice(["ok", "ok", "down", "up", "back", "left", "right"]))
            app.stack.clear()
        assert len(app.state.party) + len(app.state.storage) >= 5
    print("OK: Меняла и бомждекс, 150 сессий")
    # консоль поверх мира: набираем команды клавишами, включая бой и телепорт
    class Key:
        def __init__(self, key, ch=""):
            self.key, self.unicode = key, ch

    def type_line(con_scene, line):
        for ch in line:
            con_scene.on_key(Key(ord(ch), ch))
        con_scene.on_key(Key(13))

    cmds = ["help", "give krysa 16", "party", "checkevo", "give kokonishche 10", "useitem 3 palto", "evolve 1 krysiny_korol", "exp 1 5000",
            "give shchenok 30 5", "tp 4 4", "tp", "info 1", "storage", "dex all", "heal", "list species", "give tr", "боевая", "give ptenets 12", "trade 2", "trade 2 krysa", "trade 1",
            "battle tarakan 8", "trainer granny_zina", "save"]
    for i in range(60):
        app = FakeApp()
        w = WORLD.WorldScene(app)
        app.push(w)
        for step in range(40):
            if app.stack[-1] is w:
                app.stack[-1].update(0.05)
                c = CONSOLE.ConsoleScene(app)
                app.push(c)
                for _ in range(rng.randint(1, 4)):
                    if c not in app.stack:
                        break
                    type_line(c, rng.choice(cmds))
                    c.draw(MagicMock())
                    c.on_key(Key(9)); c.on_key(Key(1073741906)); c.on_key(Key(1073741899)); c.on_key(Key(8))
                if c in app.stack:
                    c.on_key(Key(96))                       # ` закрывает
                    assert c not in app.stack
            else:                                           # открылся бой/окно: играем до возврата в мир
                for _ in range(400):
                    top = app.stack[-1]
                    if top is w:
                        break
                    top.update(0.05); top.draw(MagicMock())
                    top.handle(rng.choice(["ok", "ok", "ok", "down", "up", "back"]))
                    if not app.state.has_usable():
                        app.state.heal_party()
    print("OK: консоль поверх мира, 60 сессий")
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
