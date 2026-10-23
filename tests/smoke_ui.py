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


class _Rect:     # минимальный Rect: хватает для арифметики координат в рисовании
    def __init__(self, x, y, w, h):
        self.x, self.y, self.w, self.h = x, y, w, h
    right = property(lambda s: s.x + s.w)
    bottom = property(lambda s: s.y + s.h)


_pg.Rect = _Rect


class FakeImg(MagicMock):    # картинка-заглушка: размер как у настоящей Surface, остальное - пустые методы
    def get_size(self):
        return (64, 64)


_pg.transform = types.SimpleNamespace(smoothscale=lambda img, size: FakeImg(), scale=lambda img, size: FakeImg(), flip=lambda img, x, y: FakeImg())
_pg.mask = types.SimpleNamespace(from_surface=lambda surf: types.SimpleNamespace(to_surface=lambda **kw: FakeImg()))

import game.ui.widgets as W  # noqa: E402


class FakeFont:
    def size(self, t): return (len(str(t)) * 7, 14)
    def render(self, *a, **k): return MagicMock()


W.font = lambda size=16, bold=False: FakeFont()
W.mono = lambda size=12: FakeFont()

import game.ui.sprites as SP  # noqa: E402
SP.creature_sprite = lambda *a, **k: FakeImg()
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
import tempfile  # noqa: E402
from pathlib import Path  # noqa: E402
SAVE.SAVE_DIR = Path(tempfile.mkdtemp(prefix="bomzhemon_smoke_"))   # тест пишет только во временную папку
import game.scenes.title as TITLE  # noqa: E402
import game.scenes.exit_flow as EXIT  # noqa: E402
import game.scenes.transition as TRANS  # noqa: E402
import game.scenes.evolution_scene as EVOS  # noqa: E402
EVOS.creature_sprite = SP.creature_sprite
import game.scenes.pc as PCS  # noqa: E402
PCS.creature_sprite = SP.creature_sprite
TITLE.creature_sprite = SP.creature_sprite

from game.core.data import GameData  # noqa: E402
from game.systems.state import PlayerState  # noqa: E402


class FakeApp:
    def __init__(self):
        self.data, self.state, self.stack = GameData(), PlayerState(), []
        self.held, self.fullscreen = set(), False
        from game.core.events import EventBus
        self.events = EventBus()
        self.state.add_creature(self.data.make_creature("shchenok", 12))
        self.state.add_creature(self.data.make_creature("krysa", 10))
        self.state.add_item("palto", 1)

    def toggle_fullscreen(self): self.fullscreen = not self.fullscreen
    def push(self, s): self.stack.append(s)
    def pop(self): self.stack.pop()
    def replace(self, s): self.stack = [s]
    def quit(self): self.stack.clear()


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


