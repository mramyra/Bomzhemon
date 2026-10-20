"""Экран слотов сохранения/загрузки."""
import time

from game.scenes.base import ChoiceScene, MessageScene, Scene
from game.systems import save
from game.ui.widgets import INK, PAPER, Menu, panel, text


def fmt_time(sec):
    h, m = divmod(int(sec) // 60, 60)
    return f"{h}ч {m:02d}м"


def slot_title(slot):
    return "Автосохранение" if slot == save.AUTO else f"Слот {slot}"


class SlotScene(Scene):
    """mode='save': выбрать слот и записать (on_done() после записи).
    mode='load': выбрать слот и загрузить (on_done(state) после загрузки).
    prepare - функция, которую вызываем перед записью (например, запомнить позицию игрока)."""
    blocks_console = True

    def __init__(self, app, mode, on_done=None, prepare=None):
        super().__init__(app)
        self.mode, self.on_done, self.prepare = mode, on_done, prepare
        self.refresh()
        st = app.state
        if mode == "save" and st and st.slot in [s for s, _ in self.rows]:
            self.menu.i = [s for s, _ in self.rows].index(st.slot)

    def refresh(self):
        self.rows = save.list_slots(data=self.app.data, with_auto=(self.mode == "load"))
        self.menu = Menu([""] * len(self.rows))

    # ---------------------------------------------------------------- действия
    def _location(self):
        st = self.app.state
        return self.app.data.districts.get(st.pos.get("map"), {}).get("name", "") if st else ""

    def _do_save(self, slot):
        try:
            if self.prepare:
                self.prepare()
            save.save(self.app.state, slot, location=self._location())
        except save.SaveError as e:
            self.app.push(MessageScene(self.app, [f"Ошибка: {e}"]))
            return
        self.app.pop()
        self.app.push(MessageScene(self.app, [f"Сохранено: {slot_title(slot)}."], on_done=self.on_done))

    def _do_load(self, slot):
        try:
            st = save.load(self.app.data, slot)
        except save.SaveError as e:
            self.app.push(MessageScene(self.app, [f"Не удалось загрузить: {e}."]))
            return
        if st is None:
            self.refresh()
            return
        self.app.pop()
        if self.on_done:
            self.on_done(st)

    def handle(self, a):
        r = self.menu.handle(a)
        if r == "back":
            self.app.pop()
            return
        if r != "ok":
            return
        slot, meta = self.rows[self.menu.i]
        if self.mode == "save":
            if meta is None:
                self._do_save(slot)
            else:
                self.app.push(ChoiceScene(self.app, f"{slot_title(slot)} занят. Перезаписать?", ["Перезаписать", "Отмена"],
                                          lambda i: self._do_save(slot) if i == 0 else None))
            return
        if meta is None:
            self.app.push(MessageScene(self.app, ["Слот пуст."]))
        elif not meta.get("ok"):
            self.app.push(ChoiceScene(self.app, f"{slot_title(slot)}: {meta.get('error', 'ошибка')}. Удалить этот файл?", ["Удалить", "Отмена"],
                                      lambda i: (save.delete(slot), self.refresh()) if i == 0 else None))
        else:
            self.app.push(ChoiceScene(self.app, f"{slot_title(slot)}: что сделать?", ["Загрузить", "Удалить", "Назад"], lambda i: self._after_choice(i, slot)))

    def _after_choice(self, i, slot):
        if i == 0:
            self._do_load(slot)
        elif i == 1:
            self.app.push(ChoiceScene(self.app, f"Удалить {slot_title(slot).lower()} насовсем?", ["Удалить", "Отмена"],
                                      lambda j: (save.delete(slot), self.refresh()) if j == 0 else None))

    # ---------------------------------------------------------------- рисование
    def draw(self, surf):
        surf.fill(PAPER)
        text(surf, "Сохранить игру" if self.mode == "save" else "Загрузить игру", 16, 8, 20, INK, True)
        for k, (slot, meta) in enumerate(self.rows):
            y = 40 + k * 68
            panel(surf, (10, y, 460, 62), (232, 240, 220) if k == self.menu.i else (255, 255, 255))
            text(surf, slot_title(slot), 20, y + 6, 15, INK, True)
            if meta is None:
                text(surf, "- пусто -", 20, y + 30, 14, (130, 130, 130))
            elif not meta.get("ok"):
                text(surf, f"Нельзя загрузить: {meta['error']}", 20, y + 30, 12, (170, 60, 50))
            else:
                text(surf, time.strftime("%d.%m.%Y %H:%M", time.localtime(meta["saved_at"])) + ("  (из резервной копии)" if meta.get("from_backup") else ""), 300, y + 8, 12)
                party = ", ".join(f"{p['name']} {p['level']}" for p in meta["party"][:4]) + (" ..." if len(meta["party"]) > 4 else "")
                text(surf, party or "команда пуста", 20, y + 26, 13)
                text(surf, f"{meta.get('location') or '-'}   Значков: {meta['badges']}   Бомждекс: {meta['dex']}   Монеты: {meta['money']}   {fmt_time(meta['play_seconds'])}", 20, y + 44, 12)
        text(surf, "Z - выбрать   X - назад", 16, 304, 11)
