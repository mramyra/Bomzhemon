"""Экран боя: проигрывает события движка (game.battle.engine.Battle)."""
import pygame

from game.battle.engine import Battle
from game.scenes.base import Scene
from game.ui.sprites import creature_sprite
from game.ui.widgets import INK, PAPER, SHADE, Menu, font, hp_bar, panel, text, wrap, arrow

STATUS_TAG = {"psn": "ЯД", "brn": "ОЖ", "par": "ТРМ", "slp": "СОН"}


class BattleScene(Scene):
    def __init__(self, app, battle: Battle, on_done):
        super().__init__(app)
        self.b, self.on_done = battle, on_done
        self.disp = {"player": None, "enemy": None}
        self.queue = battle.start()
        self.phase, self.msg, self.wait_key, self.anim = "play", "", False, None
        self.main = Menu(["БОЙ", "СУМКА", "КОМАНДА", "БЕЖАТЬ"], cols=2)
        self.moves = self.party = self.bag = None
        self.bag_item = None
        self._next()

    # ------------------------------------------------ воспроизведение событий
    def _next(self):
        while self.queue:
            e = self.queue.pop(0)
            t = e["t"]
            if t == "msg":
                self.msg, self.wait_key = e["text"], True
                return
            if t == "hp":
                d = self.disp[e["side"]]
                d["hp_shown"] = float(e["from"])
                self.anim = e
                return
            if t in ("switch_in", "level"):
                self.disp[e["side"]] = dict(e, hp_shown=float(e["hp"]))
            elif t == "status":
                self.disp[e["side"]]["status"] = e["status"]
            elif t == "faint":
                self.disp[e["side"]]["gone"] = True
            elif t == "end":
                pass
        # события кончились
        if self.b.over:
            self.app.pop()
            self.on_done(self.b.result)
        elif self.b.awaiting_switch:
            self._open_party(forced=True)
        else:
            self.phase, self.msg = "choose", f"Что делать, {self.b.player.mon.name}?"
            self.main.i = 0

    def _submit(self, action):
        self.queue = self.b.submit(action)
        self.phase = "play"
        self._next()

    def update(self, dt):
        if self.anim:
            e = self.anim
            d = self.disp[e["side"]]
            step = max(1.0, e["max"] * 0.9) * dt * 1.4 + 0.05
            if d["hp_shown"] > e["to"]:
                d["hp_shown"] = max(e["to"], d["hp_shown"] - step)
            else:
                d["hp_shown"] = min(e["to"], d["hp_shown"] + step)
            if d["hp_shown"] == e["to"]:
                d["hp"] = e["to"]
                self.anim = None
                self._next()

    # ------------------------------------------------ ввод
    def _open_party(self, forced=False):
        self.phase = "forced" if forced else "party"
        self.party = Menu([f"{c.name}  Lv{c.level}  {c.hp}/{c.max_hp}" for c in self.b.player.party])
        self.party.i = self.b.player.active
        self.msg = "Кого выпустить?"

    def handle(self, a):
        ph = self.phase
        if ph == "play":
            if self.wait_key and a == "ok" and not self.anim:
                self.wait_key = False
                self._next()
        elif ph == "choose":
            r = self.main.handle(a)
            if r == "ok":
                i = self.main.i
                if i == 0:
                    ms = self.b.player.mon.moves
                    if not self.b.usable_slots(self.b.player):
                        self._submit(("move", -1))
                        return
                    self.moves = Menu([m["id"] for m in ms])
                    self.phase = "moves"
                elif i == 1:
                    inv = [(k, n) for k, n in self.b.bag.items() if n > 0 and self.app.data.items[k]["kind"] in ("catch", "heal", "cure") and (self.b.wild or self.app.data.items[k]["kind"] != "catch")]
                    self.bag = (inv, Menu([f"{self.app.data.items[k]['name']} x{n}" for k, n in inv] or ["(пусто)"]))
                    self.phase = "bag"
                elif i == 2:
                    self._open_party()
                else:
                    self._submit(("run",))
        elif ph == "moves":
            r = self.moves.handle(a)
            if r == "back":
                self.phase = "choose"
            elif r == "ok":
                self._submit(("move", self.moves.i))
        elif ph == "bag":
            inv, menu = self.bag
            r = menu.handle(a)
            if r == "back":
                self.phase = "choose"
            elif r == "ok" and inv:
                item = inv[menu.i][0]
                if self.app.data.items[item]["kind"] == "catch":
                    self._submit(("item", item))
                else:
                    self.bag_item = item
                    self._open_party()
                    self.phase = "item_target"
        elif ph in ("party", "forced", "item_target"):
            r = self.party.handle(a)
            if r == "back" and ph != "forced":
                self.phase = "choose"
            elif r == "ok":
                if ph == "item_target":
                    self._submit(("item", self.bag_item, self.party.i))
                else:
                    self._submit(("switch", self.party.i))

    # ------------------------------------------------ рисование
    def _info(self, surf, rect, d, show_num):
        panel(surf, rect)
        x, y, w, _ = rect
        text(surf, d["name"], x + 10, y + 6, 16, bold=True)
        text(surf, f"Lv{d['level']}", x + w - 52, y + 6, 14)
        if d.get("status"):
            text(surf, STATUS_TAG[d["status"]], x + 10, y + 27, 12, (160, 60, 60), True)
        text(surf, "HP", x + 40, y + 28, 11)
        hp_bar(surf, x + 60, y + 31, w - 76, d["hp_shown"], d["max"])
        if show_num:
            text(surf, f"{int(round(d['hp_shown']))}/{d['max']}", x + w - 82, y + 42, 12)

    def draw(self, surf):
        surf.fill(PAPER)
        pygame.draw.rect(surf, (200, 220, 190), (0, 0, 480, 150))
        pygame.draw.rect(surf, (172, 190, 160), (0, 150, 480, 82))
        pygame.draw.ellipse(surf, SHADE, (270, 100, 170, 30))
        pygame.draw.ellipse(surf, SHADE, (30, 180, 190, 36))
        data = self.app.data
        e, p = self.disp["enemy"], self.disp["player"]
        if e and not e.get("gone"):
            surf.blit(creature_sprite(data, e["species"], 96), (305, 28))
        if p and not p.get("gone"):
            surf.blit(creature_sprite(data, p["species"], 120, back=True), (50, 98))
        if e:
            self._info(surf, (14, 14, 210, 56), e, False)
        if p:
            self._info(surf, (250, 150, 216, 66), p, True)
        # нижняя панель
        panel(surf, (8, 232, 464, 80))
        ph = self.phase
        if ph in ("play", "choose", "forced", "party", "item_target"):
            for k, ln in enumerate(wrap(self.msg, 250 if ph == "choose" else 440)[:3]):
                text(surf, ln, 20, 242 + k * 22)
        if ph == "play" and self.wait_key and not self.anim:
            arrow(surf, 452, 292, 6)
        if ph == "choose":
            self.main.draw(surf, 290, 246, 90, 26, 16)
        elif ph == "moves":
            mv = self.app.data.moves
            slots = self.b.player.mon.moves
            for k, m in enumerate(slots):
                x, y = 28 + (k % 2) * 200, 244 + (k // 2) * 28
                if k == self.moves.i:
                    arrow(surf, x - 14, y + 3, 7)
                text(surf, mv[m["id"]]["name"], x, y, 15)
                text(surf, f"{m['pp']}/{m['max_pp']}", x + 130, y + 2, 12)
            cur = mv[slots[self.moves.i]["id"]]
            text(surf, f"{data.types[cur['type']]['name']}  сила {cur['power'] or '-'}", 28, 296, 12)
        elif ph == "bag":
            self.bag[1].draw(surf, 28, 244, size=15)
        elif ph in ("party", "forced", "item_target"):
            # список команды поверх сцены
            panel(surf, (110, 20, 260, 200))
            self.party.draw(surf, 124, 32, 240, 30, 15)
