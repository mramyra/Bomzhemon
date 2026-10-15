"""Экраны, общие для меню на карте и отладочного хаба: команда, бомждекс, крафт, сумка."""
import pygame

from game.scenes.base import MessageScene, Scene
from game.systems import evolution, fusion, moveset, trade
from game.ui.sprites import creature_sprite
from game.ui.widgets import INK, PAPER, SHADE, Menu, font, hp_bar, panel, text, wrap


STAT_ROWS = [("hp", "HP"), ("atk", "Атака"), ("def", "Защита"), ("spa", "Спец. атака"), ("spd", "Спец. защита"), ("spe", "Скорость")]
EXP_COL, ACCENT_ROW = (90, 140, 220), (200, 70, 60)
STATUS_RU = {"psn": "отравлен", "brn": "обожжён", "par": "тремор", "slp": "спит"}


def type_chip(surf, data, tid, x, y):
    t = data.types[tid]
    w = font(11).size(t["name"])[0] + 10
    pygame.draw.rect(surf, tuple(t["color"]), (x, y, w, 15), border_radius=4)
    pygame.draw.rect(surf, INK, (x, y, w, 15), 1, border_radius=4)
    text(surf, t["name"], x + 5, y + 1, 11)
    return w + 4


def types_row(surf, data, c, x, y):
    for t in c.types:
        x += type_chip(surf, data, t, x, y)


def exp_bar(surf, x, y, w, frac, h=7):
    pygame.draw.rect(surf, SHADE, (x, y, w, h), border_radius=3)
    if frac > 0:
        pygame.draw.rect(surf, EXP_COL, (x, y, max(2, int(w * frac)), h), border_radius=3)
    pygame.draw.rect(surf, INK, (x, y, w, h), 1, border_radius=3)


def move_line(data, mv):
    m = data.moves[mv["id"]]
    return f"{moveset.CATEGORY_RU[m['category']]}  сила {m['power'] or '-'}  точн. {m['accuracy'] or '-'}"


class PartyScene(Scene):
    """Список команды. Z - действия (подробнее / переставить), X - назад."""
    blocks_console = True   # экран держит ссылки на состав команды: консоль поверх него не открываем


    def __init__(self, app):
        super().__init__(app)
        self.menu = Menu([""] * len(app.state.party))
        self.actions = Menu(["Подробнее", "Переставить", "Назад"])
        self.mode, self.src = "list", None

    def handle(self, a):
        party = self.app.state.party
        if self.mode == "list":
            r = self.menu.handle(a)
            if r == "back":
                self.app.pop()
            elif r == "ok":
                self.mode, self.actions.i = "actions", 0
        elif self.mode == "actions":
            r = self.actions.handle(a)
            if r == "back":
                self.mode = "list"
            elif r == "ok":
                i = self.actions.i
                self.mode = "list"
                if i == 0:
                    self.app.push(CreatureScene(self.app, self.menu.i))
                elif i == 1 and len(party) > 1:
                    self.src, self.mode = self.menu.i, "reorder"
        else:
            r = self.menu.handle(a)
            if r == "back":
                self.menu.i, self.mode = self.src, "list"
            elif r == "ok":
                if self.menu.i != self.src:
                    party[self.src], party[self.menu.i] = party[self.menu.i], party[self.src]
                self.mode = "list"

    def draw(self, surf):
        surf.fill(PAPER)
        d, st = self.app.data, self.app.state
        text(surf, "Команда", 16, 8, 20, INK, True)
        text(surf, {"list": "Z - выбрать   X - назад", "actions": "", "reorder": "Выбери, с кем поменять местами"}[self.mode], 120, 12, 13)
        for k, c in enumerate(st.party):
            y = 38 + k * 46
            sel = k == self.menu.i
            panel(surf, (10, y, 460, 42), (232, 240, 220) if sel else (255, 255, 255))
            if self.mode == "reorder" and k == self.src:
                pygame.draw.rect(surf, ACCENT_ROW, (10, y, 460, 42), 3, border_radius=6)
            surf.blit(creature_sprite(d, c.species_id, 36), (14, y + 3))
            text(surf, f"{c.name}  Lv{c.level}", 58, y + 4, 15, INK, True)
            types_row(surf, d, c, 58, y + 23)
            hp_bar(surf, 230, y + 8, 120, c.hp, c.max_hp)
            text(surf, f"{c.hp}/{c.max_hp}", 360, y + 3, 12)
            exp_bar(surf, 230, y + 26, 120, c.exp_progress()[2], 5)
            text(surf, "оп.", 206, y + 22, 11)
            if c.status:
                text(surf, STATUS_RU[c.status], 410, y + 4, 12, (160, 60, 60), True)
            if c.pending_moves:
                text(surf, "новый приём!", 380, y + 24, 12, (40, 110, 40), True)
        text(surf, f"В заначке: {len(st.storage)}", 16, 302, 12)
        if self.mode == "actions":
            panel(surf, (330, 40 + self.menu.i * 46, 130, 74))
            self.actions.draw(surf, 340, 46 + self.menu.i * 46, row_h=22, size=14)


