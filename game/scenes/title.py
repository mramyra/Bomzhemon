from game.scenes.base import MessageScene, Scene
from game.scenes.debug_hub import HubScene
from game.scenes.saveload import SlotScene, fmt_time, slot_title
from game.scenes.world import WorldScene
from game.systems import save
from game.systems.state import PlayerState
from game.ui.sprites import creature_sprite
from game.ui.widgets import INK, PAPER, Menu, panel, text

STARTERS = ["khomechennok", "shchenok", "kotenok"]


def enter_world(app, state):
    app.state = state
    app.held.clear()
    app.replace(WorldScene(app))
    if state.loaded_from_backup:
        app.push(MessageScene(app, ["Основной файл сохранения был повреждён, загружена резервная копия."]))


def go_title(app):
    """Выход в главное меню: состояние игры сбрасывается (несохранённое теряется)."""
    app.state = None
    app.held.clear()
    app.replace(TitleScene(app))


class TitleScene(Scene):
    def __init__(self, app):
        super().__init__(app)
        self.menu, self.items, self.latest, self._poll = Menu([""]), [], None, 0.0
        self._rebuild()

    def _rebuild(self):
        """Пересобирает меню по тому, что реально лежит в saves/ (слоты можно удалить в «Загрузить»)."""
        app = self.app
        keep = self.items[self.menu.i] if self.items else None
        slots = [(s, m) for s, m in save.list_slots(data=app.data) if m is not None]
        self.latest = save.latest_slot(data=app.data)
        self.items = (["Продолжить"] if self.latest is not None else []) + (["Загрузить"] if slots else []) + ["Новая игра", "Отладочный хаб", "Выход"]
        self.menu = Menu(self.items)
        if keep in self.items:
            self.menu.i = self.items.index(keep)

    def update(self, dt):
        self._poll += dt
        if self._poll >= 1.0:
            self._poll = 0.0
            self._rebuild()

    def handle(self, a):
        if self.menu.handle(a) != "ok":
            return
        it, app = self.items[self.menu.i], self.app
        if it == "Продолжить":
            slot = save.latest_slot(data=app.data)         # актуальный слот на момент нажатия
            try:
                st = save.load(app.data, slot) if slot is not None else None
            except save.SaveError as e:
                app.push(MessageScene(app, [f"Не удалось загрузить: {e}."]))
                self._rebuild()
                return
            if st is None:
                app.push(MessageScene(app, ["Сохранений не осталось."]))
                self._rebuild()
                return
            enter_world(app, st)
        elif it == "Загрузить":
            app.push(SlotScene(app, "load", on_done=lambda st: enter_world(app, st)))
        elif it == "Новая игра":
            app.push(StarterScene(app))
        elif it == "Отладочный хаб":
            d, st = app.data, PlayerState()
            st.add_creature(d.make_creature("shchenok", 12))
            st.add_creature(d.make_creature("krysa", 10))
            st.bag.update({"box": 10, "bread_crust": 3, "palto": 1, "bin_lid": 1, "syringe": 1})
            app.state = st
            app.replace(HubScene(app))
        else:
            app.quit()

    def draw(self, surf):
        surf.fill(PAPER)
        text(surf, "БОМЖЕМОН", 140, 40, 48, INK, True)
        text(surf, "ловить всех. коробок хватит.", 150, 98, 16)
        self.menu.draw(surf, 190, 150, row_h=28, size=18)
        if self.items[self.menu.i] == "Продолжить":
            m = save.read_meta(self.latest, data=self.app.data)
            if m and m.get("ok"):
                party = ", ".join(f"{p['name']} {p['level']}" for p in m["party"][:3])
                text(surf, f"{slot_title(self.latest)}: {party}  |  {m.get('location') or '-'}  |  {fmt_time(m['play_seconds'])}", 20, 282, 12)
        text(surf, "F11 - полный экран", 8, 302, 12)


class StarterScene(Scene):
    def __init__(self, app):
        super().__init__(app)
        self.menu = Menu(STARTERS, cols=3)

    def handle(self, a):
        r = self.menu.handle(a)
        if r == "back":
            self.app.pop()
        elif r == "ok":
            st = PlayerState()
            st.add_creature(self.app.data.make_creature(STARTERS[self.menu.i], 5))
            enter_world(self.app, st)
            self.app.push(MessageScene(self.app, ["Ты бомж. Из имущества: картонные коробки и характер.", "Лови всех, качайся, собирай значки у бомжлидеров.", "Ходить: стрелки. Действие: Z. Меню: X."]))

    def draw(self, surf):
        surf.fill(PAPER)
        text(surf, "Выбери первого кореша", 150, 20, 22, INK, True)
        d = self.app.data
        for k, sid in enumerate(STARTERS):
            x = 30 + k * 150
            if k == self.menu.i:
                panel(surf, (x - 10, 70, 140, 200), (232, 240, 220))
            surf.blit(creature_sprite(d, sid, 100), (x, 80))
            text(surf, d.species[sid]["name"], x, 190, 16, INK, True)
            text(surf, "/".join(d.types[t]["name"] for t in d.species[sid]["types"]), x, 214, 13)
