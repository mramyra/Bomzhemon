"""Мир: ходьба по карте из Tiled, встречи, предметы, бочка, баки, тренеры и бомжлидер."""
import random

import pygame

from game.core import paths
from game.scenes import flow
from game.scenes.base import MessageScene, Scene
from game.scenes.exit_flow import ask_exit
from game.scenes.pc import PCScene
from game.scenes.saveload import SlotScene
from game.scenes.transition import TransitionScene
from game.scenes.screens import BagScene, CraftScene, DexScene, PartyScene, TradeScene
from game.systems import save
from game.ui.widgets import INK, Menu, panel, text
from game.world.mapdata import DIRS, MapData

DEFAULT_DISTRICT = "dump"   # район по умолчанию (новая игра, неизвестный район в сохранении)
SPEED = 5.0             # клеток в секунду
ENCOUNTER_CHANCE = 0.12  # шанс встречи за шаг по тайлу с encounter
ITEM_SPOT_FILL = 0.55    # доля точек, где в этой игре лежит предмет (по сиду сохранения)
BANNER_SECONDS = 2.5
T, VIEW = 32, (480, 320)

COATS = {"trader": (70, 150, 110), "player": (96, 104, 124), "granny_zina": (176, 80, 120), "tramp_petya": (120, 100, 60), "leader_dump": (160, 50, 40),
         "porter_vasya": (60, 110, 150), "kassirsha_lyuda": (150, 90, 150), "leader_vokzal": (70, 70, 140)}


def migrate_flags(st):
    """Флаги карты теперь по районам: picked/opened = {район: [id объектов]}, checkpoint = {map, x, y}. Старый формат (списки) = район dump."""
    for key in ("picked", "opened"):
        v = st.flags.get(key)
        if isinstance(v, list):
            st.flags[key] = {DEFAULT_DISTRICT: v}
        elif not isinstance(v, dict):
            st.flags[key] = {}
    cp = st.flags.get("checkpoint")
    if isinstance(cp, list) and len(cp) == 2:
        st.flags["checkpoint"] = {"map": DEFAULT_DISTRICT, "x": cp[0], "y": cp[1]}
    elif cp is not None and not isinstance(cp, dict):
        st.flags.pop("checkpoint", None)


def draw_person(surf, x, y, face, coat, hat=(40, 40, 50)):
    pygame.draw.ellipse(surf, (70, 70, 70), (x + 6, y + 25, 20, 7))
    pygame.draw.rect(surf, coat, (x + 8, y + 14, 16, 14))
    pygame.draw.rect(surf, INK, (x + 8, y + 14, 16, 14), 2)
    pygame.draw.rect(surf, (236, 200, 160), (x + 10, y + 3, 12, 11))
    pygame.draw.rect(surf, INK, (x + 10, y + 3, 12, 11), 1)
    pygame.draw.rect(surf, hat, (x + 8, y + 1, 16, 5))
    if face != "up":
        sh = {"left": -3, "right": 3}.get(face, 0)
        for ex in (13, 18):
            pygame.draw.rect(surf, INK, (x + ex + sh, y + 8, 2, 2))