class CreatureScene(Scene):
    """Подробности существа. <-/-> вкладки, на 1-й вкладке вверх/вниз - другое существо.
    На вкладке приёмов: Z - выбрать приём, Z на другом - поменять местами; нижняя строка - ждущие выучки."""
    blocks_console = True   # экран держит ссылки на состав команды: консоль поверх него не открываем


    def __init__(self, app, idx):
        super().__init__(app)
        self.idx, self.page, self.mcur, self.swap_from = idx, 0, 0, None

    @property
    def c(self):
        return self.app.state.party[self.idx]

    def _rows(self):
        return len(self.c.moves) + (1 if self.c.pending_moves else 0)

    def _clamp(self):
        self.mcur = max(0, min(self.mcur, self._rows() - 1))

    def handle(self, a):
        n = len(self.app.state.party)
        if a == "back":
            if self.swap_from is not None:
                self.swap_from = None
            else:
                self.app.pop()
        elif a in ("left", "right"):
            self.page ^= 1
            self.swap_from, self.mcur = None, 0
        elif self.page == 0:
            if a == "up":
                self.idx = (self.idx - 1) % n
            elif a == "down":
                self.idx = (self.idx + 1) % n
        else:
            self._clamp()
            if a == "up":
                self.mcur = (self.mcur - 1) % self._rows()
            elif a == "down":
                self.mcur = (self.mcur + 1) % self._rows()
            elif a == "ok":
                if self.mcur < len(self.c.moves):
                    if self.swap_from is None:
                        self.swap_from = self.mcur
                    else:
                        moveset.swap_moves(self.c, self.swap_from, self.mcur)
                        self.swap_from = None
                else:
                    self.swap_from = None
                    learn_chain(self.app, [self.c], None)

    def draw(self, surf):
        surf.fill(PAPER)
        self._clamp()
        d, c = self.app.data, self.c
        for k, name in enumerate(["Характеристики", "Приёмы"]):
            x = 14 + k * 130
            panel(surf, (x, 6, 122, 26), (232, 240, 220) if k == self.page else (240, 238, 230))
            text(surf, name, x + 10, 11, 14, INK, k == self.page)
        text(surf, f"{self.idx + 1}/{len(self.app.state.party)}", 440, 12, 13)
        (self._draw_stats if self.page == 0 else self._draw_moves)(surf, d, c)

    def _draw_stats(self, surf, d, c):
        panel(surf, (10, 38, 460, 262))
        surf.blit(creature_sprite(d, c.species_id, 96), (20, 46))
        text(surf, f"{c.name}", 130, 46, 20, INK, True)
        text(surf, f"Lv{c.level}", 130, 72, 15)
        types_row(surf, d, c, 180, 74)
        text(surf, "HP", 130, 98, 13)
        hp_bar(surf, 152, 101, 190, c.hp, c.max_hp)
        text(surf, f"{c.hp}/{c.max_hp}" + (f"   {STATUS_RU[c.status]}" if c.status else ""), 352, 96, 13)
        got, need, frac = c.exp_progress()
        text(surf, "Опыт", 130, 118, 13)
        exp_bar(surf, 176, 121, 166, frac)
        if need:
            text(surf, f"{got}/{need}", 352, 116, 13)
            text(surf, f"До следующего уровня: {need - got}", 130, 134, 13)
        else:
            text(surf, "Максимальный уровень", 130, 134, 13)
        text(surf, f"Всего опыта: {c.exp}", 130, 150, 12, (90, 90, 90))
        for k, (key, name) in enumerate(STAT_ROWS):
            y = 176 + k * 20
            v = c.max_hp if key == "hp" else c.stat(key)
            base = c.species["base"][key]
            text(surf, name, 24, y, 14)
            text(surf, str(v), 140, y, 14, INK, True)
            exp_bar(surf, 180, y + 5, 80, min(1.0, v / 160))
            text(surf, f"база {base}", 266, y + 2, 11, (110, 110, 110))
        for k, ln in enumerate(wrap(c.species["desc"], 190, 13)[:4]):
            text(surf, ln, 340, 176 + k * 16, 13)
        for k, ln in enumerate(moveset.evolution_hints(d, c)[:3]):
            text(surf, ln, 340, 244 + k * 16, 12, (90, 60, 40))
        text(surf, "<- ->: приёмы   вверх/вниз: другое существо   X: назад", 20, 304, 11)

    def _draw_moves(self, surf, d, c):
        for k in range(4):
            y = 38 + k * 44
            panel(surf, (10, y, 460, 40), (232, 240, 220) if k == self.mcur else (255, 255, 255))
            if k == self.swap_from:
                pygame.draw.rect(surf, ACCENT_ROW, (10, y, 460, 40), 3, border_radius=6)
            if k < len(c.moves):
                mv = c.moves[k]
                m = d.moves[mv["id"]]
                text(surf, m["name"], 28, y + 4, 16, INK, True)
                type_chip(surf, d, m["type"], 28, y + 22)
                text(surf, move_line(d, mv), 100, y + 23, 12)
                text(surf, f"PP {mv['pp']}/{mv['max_pp']}", 400, y + 12, 14)
            else:
                text(surf, "- пусто -", 28, y + 12, 14, (130, 130, 130))
        if c.pending_moves:
            y = 38 + 4 * 44
            panel(surf, (10, y, 460, 28), (232, 240, 220) if self.mcur == len(c.moves) else (255, 255, 255))
            text(surf, f"Хочет выучить: {d.moves[c.pending_moves[0]]['name']}" + (f" (+{len(c.pending_moves) - 1})" if len(c.pending_moves) > 1 else "") + "   Z - решить", 28, y + 5, 14, (40, 110, 40), True)
        if self.mcur < len(c.moves):
            sel = c.moves[self.mcur]["id"]
            panel(surf, (10, 262, 460, 40))
            for k, ln in enumerate(wrap(moveset.describe_move(d, sel), 440, 13)[:2]):
                text(surf, ln, 20, 266 + k * 16, 13)
        hint = "Выбери приём, с которым поменять местами. X - отмена" if self.swap_from is not None else "Z - переставить приёмы   <- ->: характеристики   X: назад"
        text(surf, hint, 20, 304, 11)


