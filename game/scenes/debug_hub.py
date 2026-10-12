"""Отладочный хаб: быстрые бои без ходьбы по карте. Удобно проверять баланс и эволюции."""
from game.scenes.base import MessageScene, Scene
from game.scenes import flow
from game.scenes.screens import BagScene, CraftScene, DexScene, PartyScene
from game.systems import save
from game.ui.widgets import INK, PAPER, Menu, text

DISTRICT = "dump"


class HubScene(Scene):
    def __init__(self, app):
        super().__init__(app)
        self.items = ["Дикий бой", "Бой с Михалычем (лидер)", "Бочка (вылечить всех)", "Команда", "Сумка", "Бомждекс", "Крафт", "В главное меню"]
        self.menu = Menu(self.items)

    def _guard(self):
        if self.app.state.has_usable():
            return True
        self.app.push(MessageScene(self.app, ["Все бойцы вырублены. Погрейся у бочки."]))
        return False

    def handle(self, a):
        if self.menu.handle(a) != "ok":
            return
        i, st, app = self.menu.i, self.app.state, self.app
        if i == 0 and self._guard():
            flow.start_wild(app, DISTRICT)
        elif i == 1 and self._guard():
            st.defeated.discard("leader_dump")
            flow.start_trainer(app, "leader_dump")
        elif i == 2:
            st.heal_party()
            app.push(MessageScene(app, ["Погрелся у бочки. Команда как новенькая."]))
        elif i == 3:
            app.push(PartyScene(app))
        elif i == 4:
            app.push(BagScene(app))
        elif i == 5:
            app.push(DexScene(app))
        elif i == 6:
            app.push(CraftScene(app))
        elif i == 7:
            from game.scenes.title import TitleScene
            app.replace(TitleScene(app))

    def draw(self, surf):
        surf.fill(PAPER)
        st = self.app.state
        text(surf, "Отладочный хаб", 20, 14, 20, INK, True)
        text(surf, f"Монеты: {st.money}   Значков: {len(st.badges)}   Бомждекс: {len(st.caught)}/{len(self.app.data.species)}", 20, 42, 14)
        self.menu.draw(surf, 20, 80, row_h=26, size=17)
