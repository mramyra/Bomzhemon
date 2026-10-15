from game.scenes.base import MessageScene, Scene
from game.scenes.debug_hub import HubScene
from game.scenes.world import WorldScene
from game.systems import save
from game.systems.state import PlayerState
from game.ui.sprites import creature_sprite
from game.ui.widgets import INK, PAPER, Menu, panel, text

STARTERS = ["khomechennok", "shchenok", "kotenok"]


class TitleScene(Scene):
    def __init__(self, app):
        super().__init__(app)
        self.items = ["Новая игра"] + (["Продолжить"] if save.exists(1) else []) + ["Отладочный хаб", "Выход"]
        self.menu = Menu(self.items)

    def handle(self, a):
        if self.menu.handle(a) != "ok":
            return
        it = self.items[self.menu.i]
        if it == "Новая игра":
            self.app.push(StarterScene(self.app))
        elif it == "Продолжить":
            self.app.state = save.load(self.app.data, 1)
            self.app.replace(WorldScene(self.app))
        elif it == "Отладочный хаб":
            d, st = self.app.data, PlayerState()
            st.add_creature(d.make_creature("shchenok", 12))
            st.add_creature(d.make_creature("krysa", 10))
            st.bag.update({"box": 10, "bread_crust": 3, "palto": 1, "bin_lid": 1, "syringe": 1})
            self.app.state = st
            self.app.replace(HubScene(self.app))
        else:
            self.app.stack.clear()

    def draw(self, surf):
        surf.fill(PAPER)
        text(surf, "БОМЖЕМОН", 140, 50, 48, INK, True)
        text(surf, "ловить всех. коробок хватит.", 150, 110, 16)
        self.menu.draw(surf, 190, 170, row_h=28, size=18)
        text(surf, "F11 - полный экран", 8, 300, 12)


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
            self.app.state = st
            self.app.replace(WorldScene(self.app))
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