class LearnMoveScene(Scene):
    """Существо хочет выучить приём, но их уже 4: выбираем, какой забыть. X - решить позже."""
    blocks_console = True   # экран держит ссылки на состав команды: консоль поверх него не открываем


    def __init__(self, app, c, move_id, on_done=None):
        super().__init__(app)
        self.c, self.mid, self.on_done = c, move_id, on_done
        self.menu = Menu([""] * (len(c.moves) + 1))

    def _finish(self, lines=None):
        self.app.pop()
        if lines:
            self.app.push(MessageScene(self.app, lines, self.on_done))
        elif self.on_done:
            self.on_done()

    def handle(self, a):
        r = self.menu.handle(a)
        d, c = self.app.data, self.c
        if r == "back":
            self._finish()
        elif r == "ok":
            new = d.moves[self.mid]["name"]
            if self.menu.i == len(c.moves):
                moveset.decline_move(c, self.mid)
                self._finish([f"{c.name} не стал учить «{new}»."])
            else:
                old = moveset.learn_move(d, c, self.mid, self.menu.i)
                self._finish([f"{c.name} забыл «{d.moves[old]['name']}» и выучил «{new}»!"] if old else [f"{c.name} и так знает «{new}»."])

    def draw(self, surf):
        surf.fill(PAPER)
        d, c = self.app.data, self.c
        m = d.moves[self.mid]
        text(surf, f"{c.name} хочет выучить «{m['name']}»", 16, 8, 18, INK, True)
        text(surf, "Какой приём забыть?", 16, 32, 14)
        panel(surf, (10, 54, 460, 44), (226, 238, 214))
        type_chip(surf, d, m["type"], 20, 60)
        text(surf, f"{moveset.CATEGORY_RU[m['category']]}  сила {m['power'] or '-'}  точн. {m['accuracy'] or '-'}  PP {m['pp']}", 100, 61, 13)
        text(surf, moveset.describe_move(d, self.mid), 20, 78, 12)
        for k, mv in enumerate(c.moves):
            y = 108 + k * 34
            panel(surf, (10, y, 460, 30), (232, 240, 220) if k == self.menu.i else (255, 255, 255))
            cm = d.moves[mv["id"]]
            text(surf, cm["name"], 28, y + 6, 15, INK, True)
            type_chip(surf, d, cm["type"], 200, y + 7)
            text(surf, move_line(d, mv), 270, y + 8, 12)
        y = 108 + len(c.moves) * 34
        panel(surf, (10, y, 460, 30), (232, 240, 220) if self.menu.i == len(c.moves) else (255, 255, 255))
        text(surf, f"Не учить «{m['name']}»", 28, y + 6, 15)
        text(surf, "Z - выбрать   X - решить позже", 20, 304, 11)