class WorldScene(Scene):
    is_world = True

    def __init__(self, app):
        super().__init__(app)
        st = app.state
        migrate_flags(st)
        self.rng = random.Random()
        self.face, self.moving, self.t, self.last_dir = "down", None, 0.0, None
        district = st.pos.get("map")
        if district not in app.data.districts:
            district = DEFAULT_DISTRICT
        self._load_district(district)
        x, y = st.pos.get("x"), st.pos.get("y")
        if st.pos.get("map") == district and x is not None and not self.map.blocked(x, y):
            self.x, self.y = x, y
        else:
            self.x, self.y = self.map.start()

    # ---------------------------------------------------------------- районы
    def _load_district(self, district):
        """Загружает карту района, раскладывает предметы (по сиду сохранения - перезагрузка карту не меняет)."""
        st, d = self.app.state, self.app.data
        self.district = district
        info = d.districts[district]
        self.map = MapData.load(paths.asset(info.get("map", f"maps/{district}.tmj")))
        ts = self.map.tileset
        img = (ts["image"] if ts["image"].exists() else paths.asset("assets/tiles/" + ts["image"].name)) if ts else None
        self.sheet = pygame.image.load(str(img)).convert_alpha() if img and img.exists() else None
        # первый район сохраняет прежнюю раскладку (совместимость сохранений), остальные - своя на район
        r = random.Random(st.seed if district == DEFAULT_DISTRICT else f"{st.seed}:{district}")
        self.items = {}
        for spot in sorted(self.map.objects_of("item_spot"), key=lambda o: o.id):
            item, keep = d.roll_item(district, r), r.random() < ITEM_SPOT_FILL
            if keep:
                self.items[spot.id] = item
        self.banner = BANNER_SECONDS
        bus = getattr(self.app, "events", None)
        if bus:
            bus.emit("map_changed", district=district)

    def _picked(self):
        return self.app.state.flags["picked"].setdefault(self.district, [])

    def _opened(self):
        return self.app.state.flags["opened"].setdefault(self.district, [])

    def _enter(self, target, spawn_name):
        """Переход в другой район: загрузка карты и постановка игрока на точку появления."""
        self._load_district(target)
        sp = self.map.spawn(spawn_name) if spawn_name else None
        if sp:
            self.x, self.y, self.face = sp.x, sp.y, sp.props.get("facing", "down")
        else:
            self.x, self.y = self.map.start()
        self.moving, self.t, self.last_dir = None, 0.0, None
        self.app.held.clear()
        self.sync_pos()

    def travel(self, district, spawn_name=None):
        """Для консоли: мгновенный переход без затемнения."""
        if district not in self.app.data.districts:
            return False
        self._enter(district, spawn_name)
        return True

    def _respawn(self):
        """После поражения: возвращаемся к последней бочке (она может быть в другом районе)."""
        st, d = self.app.state, self.app.data
        cp = st.flags.get("checkpoint")
        x = y = None
        if isinstance(cp, dict) and cp.get("map") in d.districts:
            if cp["map"] != self.district:
                self._load_district(cp["map"])
            x, y = cp.get("x"), cp.get("y")
        if x is None or self.map.blocked(x, y):
            x, y = self.map.start()
        self.x, self.y, self.face, self.moving, self.t = x, y, "down", None, 0.0
        self.sync_pos()

    # ---------------------------------------------------------------- логика
    def teleport(self, x, y):
        """Для консоли. Возвращает True, если клетка свободна."""
        if self.map.blocked(x, y):
            return False
        self.x, self.y, self.moving, self.t = x, y, None, 0.0
        return True

    def sync_pos(self):
        self.app.state.pos = {"map": self.district, "x": self.x, "y": self.y}

    def _msg(self, lines, on_done=None):
        self.app.push(MessageScene(self.app, lines, on_done))

    def update(self, dt):
        self.banner = max(0.0, self.banner - dt)
        if self.moving:
            self.t += dt * SPEED
            if self.t >= 1:
                self.x += self.moving[0]
                self.y += self.moving[1]
                self.moving, self.t = None, 0.0
                self._arrive()
            return
        held = self.app.held
        d = self.last_dir if self.last_dir in held else next((k for k in ("up", "down", "left", "right") if k in held), None)
        if d:
            self.face = d
            dx, dy = DIRS[d]
            nx, ny = self.x + dx, self.y + dy
            if not self.map.blocked(nx, ny):
                ex = self.map.exit_at(nx, ny)
                if ex and not self._exit_allowed(ex):
                    self.app.held.clear()
                    self.last_dir = None
                    self._msg(ex.props.get("blocked_text", "Путь закрыт.").split("\n"))
                    return
                self.moving, self.t = (dx, dy), 0.0

    def _exit_allowed(self, ex):
        need = ex.props.get("requires_badge")
        return not need or need in self.app.state.badges

    def _arrive(self):
        st, m = self.app.state, self.map
        ex = m.exit_at(self.x, self.y)
        if ex:                                          # встали на выход: плавный переход в другой район
            target, spawn = ex.props.get("target"), ex.props.get("spawn")
            if target in self.app.data.districts:
                self.app.held.clear()
                self.app.push(TransitionScene(self.app, lambda: self._enter(target, spawn)))
                return
        for o in m.objects_of("item_spot"):
            if (o.x, o.y) == (self.x, self.y) and o.id in self.items and o.id not in self._picked():
                item = self.items[o.id]
                self._picked().append(o.id)
                st.add_item(item)
                self._msg([f"Нашёл на земле: {self.app.data.items[item]['name']}!"])
                return
        if m.prop(self.x, self.y, "encounter") and st.has_usable() and self.rng.random() < ENCOUNTER_CHANCE:
            flow.start_wild(self.app, self.district, self._after_battle)

    def _after_battle(self, result):
        if result == "lose":
            self._respawn()

    def handle(self, a):
        if self.moving:
            return
        if a in DIRS:
            self.last_dir = a
        elif a == "back":
            self.app.push(PauseScene(self.app, self))
        elif a == "ok":
            self._interact()

    def _interact(self):
        st, d = self.app.state, self.app.data
        dx, dy = DIRS[self.face]
        o = self.map.object_at(self.x + dx, self.y + dy)
        if not o:
            return
        if o.type == "barrel":
            st.heal_party()
            st.flags["checkpoint"] = {"map": self.district, "x": self.x, "y": self.y}
            self.sync_pos()
            ok = save.autosave(st, location=d.districts[self.district]["name"])
            self._msg(["Погрелся у бочки. Команда отдохнула.", "Теперь ты просыпаешься тут, если что." + (" (Автосохранение.)" if ok else "")])
        elif o.type == "dumpster":
            if o.id in self._opened():
                self._msg(["Пусто. Тут уже рылись."])
                return
            self._opened().append(o.id)
            item = d.roll_item(self.district)
            qty = 2 if item == "box" else 1
            st.add_item(item, qty)
            self._msg([f"В баке нашлось: {d.items[item]['name']} x{qty}."])
        elif o.type == "pc":
            self._msg(["Выброшенный системник. Экран мигает, а внутри - все твои существа."], on_done=lambda: self.app.push(PCScene(self.app)))
        elif o.type == "trader":
            self._msg(["Меняла: Есть что обменять? Кое-кто от обмена... меняется."], on_done=lambda: self.app.push(TradeScene(self.app)))
        elif o.type in ("trainer", "leader"):
            tid = o.props["trainer_id"]
            tr = d.trainers[tid]
            if tid in st.defeated:
                self._msg(tr.get("after", ["..."]))
            elif not st.has_usable():
                self._msg(["Твоя команда вырублена. Сначала погрейся у бочки."])
            else:
                self._msg(tr.get("intro", ["..."]), on_done=lambda: flow.start_trainer(self.app, tid, self._after_battle))

    # ---------------------------------------------------------------- рисование
    def draw(self, surf):
        m, st = self.map, self.app.state
        surf.fill((20, 20, 24))
        px, py = self.x * T, self.y * T
        if self.moving:
            px += self.moving[0] * self.t * T
            py += self.moving[1] * self.t * T
        cx = int(min(max(px + T // 2 - VIEW[0] // 2, 0), max(0, m.w * T - VIEW[0])))
        cy = int(min(max(py + T // 2 - VIEW[1] // 2, 0), max(0, m.h * T - VIEW[1])))
        ts = m.tileset
        for ty in range(cy // T, min(m.h, (cy + VIEW[1]) // T + 2)):
            for tx in range(cx // T, min(m.w, (cx + VIEW[0]) // T + 2)):
                gid = m.gid(tx, ty)
                if gid and self.sheet:
                    i = gid - ts["first"]
                    surf.blit(self.sheet, (tx * T - cx, ty * T - cy), ((i % ts["columns"]) * ts["tw"], (i // ts["columns"]) * ts["th"], T, T))
        drawables = []
        for o in m.objects:
            sx, sy = o.x * T - cx, o.y * T - cy
            if o.type == "item_spot":
                if o.id in self.items and o.id not in self._picked():
                    drawables.append((o.y * T - 1, lambda sx=sx, sy=sy: self._item(surf, sx, sy)))
            elif o.type == "barrel":
                drawables.append((o.y * T, lambda sx=sx, sy=sy: self._barrel(surf, sx, sy)))
            elif o.type == "dumpster":
                opened = o.id in self._opened()
                drawables.append((o.y * T, lambda sx=sx, sy=sy, op=opened: self._dumpster(surf, sx, sy, op)))
            elif o.type == "pc":
                drawables.append((o.y * T, lambda sx=sx, sy=sy: self._pc(surf, sx, sy)))
            elif o.type == "trader":
                drawables.append((o.y * T, lambda sx=sx, sy=sy: draw_person(surf, sx, sy, "down", COATS["trader"], (30, 80, 50))))
            elif o.type in ("trainer", "leader"):
                tid = o.props["trainer_id"]
                drawables.append((o.y * T, lambda sx=sx, sy=sy, o=o, tid=tid: draw_person(surf, sx, sy, o.props.get("facing", "down"), COATS.get(tid, (120, 120, 120)), (120, 30, 30) if o.type == "leader" else (40, 40, 50))))
        drawables.append((py, lambda: draw_person(surf, int(px - cx), int(py - cy), self.face, COATS["player"])))
        for _, fn in sorted(drawables, key=lambda d: d[0]):
            fn()
        if "top" in m.layers and self.sheet:
            for ty in range(cy // T, min(m.h, (cy + VIEW[1]) // T + 2)):
                for tx in range(cx // T, min(m.w, (cx + VIEW[0]) // T + 2)):
                    gid = m.gid(tx, ty, "top")
                    if gid:
                        i = gid - ts["first"]
                        surf.blit(self.sheet, (tx * T - cx, ty * T - cy), ((i % ts["columns"]) * ts["tw"], (i // ts["columns"]) * ts["th"], T, T))

        if self.banner > 0:                                     # название района при входе
            name = self.app.data.districts[self.district]["name"]
            panel(surf, (8, 8, 20 + len(name) * 11, 28))
            text(surf, name, 18, 13, 16, INK, True)

    @staticmethod
    def _item(surf, x, y):
        pygame.draw.rect(surf, (190, 150, 90), (x + 10, y + 14, 12, 10))
        pygame.draw.rect(surf, INK, (x + 10, y + 14, 12, 10), 1)
        pygame.draw.rect(surf, (255, 255, 255), (x + 14, y + 17, 4, 3))

    @staticmethod
    def _pc(surf, x, y):
        pygame.draw.rect(surf, (150, 110, 70), (x + 3, y + 21, 26, 9))             # ящик-подставка
        pygame.draw.rect(surf, INK, (x + 3, y + 21, 26, 9), 1)
        pygame.draw.rect(surf, (60, 64, 76), (x + 6, y + 5, 20, 16))               # монитор
        pygame.draw.rect(surf, INK, (x + 6, y + 5, 20, 16), 2)
        pygame.draw.rect(surf, (120, 190, 230), (x + 9, y + 8, 14, 9))             # экран
        pygame.draw.rect(surf, (230, 240, 250), (x + 10, y + 9, 5, 2))

    @staticmethod
    def _barrel(surf, x, y):
        pygame.draw.rect(surf, (52, 52, 58), (x + 7, y + 10, 18, 20))
        pygame.draw.rect(surf, INK, (x + 7, y + 10, 18, 20), 2)
        pygame.draw.rect(surf, (150, 80, 40), (x + 7, y + 17, 18, 3))
        pygame.draw.polygon(surf, (255, 150, 40), [(x + 9, y + 10), (x + 13, y + 1), (x + 16, y + 7), (x + 19, y), (x + 23, y + 10)])
        pygame.draw.polygon(surf, (255, 220, 90), [(x + 13, y + 10), (x + 16, y + 4), (x + 19, y + 10)])

    @staticmethod
    def _dumpster(surf, x, y, opened):
        pygame.draw.rect(surf, (60, 110, 80), (x + 3, y + 10, 26, 19))
        pygame.draw.rect(surf, INK, (x + 3, y + 10, 26, 19), 2)
        pygame.draw.rect(surf, (40, 70, 55) if not opened else (30, 50, 40), (x + 2, y + 6 if not opened else y + 2, 28, 5))


class PauseScene(Scene):
    transparent = True

    def __init__(self, app, world):
        super().__init__(app)
        self.world = world
        self.items = ["Команда", "Сумка", "Бомждекс", "Крафт", "Сохранить", "Полный экран", "В главное меню", "Выйти из игры", "Закрыть"]
        self.menu = Menu(self.items)

    def handle(self, a):
        r = self.menu.handle(a)
        app = self.app
        if r == "back":
            app.pop()
        elif r == "ok":
            it = self.items[self.menu.i]
            if it == "Команда":
                app.push(PartyScene(app))
            elif it == "Сумка":
                app.push(BagScene(app))
            elif it == "Бомждекс":
                app.push(DexScene(app))
            elif it == "Крафт":
                app.push(CraftScene(app))
            elif it == "Сохранить":
                app.push(SlotScene(app, "save", prepare=self.world.sync_pos))
            elif it == "Полный экран":
                app.toggle_fullscreen()
            elif it == "В главное меню":
                ask_exit(app, True)
            elif it == "Выйти из игры":
                ask_exit(app, False)
            else:
                app.pop()

    def draw(self, surf):
        st = self.app.state
        panel(surf, (320, 8, 152, 244))
        self.menu.draw(surf, 328, 16, row_h=26, size=14)
        panel(surf, (320, 258, 152, 54))
        text(surf, f"Монеты: {st.money}", 330, 262, 13)
        text(surf, f"Значки: {len(st.badges)}  Декс: {len(st.caught)}", 330, 282, 13)
