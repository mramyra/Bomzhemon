"""ПК: команда слева, ящики справа. Переносить, менять местами, смотреть подробности, сортировать, отпускать."""
import pygame

from game.scenes.base import ChoiceScene, MessageScene, Scene
from game.scenes.screens import CreatureScene, STATUS_RU, types_row
from game.systems import pc
from game.ui.sprites import creature_sprite
from game.ui.widgets import INK, PAPER, SHADE, hp_bar, panel, text

COLS, ROWS = 6, 5
CELL_W, CELL_H = 50, 41
ACCENT = (200, 70, 60)
HELD_FILL = (255, 240, 190)


class PCScene(Scene):
    blocks_console = True   # экран держит ссылки на состав команды

    def __init__(self, app):
        super().__init__(app)
        self.zone = "team"          # team | box | head
        self.team_i, self.box_i, self.page = 0, 0, 0
        self.held = None            # ("party"|"box", i) - что несём в руке

    # ---------------------------------------------------------------- вспомогательное
    @property
    def st(self):
        return self.app.state

    def _loc(self):
        if self.zone == "team":
            return ("party", self.team_i)
        return ("box", self.page * pc.BOX_SIZE + self.box_i)

    def _under_cursor(self):
        return pc.get(self.st, self._loc()) if self.zone != "head" else None

    def _fix(self):
        self.page = max(0, min(self.page, pc.pages(self.st) - 1))
        self.team_i = max(0, min(self.team_i, pc.PARTY_MAX - 1))

    def _say(self, lines):
        self.app.push(MessageScene(self.app, [lines] if isinstance(lines, str) else lines))

    # ---------------------------------------------------------------- ввод
    def handle(self, a):
        self._fix()
        z = self.zone
        if a == "back":
            if self.held:
                self.held = None
            else:
                self.app.pop()
            return
        if z == "team":
            if a == "up":
                self.team_i = max(0, self.team_i - 1)
            elif a == "down":
                self.team_i = min(pc.PARTY_MAX - 1, self.team_i + 1)
            elif a == "right":
                self.zone, self.box_i = "box", min(self.team_i, ROWS - 1) * COLS
            elif a == "ok":
                self._ok()
        elif z == "box":
            row, col = divmod(self.box_i, COLS)
            if a == "left":
                if col > 0:
                    self.box_i -= 1
                else:
                    self.zone, self.team_i = "team", min(row, pc.PARTY_MAX - 1)
            elif a == "right" and col < COLS - 1:
                self.box_i += 1
            elif a == "up":
                if row > 0:
                    self.box_i -= COLS
                else:
                    self.zone = "head"
            elif a == "down" and row < ROWS - 1:
                self.box_i += COLS
            elif a == "ok":
                self._ok()
        else:   # заголовок ящика
            n = pc.pages(self.st)
            if a == "left":
                self.page = (self.page - 1) % n
            elif a == "right":
                self.page = (self.page + 1) % n
            elif a == "down":
                self.zone = "box"
            elif a == "ok":
                self._sort_menu()

    def _ok(self):
        if self.held:
            dst = self._loc()
            try:
                msg = pc.move(self.st, self.held, dst)
            except pc.PCError as e:
                self._say(str(e))
                return
            self.held = None
            self._fix()
            self._say(msg)
            return
        c = self._under_cursor()
        if c is None:
            return
        loc = self._loc()
        quick = "В ПК" if loc[0] == "party" else "В команду"
        self.app.push(ChoiceScene(self.app, f"{c.name}  Lv{c.level}", ["Подробнее", "Переместить", quick, "Отпустить", "Назад"], lambda i: self._action(i, loc), cancel=4))

    def _action(self, i, loc):
        st = self.st
        c = pc.get(st, loc)
        if c is None:
            return
        try:
            if i == 0:
                pool = st.party if loc[0] == "party" else st.storage
                self.app.push(CreatureScene(self.app, loc[1], pool))
            elif i == 1:
                self.held = loc
            elif i == 2:
                self._say(pc.deposit(st, loc[1]) if loc[0] == "party" else pc.withdraw(st, loc[1]))
            elif i == 3:
                q = "Это легендарное существо! Точно отпустить? Вернуть его уже не получится." if c.species.get("legendary") else f"Отпустить {c.name}? Вернуть его уже не получится."
                self.app.push(ChoiceScene(self.app, q, ["Отпустить", "Оставить"], lambda j: self._release(j, loc)))
        except pc.PCError as e:
            self._say(str(e))
        self._fix()

    def _release(self, j, loc):
        if j != 0:
            return
        try:
            c = pc.release(self.st, loc)
        except pc.PCError as e:
            self._say(str(e))
            return
        self._fix()
        self._say(f"{c.name} уходит в подворотню. Удачи ему там.")

    def _sort_menu(self):
        modes = list(pc.SORT_MODES)
        self.app.push(ChoiceScene(self.app, "Сортировать существ в ПК:", [f"{pc.SORT_MODES[m].capitalize()}" for m in modes] + ["Назад"],
                                  lambda i: (pc.sort_box(self.app.data, self.st, modes[i]), self._say(f"Отсортировано {pc.SORT_MODES[modes[i]]}.")) if i < len(modes) else None))

    # ---------------------------------------------------------------- рисование
    def _cell_rect(self, k):
        row, col = divmod(k, COLS)
        return pygame.Rect(166 + col * CELL_W, 62 + row * CELL_H, CELL_W - 2, CELL_H - 2)

    def draw(self, surf):
        self._fix()
        surf.fill(PAPER)
        d, st = self.app.data, self.st
        text(surf, "ПК", 12, 8, 20, INK, True)
        text(surf, "Выброшенный системник. Знает всех твоих существ.", 50, 13, 12, (110, 110, 110))
        # --- команда
        panel(surf, (6, 34, 148, 238))
        text(surf, "Команда", 14, 38, 13, INK, True)
        for k in range(pc.PARTY_MAX):
            y = 56 + k * 36
            c = st.party[k] if k < len(st.party) else None
            held_here = self.held == ("party", k)
            if held_here:
                pygame.draw.rect(surf, HELD_FILL, (10, y, 140, 33), border_radius=4)
            pygame.draw.rect(surf, SHADE, (10, y, 140, 33), 1, border_radius=4)
            if c:
                surf.blit(creature_sprite(d, c.species_id, 28), (12, y + 2))
                text(surf, f"{c.name[:11]}", 44, y + 2, 13, INK, True)
                text(surf, f"Lv{c.level}", 44, y + 17, 11)
                hp_bar(surf, 78, y + 21, 66, c.hp, c.max_hp, 5)
            if self.zone == "team" and self.team_i == k:
                pygame.draw.rect(surf, ACCENT, (10, y, 140, 33), 3, border_radius=4)
        # --- ящик
        panel(surf, (160, 34, 314, 238))
        n = pc.pages(st)
        head = pygame.Rect(166, 38, 302, 20)
        if self.zone == "head":
            pygame.draw.rect(surf, (232, 240, 220), head, border_radius=4)
            pygame.draw.rect(surf, ACCENT, head, 3, border_radius=4)
        text(surf, f"Ящик {self.page + 1}/{n}", 270, 41, 14, INK, True)
        pygame.draw.polygon(surf, INK, [(180, 48), (190, 42), (190, 54)])
        pygame.draw.polygon(surf, INK, [(454, 48), (444, 42), (444, 54)])
        if self.zone == "head":
            text(surf, "Z - сортировка", 340, 43, 11, (110, 110, 110))
        for k in range(pc.BOX_SIZE):
            g = self.page * pc.BOX_SIZE + k
            c = st.storage[g] if g < len(st.storage) else None
            r = self._cell_rect(k)
            pygame.draw.rect(surf, HELD_FILL if self.held == ("box", g) else (255, 255, 255), r, border_radius=4)
            pygame.draw.rect(surf, SHADE, r, 1, border_radius=4)
            if c:
                surf.blit(creature_sprite(d, c.species_id, 30), (r.x + 9, r.y + 1))
                text(surf, f"Lv{c.level}", r.x + 14, r.y + 28, 10, INK)
                if c.pending_moves:
                    pygame.draw.circle(surf, (60, 150, 60), (r.right - 6, r.y + 6), 3)
        if self.zone == "box":
            pygame.draw.rect(surf, ACCENT, self._cell_rect(self.box_i), 3, border_radius=4)
        # --- рука
        if self.held:
            h = pc.get(st, self.held)
            if h:
                if self.zone == "box":
                    r = self._cell_rect(self.box_i)
                    pos = (r.right - 14, r.y - 8)
                elif self.zone == "team":
                    pos = (120, 56 + self.team_i * 36 - 8)
                else:
                    pos = (300, 20)
                surf.blit(creature_sprite(d, h.species_id, 26), pos)
        # --- инфо внизу
        panel(surf, (6, 276, 468, 38))
        c = pc.get(st, self.held) if self.held else self._under_cursor()
        if self.held and c:
            text(surf, f"В руке: {c.name} Lv{c.level}.  Выбери клетку и нажми Z, X - отмена. Занятая клетка - обмен.", 14, 285, 12)
        elif c:
            text(surf, f"{c.name}  Lv{c.level}", 14, 280, 14, INK, True)
            types_row(surf, d, c, 14, 297)
            hp_bar(surf, 130, 292, 90, c.hp, c.max_hp, 6)
            text(surf, f"HP {c.hp}/{c.max_hp}" + (f"  {STATUS_RU[c.status]}" if c.status else ""), 228, 288, 12)
            if c.pending_moves:
                text(surf, "ждёт новый приём", 330, 288, 12, (40, 110, 40), True)
            if c.species.get("legendary"):
                text(surf, "★ легендарное", 400, 280, 11, (150, 100, 20), True)
        else:
            text(surf, "Z - выбрать, X - назад. Влево/вправо - между командой и ящиком, вверх из ящика - сменить ящик.", 14, 285, 11)