def learn_chain(app, creatures, on_done=None):
    """По очереди предлагает выучить ждущие приёмы: свободная ячейка - учит сразу, иначе спрашивает, что забыть."""
    todo = [(c, m) for c in creatures for m in c.pending_moves]

    def step():
        while todo:
            c, m = todo.pop(0)
            if m not in c.pending_moves:
                continue
            if any(x["id"] == m for x in c.moves):      # уже знает - молча убираем из очереди
                moveset.decline_move(c, m)
                continue
            if len(c.moves) < 4:
                moveset.learn_move(app.data, c, m)
                app.push(MessageScene(app, [f"{c.name} выучил «{app.data.moves[m]['name']}»!"], on_done=step))
            else:
                app.push(LearnMoveScene(app, c, m, on_done=step))
            return
        if on_done:
            on_done()
    step()


class DexScene(Scene):
    def __init__(self, app):
        super().__init__(app)
        self.ids = list(app.data.species)
        self.menu = Menu([""] * len(self.ids))

    def handle(self, a):
        if self.menu.handle(a) == "back":
            self.app.pop()

    def draw(self, surf):
        surf.fill(PAPER)
        d, st = self.app.data, self.app.state
        text(surf, f"Бомждекс  {len(st.caught)}/{len(self.ids)}", 16, 8, 20, INK, True)
        top = max(0, min(self.menu.i - 5, len(self.ids) - 11))
        for row, k in enumerate(range(top, min(top + 11, len(self.ids)))):
            sid, y = self.ids[k], 40 + row * 24
            nm = d.species[sid]["name"] if sid in st.seen else "???"
            mark = "●" if sid in st.caught else ("○" if sid in st.seen else " ")
            if k == self.menu.i:
                pygame.draw.rect(surf, (226, 232, 214), (10, y - 2, 200, 22))
            text(surf, f"{k + 1:02d} {nm}", 16, y, 15)
            if sid in st.caught:
                pygame.draw.circle(surf, INK, (196, y + 9), 4)
        sid = self.ids[self.menu.i]
        panel(surf, (230, 36, 240, 270))
        if sid in st.seen:
            sp = d.species[sid]
            surf.blit(creature_sprite(d, sid, 110), (290, 42))
            text(surf, sp["name"], 244, 156, 17, INK, True)
            text(surf, "/".join(d.types[t]["name"] for t in sp["types"]), 244, 178, 13)
            for k, ln in enumerate(wrap(sp["desc"], 214, 13)[:4]):
                text(surf, ln, 244, 200 + k * 16, 13)
            if sp.get("legendary"):
                text(surf, "★ Легендарное", 244, 252, 12, (150, 100, 20), True)
            for k, ln in enumerate(moveset.species_evolution_hints(d, sid)[:3]):
                text(surf, ln, 244, 268 + k * 14, 12, (90, 60, 40))
        else:
            text(surf, "Не встречен", 300, 150, 16)