class CONSOLE_BATTLE_STUB:      # заглушка боя для проверки выхода: достаточно признака is_battle
    is_battle = True
    transparent = True
    def update(self, dt): pass
    def draw(self, s): pass
    def handle(self, a): pass


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
                hub.menu.i = rng.choice([0, 0, 0, 1, 2, 3, 4, 5, 6, 7])
                top.handle("ok")
            else:
                top.handle(rng.choice(["ok", "ok", "ok", "down", "up", "left", "right", "back"]))
            if app.state and not app.state.has_usable():
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
            "battle tarakan 8", "trainer granny_zina", "map vokzal", "map dump from_vokzal", "map", "map нету", "save"]
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
                    if app.state and not app.state.has_usable():
                        app.state.heal_party()
    print("OK: консоль поверх мира, 60 сессий")
    # сценарий сохранения и выходов: новая игра -> сохранить -> в меню -> продолжить -> выйти с сохранением
    def press(app, *actions):
        for a in actions:
            if not app.stack:
                return
            top = app.stack[-1]
            top.update(0.05); top.draw(MagicMock())
            top.handle(a)

    def pause_pick(app, label):
        press(app, "back")
        pause = app.stack[-1]
        assert isinstance(pause, WORLD.PauseScene), type(pause)
        pause.menu.i = pause.items.index(label)
        press(app, "ok")

    import shutil
    shutil.rmtree(SAVE.SAVE_DIR, ignore_errors=True)
    SAVE.SAVE_DIR.mkdir(parents=True, exist_ok=True)
    app = FakeApp()
    app.state = None
    app.replace(TITLE.TitleScene(app))
    assert app.stack[-1].items == ["Новая игра", "Отладочный хаб", "Выход"]             # сохранений нет - продолжить недоступно
    press(app, "ok", "right", "ok")                                                       # новая игра, выбрать второго стартового
    assert isinstance(app.stack[-1], SCREENS.MessageScene)
    press(app, "ok", "ok", "ok")
    world = app.stack[-1]
    assert isinstance(world, WORLD.WorldScene) and app.state.party[0].species_id == "shchenok"
    start_pos = (world.x, world.y)
    pause_pick(app, "Сохранить")
    assert type(app.stack[-1]).__name__ == "SlotScene"
    app.stack[-1].menu.i = 1                                                              # слот 2
    press(app, "ok")                                                                      # записали, окно слотов закрылось
    press(app, "ok")                                                                      # сообщение "Сохранено"
    assert app.state.slot == 2 and SAVE.slot_path(2).exists()
    assert isinstance(app.stack[-1], WORLD.PauseScene)                                     # после сохранения остаёмся в паузе
    press(app, "back")                                                                    # закрыть паузу
    assert isinstance(app.stack[-1], WORLD.WorldScene)
    app.state.money = 999                                                                 # несохранённое изменение
    pause_pick(app, "В главное меню")
    assert type(app.stack[-1]).__name__ == "ChoiceScene"
    press(app, "down", "ok")                                                              # выйти без сохранения
    assert isinstance(app.stack[-1], TITLE.TitleScene) and app.state is None
    assert app.stack[-1].items[:2] == ["Продолжить", "Загрузить"]
    press(app, "ok")                                                                      # продолжить
    assert isinstance(app.stack[-1], WORLD.WorldScene) and app.state.money == 0 and app.state.slot == 2
    assert (app.stack[-1].x, app.stack[-1].y) == start_pos
    app.state.money = 321
    pause_pick(app, "Выйти из игры")
    press(app, "ok")                                                                      # сохранить и выйти (слот уже известен)
    assert app.stack == [] and SAVE.load(app.data, 2).money == 321
    # загрузить из списка слотов, битый файл, старый состав
    app = FakeApp(); app.state = None
    SAVE.slot_path(3).write_text("мусор", encoding="utf-8")
    import json
    raw = json.load(open(SAVE.slot_path(2), encoding="utf-8")); raw["party"][0]["species"] = "rat_boss"
    SAVE.slot_path(1).write_text(json.dumps(raw), encoding="utf-8")
    app.replace(TITLE.TitleScene(app))
    title = app.stack[-1]
    assert title.latest == 2                                                              # битые слоты не мешают "Продолжить"
    title.menu.i = title.items.index("Загрузить")
    press(app, "ok")
    slots = app.stack[-1]
    assert [(s, m["ok"] if m else None) for s, m in slots.rows] == [(0, None), (1, False), (2, True), (3, False)]
    slots.menu.i = 1; press(app, "ok")                                                    # несовместимый: предложение удалить
    assert type(app.stack[-1]).__name__ == "ChoiceScene"
    press(app, "ok")                                                                      # удалить
    assert not SAVE.slot_path(1).exists()
    slots.menu.i = 2; press(app, "ok", "ok")                                              # слот 2 -> Загрузить
    assert isinstance(app.stack[-1], WORLD.WorldScene) and app.state.money == 321
    # слот удалили в списке слотов: "Продолжить" исчезает, а устаревший пункт не роняет игру
    app = FakeApp(); app.state = None
    SAVE.save(FakeApp().state, 2)
    app.replace(TITLE.TitleScene(app))
    title = app.stack[-1]
    assert title.items[0] == "Продолжить"
    SAVE.delete(2)
    title.menu.i = 0
    press(app, "ok")                                                                      # ещё "Продолжить" в меню, но сохранений уже нет
    assert type(app.stack[-1]).__name__ == "MessageScene" and "Сохранений не осталось" in app.stack[-1].lines[0]
    press(app, "ok")
    assert "Продолжить" not in title.items and isinstance(app.stack[-1], TITLE.TitleScene)
    print("OK: сценарий сохранения/выхода/продолжения")
    # случайные нажатия по титульному экрану и слотам с разными файлами (целый, битый, старый состав)
    import json as _json
    for i in range(120):
        shutil.rmtree(SAVE.SAVE_DIR, ignore_errors=True)
        SAVE.SAVE_DIR.mkdir(parents=True, exist_ok=True)
        app = FakeApp(); app.state = app.state
        SAVE.save(app.state, 2, location="Свалка")
        if i % 3 == 0:
            SAVE.slot_path(1).write_text("{ битый", encoding="utf-8")
        if i % 4 == 0:
            raw = _json.load(open(SAVE.slot_path(2), encoding="utf-8")); raw["party"][0]["species"] = "rat_boss"
            SAVE.slot_path(3).write_text(_json.dumps(raw), encoding="utf-8")
        if i % 5 == 0:
            SAVE.autosave(app.state)
        app.state = None
        app.replace(TITLE.TitleScene(app))
        for _ in range(200):
            if not app.stack:
                break
            top = app.stack[-1]
            top.update(0.05); top.draw(MagicMock())
            if isinstance(top, TITLE.TitleScene) and top.items[top.menu.i] in ("Выход", "Отладочный хаб"):
                top.menu.i = 0
            top.handle(rng.choice(["ok", "ok", "down", "up", "back", "left", "right"]))
            if app.state and not app.state.has_usable():
                app.state.heal_party()
    print("OK: титульный экран и слоты, 120 сессий")
    def press(app, *actions):
        for a in actions:
            if not app.stack:
                return
            top = app.stack[-1]
            top.update(0.05); top.draw(MagicMock())
            top.handle(a)

    # экран ПК: случайные нажатия, инварианты состава команды/ПК
    for i in range(150):
        app = FakeApp()
        for k in range(rng.choice([0, 3, 31, 65])):
            app.state.storage.append(app.data.make_creature(rng.choice(list(app.data.species)), 3 + k % 20))
        total = len(app.state.party) + len(app.state.storage)
        scene = PCS.PCScene(app)
        app.push(scene)
        released = 0
        for _ in range(500):
            if not app.stack:
                break
            top = app.stack[-1]
            top.update(0.05); top.draw(MagicMock())
            top.handle(rng.choice(["ok", "ok", "ok", "down", "up", "left", "right", "back"]))
            st = app.state
            assert 1 <= len(st.party) <= 6
            assert len({id(c) for c in st.party + st.storage}) == len(st.party) + len(st.storage)
            assert len(st.party) + len(st.storage) <= total
            total = len(st.party) + len(st.storage)         # отпускание допустимо - уменьшает общее число
    print("OK: ПК, 150 сессий")
    # экран ПК по шагам: быстрый перенос, перенос в руке, обмен, подробности, отпускание
    app = FakeApp()                                   # команда: Щенок, Крыса
    app.state.add_creature(app.data.make_creature("kotenok", 6))
    for sid in ("pes", "lisitsa", "enot"):
        app.state.storage.append(app.data.make_creature(sid, 8))
    pcs = PCS.PCScene(app); app.push(pcs)
    names = lambda L: [c.species_id for c in L]
    press(app, "down", "ok")                           # Крыса -> меню действий
    assert type(app.stack[-1]).__name__ == "ChoiceScene" and app.stack[-1].opts[2] == "В ПК"
    press(app, "down", "down", "ok")                   # "В ПК"
    press(app, "ok")                                   # закрыть сообщение
    assert names(app.state.party) == ["shchenok", "kotenok"] and app.state.storage[-1].species_id == "krysa"
    press(app, "right", "up", "ok", "down", "ok")      # клетка 1 ящика -> "Переместить" (в руке Пёс)
    assert pcs.held == ("box", 0)
    press(app, "left", "ok")                           # в клетку команды 0: обмен с Щенком
    press(app, "ok")
    assert app.state.party[0].species_id == "pes" and app.state.storage[0].species_id == "shchenok" and pcs.held is None
    press(app, "ok", "ok")                             # меню действий -> "Подробнее"
    assert type(app.stack[-1]).__name__ == "CreatureScene" and app.stack[-1].c.species_id == "pes"
    press(app, "back")
    press(app, "ok", "down", "down", "down", "ok")     # "Отпустить" -> подтверждение
    press(app, "ok")                                   # да
    press(app, "ok")                                   # сообщение
    assert "pes" not in names(app.state.party + app.state.storage) and len(app.state.party) == 1
    press(app, "ok", "down", "down", "down", "ok", "ok", "ok")      # последнего в команде отпустить нельзя
    assert len(app.state.party) == 1 and isinstance(app.stack[-1], PCS.PCScene)
    print("OK: ПК по шагам")
    # анимация эволюции: после боя, отмена, предмет (без отмены), просмотр, фаззинг
    def run_scene(app, limit=400, dt=0.1, actions=()):
        """Проигрывает верхнюю сцену, пока она не закроется; actions - {номер шага: действие}."""
        top = app.stack[-1]
        for step in range(limit):
            if not app.stack or app.stack[-1] is not top:
                return step
            top.update(dt); top.draw(MagicMock())
            if step in dict(actions):
                top.handle(dict(actions)[step])
            if top.stage in ("message", "cancelled") and step > 5:
                top.handle("ok")
        raise AssertionError("анимация не закончилась")

    app = FakeApp(); app.state.party[:] = [app.data.make_creature("khomechennok", 16)]
    log, done = [], []
    for ev_name in ("evolution_start", "evolution_intro", "evolution_flicker", "evolution_burst", "evolution_reveal", "evolution_done", "evolution_cancelled"):
        app.events.on(ev_name, lambda _n=ev_name, **kw: log.append(_n))
    EVOS.evolve_chain(app, lambda: done.append(1))
    assert isinstance(app.stack[-1], EVOS.EvolutionScene)
    run_scene(app)
    assert app.state.party[0].species_id == "khomyak" and done == [1] and "khomyak" in app.state.caught
    assert log == ["evolution_start", "evolution_flicker", "evolution_burst", "evolution_reveal", "evolution_done"], log
    app.state.party[0].level = 33; app.state.party[0].recalc()                       # цепочка: Хомяк -> Хомемертв
    EVOS.evolve_chain(app, lambda: done.append(2)); run_scene(app)
    assert app.state.party[0].species_id == "khomemertv" and done == [1, 2]
    # отмена эволюции по уровню: остаёмся прежним, снова не спрашивают на этом же уровне
    app = FakeApp(); app.state.party[:] = [app.data.make_creature("khomechennok", 16)]
    done = []
    EVOS.evolve_chain(app, lambda: done.append(1))
    run_scene(app, actions=[(5, "back")])
    c = app.state.party[0]
    assert c.species_id == "khomechennok" and c.declined_evolution_level == 16 and done == [1] and app.stack == []
    EVOS.evolve_chain(app, lambda: done.append(2))
    assert app.stack == [] and done == [1, 2]                                         # новой анимации нет
    c.level = 17; c.recalc()
    EVOS.evolve_chain(app, lambda: done.append(3))
    assert isinstance(app.stack[-1], EVOS.EvolutionScene)                             # на следующем уровне спрашиваем снова
    run_scene(app)
    assert c.species_id == "khomyak"
    # предмет: отменить нельзя, предмет тратится, Бомждекс обновляется
    app = FakeApp(); app.state.party[:] = [app.data.make_creature("kokonishche", 20)]
    app.state.bag["palto"] = 1
    bag = SCREENS.BagScene(app); app.push(bag)
    bag.use("palto", app.state.party[0])
    scene = app.stack[-1]
    assert isinstance(scene, EVOS.EvolutionScene) and not scene.cancellable and app.state.bag["palto"] == 0
    run_scene(app, actions=[(5, "back"), (10, "back")])                              # X во время анимации не отменяет
    assert app.state.party[0].species_id == "mol" and "mol" in app.state.caught
    # просмотр анимации не меняет существо
    app = FakeApp(); app.state.party[:] = [app.data.make_creature("krysa", 10)]
    app.push(EVOS.EvolutionScene(app, app.state.party[0], "spidkrys", preview=True, cause="preview"))
    run_scene(app)
    assert app.state.party[0].species_id == "krysa" and "spidkrys" not in app.state.caught
    # фаззинг: случайные нажатия и шаги времени
    for i in range(200):
        app = FakeApp(); app.state.party[:] = [app.data.make_creature("khomechennok", 16)]
        called = []
        sc = EVOS.EvolutionScene(app, app.state.party[0], "khomyak", on_done=lambda ok: called.append(ok), cancellable=bool(i % 2), preview=(i % 7 == 0))
        app.push(sc)
        for _ in range(600):
            if not app.stack:
                break
            sc.update(rng.choice([0.0, 0.016, 0.05, 0.3, 1.5]))
            sc.draw(MagicMock())
            sc.handle(rng.choice(["ok", "back", "up", "left"]))
        assert len(called) <= 1
        if called:
            assert called[0] == (app.state.party[0].species_id == "khomyak") or sc.preview
    print("OK: анимация эволюции")
    # переход между локациями: значок-замок, затемнение, возвращение, респаун, сохранение, миграция флагов
    def drive(app, limit=100, dt=0.05):
        for _ in range(limit):
            top = app.stack[-1]
            if not isinstance(top, TRANS.TransitionScene):
                return
            top.update(dt); top.draw(MagicMock())
        raise AssertionError("затемнение не закончилось")

    app = FakeApp(); app.state.party[:] = [app.data.make_creature("shchenok", 12)]
    w = WORLD.WorldScene(app); app.replace(w)
    assert w.district == "dump" and w.banner > 0
    ex = w.map.objects_of("exit")[0]
    arrive = w.map.spawn("from_vokzal")
    w.x, w.y = arrive.x, arrive.y
    app.held = {"right"}; w.last_dir = "right"
    w.update(0.0)                                                   # значка нет - не пускают
    assert isinstance(app.stack[-1], SCREENS.MessageScene) and w.moving is None and not app.held and w.district == "dump"
    assert "Михалыч" in app.stack[-1].lines[0]
    press(app, "ok")
    app.state.badges.append("badge_dump")
    app.held = {"right"}; w.last_dir = "right"
    w.update(0.0)
    assert w.moving == (1, 0)
    w.update(1.0)                                                   # дошли до тайла выхода -> затемнение
    assert isinstance(app.stack[-1], TRANS.TransitionScene)
    drive(app)
    assert app.stack == [w] and w.district == "vokzal" and w.banner > 0
    sp = w.map.spawn("from_dump")
    assert (w.x, w.y) == (sp.x, sp.y) and app.state.pos == {"map": "vokzal", "x": sp.x, "y": sp.y}
    assert w.face == "right" and not w.map.blocked(w.x, w.y)
    assert w.items and set(w.items) != set()                        # в новой локации свои предметы
    # предметы и баки отмечаются отдельно по районам
    spot = next(o for o in w.map.objects_of("item_spot") if o.id in w.items)
    w.x, w.y = spot.x, spot.y
    w._picked().append(spot.id)
    assert spot.id in app.state.flags["picked"]["vokzal"] and spot.id not in app.state.flags["picked"].get("dump", [])
    # сохранение внутри вокзала и загрузка
    w.sync_pos()
    SAVE.save(app.state, 1)
    st2 = SAVE.load(app.data, 1)
    app2 = FakeApp(); app2.state = st2
    w2 = WORLD.WorldScene(app2)
    assert w2.district == "vokzal" and (w2.x, w2.y) == (w.x, w.y) and w2.items == w.items
    SAVE.delete(1)                                                  # не мешаем следующим сценариям
    # респаун после поражения возвращает к бочке в другом районе
    dump_start = None
    app.state.flags["checkpoint"] = {"map": "dump", "x": 5, "y": 3}
    w._after_battle("lose")
    assert w.district == "dump" and (w.x, w.y) in ((5, 3), w.map.start()) and app.state.pos["map"] == "dump"
    # обратный путь: вокзал -> свалка без значка не нужен
    w.travel("vokzal", "from_dump")
    ex2 = w.map.objects_of("exit")[0]
    assert ex2.props["target"] == "dump" and "requires_badge" not in ex2.props
    app.state.badges.clear()
    w.x, w.y = w.map.spawn("from_dump").x, w.map.spawn("from_dump").y
    app.held = {"left"}; w.last_dir = "left"
    w.update(0.0); w.update(1.0)
    assert isinstance(app.stack[-1], TRANS.TransitionScene)
    drive(app)
    back = w.map.spawn("from_vokzal")
    assert w.district == "dump" and (w.x, w.y) == (back.x, back.y)
    # старые сохранения: флаги-списки -> по районам; неизвестный район -> свалка
    app = FakeApp(); app.state.flags.update({"picked": [1, 2], "opened": [3], "checkpoint": [5, 6]})
    app.state.pos = {"map": "no_such_district", "x": 9, "y": 9}
    w = WORLD.WorldScene(app)
    assert app.state.flags["picked"] == {"dump": [1, 2]} and app.state.flags["opened"] == {"dump": [3]}
    assert app.state.flags["checkpoint"] == {"map": "dump", "x": 5, "y": 6}
    assert w.district == "dump" and (w.x, w.y) == w.map.start()
    app.state.flags["checkpoint"] = "мусор"
    WORLD.migrate_flags(app.state)
    assert "checkpoint" not in app.state.flags
    print("OK: переход между локациями")
    # закрытие окна (крестик / Alt+F4)
    app = FakeApp(); app.state = None
    app.replace(TITLE.TitleScene(app))
    EXIT.request_quit(app)
    assert app.stack == []                                       # на титульном экране - сразу выход
    app = FakeApp()                                              # игра идёт, слот ещё не выбран
    w = WORLD.WorldScene(app); app.replace(w)
    EXIT.request_quit(app)
    assert type(app.stack[-1]).__name__ == "ChoiceScene" and len(app.stack[-1].opts) == 3
    press(app, "back")                                           # отмена - остаёмся в игре
    assert app.stack == [w]
    EXIT.request_quit(app); EXIT.request_quit(app)               # повторное закрытие при открытом вопросе - выходит сразу
    assert app.stack == []
    app = FakeApp(); w = WORLD.WorldScene(app); app.replace(w)
    EXIT.request_quit(app); press(app, "ok")                     # "Сохранить и выйти" без слота -> выбор слота
    assert type(app.stack[-1]).__name__ == "SlotScene"
    press(app, "ok", "ok")                                       # записали в слот 1, сообщение, выход
    assert app.stack == [] and SAVE.slot_path(1).exists()
    app = FakeApp(); w = WORLD.WorldScene(app); app.replace(w)
    app.stack.append(CONSOLE_BATTLE_STUB())
    EXIT.request_quit(app)
    q = app.stack[-1]
    assert type(q).__name__ == "ChoiceScene" and len(q.opts) == 2   # в бою сохранить нельзя
    press(app, "ok")
    assert app.stack == []
    print("OK: закрытие окна: вопрос, отмена, сохранение, бой")
    # мир: бродим по карте, удерживая случайные направления; бои проходят скриптом
    for i in range(40):
        app = FakeApp()
        app.state.bag["box"] = 10
        w = WORLD.WorldScene(app)
        app.push(w)
        for step in range(1500):
            if not app.stack or w not in app.stack:     # случайно вышли в меню/из игры через паузу
                break
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
            if app.state and not app.state.has_usable():
                app.state.heal_party()
        assert (w.x, w.y) != (0, 0) or not app.stack or w not in app.stack
    print("OK: 40 прогулок по карте по 1500 тиков, без падений")


if __name__ == "__main__":
    main()