class CraftScene(Scene):
    blocks_console = True   # экран держит ссылки на состав команды: консоль поверх него не открываем

    def __init__(self, app):
        super().__init__(app)
        self.refresh()

    def refresh(self):
        d, st = self.app.data, self.app.state
        self.avail = {f["id"] for f in fusion.available(d, st)}
        self.menu = Menu([f["name"] for f in d.fusions])

    def handle(self, a):
        r = self.menu.handle(a)
        if r == "back":
            self.app.pop()
        elif r == "ok":
            f = self.app.data.fusions[self.menu.i]
            res = fusion.craft(self.app.data, self.app.state, f["id"])
            self.app.push(MessageScene(self.app, [f"Из {sum(f['inputs'].values())} существ получился {res.name} (Lv{res.level})!" if res else "Не хватает существ для крафта."]))
            self.refresh()

    def draw(self, surf):
        surf.fill(PAPER)
        d, st = self.app.data, self.app.state
        text(surf, "Крафт", 16, 8, 20, INK, True)
        self.menu.draw(surf, 16, 44, row_h=28, size=17)
        f = d.fusions[self.menu.i]
        have = {}
        for c in st.party + st.storage:
            have[c.species_id] = have.get(c.species_id, 0) + 1
        for k, (sp, n) in enumerate(f["inputs"].items()):
            text(surf, f"{d.species[sp]['name']}: {have.get(sp, 0)}/{n}", 16, 220 + k * 20, 15)
        text(surf, "Доступно" if f["id"] in self.avail else "Не хватает", 16, 290, 14)


class BagScene(Scene):
    blocks_console = True   # экран держит ссылки на состав команды: консоль поверх него не открываем

    def __init__(self, app):
        super().__init__(app)
        self.stage = "items"
        self.refresh()

    def refresh(self):
        st, d = self.app.state, self.app.data
        self.inv = [(k, n) for k, n in st.bag.items() if n > 0]
        self.menu = Menu([f"{d.items[k]['name']} x{n}" for k, n in self.inv] or ["(пусто)"])
        self.target = Menu([f"{c.name} Lv{c.level} {c.hp}/{c.max_hp}" for c in st.party])

    def handle(self, a):
        if self.stage == "items":
            r = self.menu.handle(a)
            if r == "back":
                self.app.pop()
            elif r == "ok" and self.inv:
                kind = self.app.data.items[self.inv[self.menu.i][0]]["kind"]
                if kind in ("heal", "cure", "evolution"):
                    self.stage = "target"
                else:
                    self.app.push(MessageScene(self.app, ["Это пригодится в бою."]))
        else:
            r = self.target.handle(a)
            if r == "back":
                self.stage = "items"
            elif r == "ok":
                self.use(self.inv[self.menu.i][0], self.app.state.party[self.target.i])

    def use(self, item_id, c):
        d, st = self.app.data, self.app.state
        it = d.items[item_id]
        msg = None
        if it["kind"] == "heal" and 0 < c.hp < c.max_hp:
            c.hp = min(c.max_hp, c.hp + it["amount"])
            msg = f"{c.name} подкрепился."
        elif it["kind"] == "cure" and c.status in it["cures"]:
            c.status = None
            msg = f"{c.name} отпустило."
        elif it["kind"] == "evolution":
            into = evolution.item_evolution(c, item_id)
            if into:
                old = c.name
                evolution.evolve(d, c, into)
                msg = f"{old} эволюционировал в {c.species['name']}!"
        if msg:
            st.bag[item_id] -= 1
        self.app.push(MessageScene(self.app, [msg or "Это ничего не даст."]))
        self.stage = "items"
        self.refresh()

    def draw(self, surf):
        surf.fill(PAPER)
        text(surf, "Сумка", 16, 8, 20, INK, True)
        self.menu.draw(surf, 16, 44, row_h=26, size=16)
        if self.inv:
            text(surf, self.app.data.items[self.inv[self.menu.i][0]]["desc"], 16, 290, 14)
        if self.stage == "target":
            panel(surf, (220, 40, 250, 180))
            self.target.draw(surf, 232, 52, row_h=28, size=14)


class TradeScene(Scene):
    """Меняла: отдаёшь существо - получаешь другое, а оно эволюционирует (эволюция по обмену)."""
    blocks_console = True   # экран держит ссылки на состав команды: консоль поверх него не открываем


    def __init__(self, app):
        super().__init__(app)
        self.stage, self.sel, self.opt = "pick", None, None
        self.refresh()

    def refresh(self):
        d, st = self.app.data, self.app.state
        self.rows = trade.tradable(d, st)
        self.menu = Menu([f"{c.name}  Lv{c.level}" for c, _ in self.rows] or ["(нечего менять)"])
        self.opts = Menu([""])
        self.confirm = Menu(["Обменять", "Назад"])

    def handle(self, a):
        d = self.app.data
        if self.stage == "pick":
            r = self.menu.handle(a)
            if r == "back" or (r == "ok" and not self.rows):
                self.app.pop()
            elif r == "ok":
                self.sel = self.rows[self.menu.i]
                self.opts = Menu([f"{d.species[rs]['name']} (станет: {d.species[into]['name']})" for rs, into in self.sel[1]])
                self.stage = "opts"
        elif self.stage == "opts":
            r = self.opts.handle(a)
            if r == "back":
                self.stage = "pick"
            elif r == "ok":
                self.opt, self.confirm.i, self.stage = self.sel[1][self.opts.i], 0, "confirm"
        else:
            r = self.confirm.handle(a)
            if r == "back" or (r == "ok" and self.confirm.i == 1):
                self.stage = "opts"
            elif r == "ok":
                give, (rs, into) = self.sel[0], self.opt
                old = give.name
                self.stage = "pick"
                try:
                    new = trade.execute(d, self.app.state, give, rs, into)
                except ValueError:      # пока окно было открыто, состав команды изменился
                    self.refresh()
                    self.app.push(MessageScene(self.app, ["Меняла: Что-то поменялось, давай заново."]))
                    return
                self.refresh()
                self.app.push(MessageScene(self.app, [f"Меняла забирает {old} и отдаёт {d.species[rs]['name']}.", f"{d.species[rs]['name']} тут же превращается: {new.name}!"]))

    def draw(self, surf):
        surf.fill(PAPER)
        d = self.app.data
        text(surf, "Меняла", 16, 8, 20, INK, True)
        text(surf, "Отдай существо - получишь другое. Обмен меняет не только владельца.", 16, 34, 13)
        if not self.rows:
            text(surf, "Тебе нечего мне предложить.", 16, 70, 15)
            wanted = sorted({e["partner"] for sp in d.species.values() for e in sp["evolutions"] if e["method"] == "trade"})
            for k, ln in enumerate(wrap("Нужны существа: " + ", ".join(d.species[w]["name"] for w in wanted), 440, 13)):
                text(surf, ln, 16, 96 + k * 16, 13)
            return
        self.menu.draw(surf, 16, 62, row_h=24, size=15)
        if self.stage == "pick":
            for k, ln in enumerate(wrap("Получишь: " + "; ".join(f"{d.species[rs]['name']} - станет {d.species[into]['name']}" for rs, into in self.rows[self.menu.i][1]), 200, 12)):
                text(surf, ln, 250, 66 + k * 14, 12)
        else:
            panel(surf, (230, 56, 240, 200))
            if self.stage == "opts":
                text(surf, f"За {self.sel[0].name} можно получить:", 240, 62, 13)
                self.opts.draw(surf, 240, 86, row_h=26, size=13)
            else:
                rs, into = self.opt
                text(surf, f"Отдать: {self.sel[0].name}", 240, 66, 14)
                text(surf, f"Получить: {d.species[rs]['name']}", 240, 88, 14)
                text(surf, f"(станет: {d.species[into]['name']})", 240, 108, 13)
                self.confirm.draw(surf, 240, 140, row_h=26, size=15)
