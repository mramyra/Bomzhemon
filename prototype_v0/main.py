# -*- coding: utf-8 -*-
"""БОМЖЕМОН - покемоны для тех, у кого нет покебола, зато есть картонная коробка.

Управление:
  стрелки / WASD - ходить, Z / Space - действие, X - назад, Enter / Esc - меню
"""
import os
import random
import sys

import pygame

from data import CREATURES, CID, MOVES, TYPE_MOVE, type_mult

pygame.init()

W, H, SCALE, T = 320, 288, 2, 32          # экран 320x288 (10x9 тайлов по 32), окно x2
C0, C1, C2, C3 = (15, 56, 15), (48, 98, 48), (139, 172, 15), (155, 188, 15)  # палитра GameBoy
FONT = pygame.font.Font(None, 22)
FONT_S = pygame.font.Font(None, 18)
FONT_L = pygame.font.Font(None, 44)

K = pygame
CONFIRM = (K.K_z, K.K_SPACE, K.K_RETURN)
BACK = (K.K_x, K.K_BACKSPACE, K.K_ESCAPE)
UP, DOWN, LEFT, RIGHT = (K.K_UP, K.K_w), (K.K_DOWN, K.K_s), (K.K_LEFT, K.K_a), (K.K_RIGHT, K.K_d)

SOLID = {1, 4, 5}   # стена, бочка, контейнер
GRASS = 2           # свалка - тут встречаются существа


# ------------------------------------------------------------------ существа
class Creature:
    def __init__(s, cid, level):
        s.cid = cid
        s.name, s.type, *s.base = CREATURES[cid]
        s.level, s.xp = level, 0
        s.moves = ["Царапка", TYPE_MOVE[s.type]]
        s.recalc()
        s.hp = s.maxhp

    def recalc(s):
        hp, a, d, sp = s.base
        L = s.level
        old = getattr(s, "maxhp", 0)
        s.maxhp = hp * L // 25 + L + 10
        s.atk, s.df, s.spd = a * L // 30 + 5, d * L // 30 + 5, sp * L // 30 + 5
        if old:
            s.hp += s.maxhp - old

    @property
    def need(s):
        return 10 + 5 * s.level


def calc_damage(att, dfn, move):
    mtype, power = MOVES[move]
    base = ((2 * att.level / 5 + 2) * power * att.atk / dfn.df) / 50 + 2
    mult = type_mult(mtype, dfn.type)
    stab = 1.5 if mtype == att.type else 1.0
    return max(1, int(base * mult * stab * random.uniform(0.85, 1.0))), mult


# ------------------------------------------------------------------ графика
_sprite_cache = {}


def gen_sprite(cid):
    """Процедурный спрайт-заглушка 16x16. Положи assets/sprites/NN.png (NN = номер 01..43) - и он заменится."""
    path = os.path.join(os.path.dirname(__file__), "assets", "sprites", f"{cid + 1:02d}.png")
    if os.path.exists(path):
        return pygame.image.load(path).convert_alpha()
    r = random.Random(cid * 7919 + 13)
    N = 16
    g = [[0] * N for _ in range(N)]

    def ell(cx, cy, rx, ry, v):
        for y in range(N):
            for x in range(N):
                if ((x - cx) / rx) ** 2 + ((y - cy) / ry) ** 2 <= 1:
                    g[y][x] = v

    brx, bry = r.uniform(3.5, 5.5), r.uniform(2.5, 4.0)
    hr = r.uniform(2.5, 3.5)
    ell(7.5, 10.5, brx, bry, 2)
    ell(7.5, 6, hr, hr * 0.9, 2)
    ell(7.5, 11, brx * 0.5, bry * 0.5, 3)
    ex = int(round(hr)) - 1
    top = int(6 - hr * 0.9)
    for y in range(max(0, top - r.randint(1, 2)), top + 1):
        g[y][7 - ex] = g[y][8 + ex] = 2
    side = r.choice([-1, 1])
    x, y = (8 + int(brx) if side > 0 else 7 - int(brx)), 11
    for i in range(r.randint(2, 4)):
        x += side
        y -= i % 2
        if 0 <= x < N and 0 <= y < N:
            g[y][x] = 2
    for y in range(N):
        for x in range(N):
            if g[y][x] == 2 and r.random() < 0.12:
                g[y][x] = 1.5
    out = [[0] * N for _ in range(N)]
    for y in range(N):
        for x in range(N):
            if g[y][x] == 0:
                for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    nx, ny = x + dx, y + dy
                    if 0 <= nx < N and 0 <= ny < N and g[ny][nx]:
                        out[y][x] = "o"
    col = {2: C2, 3: C3, 1.5: C1, "o": C0}
    surf = pygame.Surface((N, N), pygame.SRCALPHA)
    for y in range(N):
        for x in range(N):
            v = out[y][x] or g[y][x]
            if v:
                surf.set_at((x, y), col[v])
    surf.set_at((6, 6), C0)
    surf.set_at((9, 6), C0)
    return surf


def sprite(cid, size, flip=False):
    key = (cid, size, flip)
    if key not in _sprite_cache:
        if ("raw", cid) not in _sprite_cache:
            _sprite_cache[("raw", cid)] = gen_sprite(cid)
        img = pygame.transform.scale(_sprite_cache[("raw", cid)], (size, size))
        _sprite_cache[key] = pygame.transform.flip(img, True, False) if flip else img
    return _sprite_cache[key]


def make_tiles():
    r = random.Random(5)
    tiles = {}
    g = pygame.Surface((T, T)); g.fill(C3)
    for _ in range(5):
        pygame.draw.rect(g, C2, (r.randint(0, T - 3), r.randint(0, T - 3), 2, 2))
    tiles[0] = g
    w = pygame.Surface((T, T)); w.fill(C1)
    pygame.draw.rect(w, C0, (0, 0, T, T), 2)
    pygame.draw.rect(w, C3, (9, 8, 14, 12)); pygame.draw.rect(w, C0, (9, 8, 14, 12), 2)
    pygame.draw.line(w, C0, (16, 8), (16, 20), 2)
    tiles[1] = w
    d = g.copy(); d.fill(C2)
    for _ in range(14):
        pygame.draw.rect(d, r.choice([C0, C1, C3]), (r.randint(0, T - 5), r.randint(0, T - 5), r.randint(2, 5), r.randint(2, 4)))
    tiles[2] = d
    b = g.copy()
    pygame.draw.rect(b, C0, (7, 8, 18, 22)); pygame.draw.rect(b, C1, (9, 12, 14, 4))
    pygame.draw.polygon(b, C2, [(16, 0), (21, 8), (11, 8)]); pygame.draw.polygon(b, C0, [(16, 0), (21, 8), (11, 8)], 1)
    tiles[4] = b
    c = g.copy()
    pygame.draw.rect(c, C1, (3, 10, 26, 18)); pygame.draw.rect(c, C0, (3, 10, 26, 18), 2)
    pygame.draw.rect(c, C0, (2, 6, 28, 6))
    tiles[5] = c
    return tiles


def make_map():
    r = random.Random(11)
    w, h = 40, 32
    m = [[0] * w for _ in range(h)]
    for x in range(w):
        m[0][x] = m[h - 1][x] = 1
    for y in range(h):
        m[y][0] = m[y][w - 1] = 1
    blds, tries = [], 0
    while len(blds) < 9 and tries < 300:
        tries += 1
        bw, bh = r.randint(4, 7), r.randint(3, 5)
        bx, by = r.randint(2, w - bw - 3), r.randint(2, h - bh - 3)
        if bx - 4 <= 3 <= bx + bw + 4 and by - 4 <= 3 <= by + bh + 4:
            continue
        if any(bx < ox + ow + 2 and ox < bx + bw + 2 and by < oy + oh + 2 and oy < by + bh + 2 for ox, oy, ow, oh in blds):
            continue
        blds.append((bx, by, bw, bh))
        for y in range(by, by + bh):
            for x in range(bx, bx + bw):
                m[y][x] = 1
    for _ in range(16):
        x, y = r.randint(3, w - 4), r.randint(3, h - 4)
        for _ in range(14):
            if m[y][x] == 0 and abs(x - 3) + abs(y - 3) > 4:
                m[y][x] = GRASS
            x = min(w - 2, max(1, x + r.choice([-1, 0, 1])))
            y = min(h - 2, max(1, y + r.choice([-1, 0, 1])))
    m[3][4] = 4
    placed = 0
    while placed < 6:
        x, y = r.randint(2, w - 3), r.randint(2, h - 3)
        if m[y][x] == 0 and abs(x - 3) + abs(y - 3) > 3:
            m[y][x] = 5
            placed += 1
    return m


def box(surf, rect):
    pygame.draw.rect(surf, C3, rect)
    pygame.draw.rect(surf, C0, rect, 3)
    pygame.draw.rect(surf, C1, pygame.Rect(rect).inflate(-8, -8), 1)


def text(surf, s, x, y, font=FONT, color=C0):
    surf.blit(font.render(s, False, color), (x, y))


def wrap(s, width, font=FONT):
    lines, cur = [], ""
    for word in s.split(" "):
        t = (cur + " " + word).strip()
        if font.size(t)[0] > width and cur:
            lines.append(cur)
            cur = word
        else:
            cur = t
    return lines + [cur]


def hp_bar(surf, x, y, w, c):
    text(surf, "HP", x, y - 3, FONT_S)
    pygame.draw.rect(surf, C0, (x + 22, y, w, 8), 2)
    fill = int((w - 4) * max(0, c.hp) / c.maxhp)
    pygame.draw.rect(surf, C1 if c.hp / c.maxhp < 0.35 else C0, (x + 24, y + 2, fill, 4))


# ------------------------------------------------------------------ бой
def mk(txt, fn=None):
    def f():
        if fn:
            fn()
        return txt
    return f


class Battle:
    def __init__(s, g, wild):
        s.g, s.wild = g, wild
        s.act = next(c for c in g.party if c.hp > 0)
        s.queue, s.text, s.phase, s.next = [], "", "msg", "menu"
        s.cur, s.over, s.result = 0, False, None
        g.seen.add(wild.cid)
        s.say(f"Из кустов вылез дикий {wild.name}!")
        s.say(f"Вперёд, {s.act.name}!")
        s.advance()

    # --- очередь сообщений
    def say(s, t, fn=None):
        s.queue.append(mk(t, fn))

    def front(s, items):
        s.queue[0:0] = items

    def advance(s):
        while s.queue:
            t = s.queue.pop(0)()
            if t:
                s.text, s.phase = t, "msg"
                return
        s.phase = s.next
        if s.phase == "menu":
            s.text, s.cur = f"Что делать, {s.act.name}?", 0

    def nm(s, c):
        return "Дикий " + c.name if c is s.wild else c.name

    # --- логика
    def attack(s, att, dfn, move):
        if s.over or att.hp <= 0:
            return None
        dmg, mult = calc_damage(att, dfn, move)
        dfn.hp = max(0, dfn.hp - dmg)
        t = f"{s.nm(att)}: {move}!"
        t += " Очень эффективно!" if mult > 1 else (" Слабовато..." if mult < 1 else "")
        if dfn.hp <= 0:
            s.front([lambda: s.faint(dfn)])
        return t

    def enemy_attack(s):
        return lambda: s.attack(s.wild, s.act, random.choice(s.wild.moves))

    def faint(s, d):
        if d is s.wild:
            s.over, s.result, s.next = True, "win", "end"
            xp = d.level * 3 + sum(d.base) // 15
            s.front([mk(f"{s.act.name} получил {xp} опыта.", lambda: s.give_xp(xp))])
            return f"{s.nm(d)} сдулся!"
        s.queue.clear()
        if any(c.hp > 0 for c in s.g.party):
            s.next = "forced"
        else:
            s.over, s.result, s.next = True, "lose", "end"
            s.say("Ты вырубился... Тебя откачали у бочки.")
        return f"{d.name} вырубился!"

    def give_xp(s, xp):
        a, msgs = s.act, []
        a.xp += xp
        while a.xp >= a.need and a.level < 50:
            a.xp -= a.need
            a.level += 1
            a.recalc()
            msgs.append(mk(f"{a.name} вырос до {a.level} уровня!"))
        s.front(msgs)

    def turn(s, items):
        s.queue = items
        s.next = "menu"
        s.advance()

    def fight(s, move):
        p, e = s.act, s.wild
        pa = lambda: s.attack(p, e, move)
        ea = s.enemy_attack()
        s.turn([pa, ea] if p.spd >= e.spd else [ea, pa])

    def throw(s):
        if s.g.boxes <= 0:
            s.text = "Коробок нет! Поищи в мусорных баках."
            return
        s.g.boxes -= 1
        s.turn([mk("Ты накидываешь картонную коробку!"), lambda: s.catch_try()])

    def catch_try(s):
        w = s.wild
        p = min(0.95, max(0.05, 0.1 + 0.8 * (1 - w.hp / w.maxhp) - (w.level - 5) * 0.01))
        if random.random() < p:
            s.over, s.result, s.next = True, "caught", "end"
            s.g.caught.add(w.cid)
            w.hp = max(1, w.hp)
            if len(s.g.party) < 6:
                s.g.party.append(w)
                return f"Поймал! {w.name} теперь с тобой."
            s.g.storage.append(w)
            return f"Поймал! {w.name} отправился в заначку (команда полна)."
        s.front([s.enemy_attack()])
        return random.choice(["Выскочил из коробки!", "Почти! Но нет.", "Коробка промокла и порвалась!"])

    def run(s):
        ch = min(0.95, max(0.2, 0.5 + (s.act.spd - s.wild.spd) / 100))
        if random.random() < ch:
            s.turn([mk("Ты свалил по-тихому.", lambda: s.end("run"))])
        else:
            s.turn([mk("Не удалось сбежать!"), s.enemy_attack()])

    def end(s, res):
        s.over, s.result, s.next = True, res, "end"

    def switch(s, c, forced=False):
        def do():
            s.act = c
        items = [mk(f"Вперёд, {c.name}!", do)]
        if not forced:
            items.append(s.enemy_attack())
        s.turn(items)

    def finish(s):
        g = s.g
        if s.result == "lose":
            for c in g.party:
                c.hp = c.maxhp
            g.px, g.py = g.start
        g.battle, g.state = None, "world"

    # --- ввод
    def key(s, k):
        if s.phase == "msg":
            if k in CONFIRM:
                s.advance()
        elif s.phase == "end":
            if k in CONFIRM:
                s.finish()
        elif s.phase == "menu":
            if k in UP:
                s.cur = (s.cur - 1) % 4
            elif k in DOWN:
                s.cur = (s.cur + 1) % 4
            elif k in CONFIRM:
                if s.cur == 0:
                    s.phase, s.mcur = "moves", 0
                elif s.cur == 1:
                    s.throw()
                elif s.cur == 2:
                    s.phase, s.g.cursor = "party", 0
                else:
                    s.run()
        elif s.phase == "moves":
            if k in UP + DOWN:
                s.mcur = (s.mcur + 1) % len(s.act.moves)
            elif k in BACK:
                s.advance()
            elif k in CONFIRM:
                s.fight(s.act.moves[s.mcur])
        elif s.phase in ("party", "forced"):
            n = len(s.g.party)
            if k in UP:
                s.g.cursor = (s.g.cursor - 1) % n
            elif k in DOWN:
                s.g.cursor = (s.g.cursor + 1) % n
            elif k in BACK and s.phase == "party":
                s.advance()
            elif k in CONFIRM:
                c = s.g.party[s.g.cursor]
                if c.hp > 0 and c is not s.act:
                    s.switch(c, forced=(s.phase == "forced"))

    def draw(s, surf):
        g = s.g
        surf.fill(C3)
        e, p = s.wild, s.act
        pygame.draw.ellipse(surf, C2, (170, 96, 130, 24)); pygame.draw.ellipse(surf, C2, (10, 176, 150, 26))
        surf.blit(sprite(e.cid, 96), (190, 22))
        surf.blit(sprite(p.cid, 112, flip=True), (30, 78 + 8))
        box(surf, (8, 10, 150, 52))
        text(surf, f"{e.name}", 16, 16); text(surf, f"Lv{e.level}", 112, 16)
        text(surf, e.type, 16, 30, FONT_S); hp_bar(surf, 16, 46, 100, e)
        box(surf, (164, 128, 150, 66))
        text(surf, p.name, 172, 134); text(surf, f"Lv{p.level}", 268, 134)
        text(surf, p.type, 172, 148, FONT_S); hp_bar(surf, 172, 164, 100, p)
        text(surf, f"{p.hp}/{p.maxhp}", 200, 176, FONT_S)
        box(surf, (0, 208, W, 80))
        if s.phase in ("msg", "end"):
            for i, ln in enumerate(wrap(s.text, W - 40)[:3]):
                text(surf, ln, 16, 220 + i * 20)
            if pygame.time.get_ticks() // 400 % 2:
                text(surf, "v", W - 26, 266)
        elif s.phase == "menu":
            for i, ln in enumerate(wrap(s.text, 130)[:3]):
                text(surf, ln, 16, 220 + i * 20)
            box(surf, (150, 208, 170, 80))
            for i, o in enumerate(["БОЙ", f"КОРОБКА x{g.boxes}", "КОМАНДА", "БЕЖАТЬ"]):
                x, y = 172 + (i % 2) * 0, 218 + i * 17
                text(surf, ("> " if i == s.cur else "  ") + o, 164, y)
        elif s.phase == "moves":
            for i, m in enumerate(p.moves):
                t, pw = MOVES[m]
                text(surf, ("> " if i == s.mcur else "  ") + m, 16, 222 + i * 22)
                text(surf, f"{t or 'Обычный'}  сила {pw}", 180, 224 + i * 22, FONT_S)
            text(surf, "X - назад", 16, 268, FONT_S)
        elif s.phase in ("party", "forced"):
            g.draw_party(surf, "Кого выпустить?")


# ------------------------------------------------------------------ игра
class Game:
    def __init__(s):
        s.screen = pygame.display.set_mode((W * SCALE, H * SCALE))
        pygame.display.set_caption("БОМЖЕМОН")
        s.buf = pygame.Surface((W, H))
        s.clock = pygame.time.Clock()
        s.tiles, s.map = make_tiles(), make_map()
        s.state, s.cursor = "title", 0
        s.party, s.storage, s.boxes = [], [], 5
        s.seen, s.caught, s.opened = set(), set(), set()
        s.start = (3, 3)
        s.px, s.py, s.face = 3, 3, (0, 1)
        s.mf, s.mdir = 0, None
        s.world_msg, s.battle, s.trans = [], None, 0
        w = [(1000 / sum(c[2:]), i) for i, c in enumerate(CREATURES)]
        s.weights = [x[0] for x in w]

    # --- ввод
    def on_key(s, k):
        st = s.state
        if s.trans:
            return
        if st == "title" and k in CONFIRM:
            s.state, s.cursor = "starter", 0
        elif st == "starter":
            names = ["Крыса", "Дворняга", "Дворовый кот"]
            if k in LEFT:
                s.cursor = (s.cursor - 1) % 3
            elif k in RIGHT:
                s.cursor = (s.cursor + 1) % 3
            elif k in CONFIRM:
                c = Creature(CID[names[s.cursor]], 5)
                s.party, s.state = [c], "world"
                s.caught.add(c.cid); s.seen.add(c.cid)
                s.world_msg = ["Ты бомж. Из имущества - картонные коробки.", "Лови всех, кого найдёшь на свалках. Бочка с огнём лечит (Z рядом).", "Мусорные баки (Z) - источник коробок."]
        elif st == "world":
            if s.world_msg:
                if k in CONFIRM:
                    s.world_msg.pop(0)
            elif k in (K.K_RETURN, K.K_ESCAPE):
                s.state, s.cursor = "menu", 0
            elif k in (K.K_z, K.K_SPACE):
                s.interact()
        elif st == "menu":
            if k in UP:
                s.cursor = (s.cursor - 1) % 3
            elif k in DOWN:
                s.cursor = (s.cursor + 1) % 3
            elif k in BACK:
                s.state = "world"
            elif k in CONFIRM:
                if s.cursor == 2:
                    s.state = "world"
                else:
                    s.state, s.cursor = ("party", "dex")[s.cursor], 0
        elif st == "party":
            if k in UP:
                s.cursor = (s.cursor - 1) % len(s.party)
            elif k in DOWN:
                s.cursor = (s.cursor + 1) % len(s.party)
            elif k in BACK:
                s.state, s.cursor = "menu", 0
        elif st == "dex":
            n = len(CREATURES)
            if k in UP:
                s.cursor = (s.cursor - 1) % n
            elif k in DOWN:
                s.cursor = (s.cursor + 1) % n
            elif k in BACK:
                s.state, s.cursor = "menu", 0
        elif st == "battle" and s.battle:
            s.battle.key(k)

    def interact(s):
        tx, ty = s.px + s.face[0], s.py + s.face[1]
        t = s.map[ty][tx]
        if t == 4:
            for c in s.party:
                c.hp = c.maxhp
            s.world_msg = ["Ты погрелся у бочки. Вся команда отдохнула."]
        elif t == 5:
            if (tx, ty) in s.opened:
                s.world_msg = ["Тут уже рылись. Пусто."]
            else:
                s.opened.add((tx, ty))
                n = random.randint(1, 3)
                s.boxes += n
                s.world_msg = [f"В баке нашлись коробки: +{n}."]

    # --- мир
    def walkable(s, x, y):
        return 0 <= y < len(s.map) and 0 <= x < len(s.map[0]) and s.map[y][x] not in SOLID

    def update(s):
        if s.trans:
            s.trans -= 1
            if s.trans == 0:
                s.battle, s.state = Battle(s, s.pending), "battle"
            return
        if s.state != "world" or s.world_msg:
            return
        if s.mdir:
            s.mf += 1
            if s.mf >= 8:
                s.px += s.mdir[0]; s.py += s.mdir[1]
                s.mdir, s.mf = None, 0
                if s.map[s.py][s.px] == GRASS and random.random() < 0.2:
                    lvl = random.randint(3, 8)
                    s.pending = Creature(random.choices(range(len(CREATURES)), s.weights)[0], lvl)
                    s.trans = 40
            return
        keys = pygame.key.get_pressed()
        d = None
        if any(keys[k] for k in UP): d = (0, -1)
        elif any(keys[k] for k in DOWN): d = (0, 1)
        elif any(keys[k] for k in LEFT): d = (-1, 0)
        elif any(keys[k] for k in RIGHT): d = (1, 0)
        if d:
            s.face = d
            if s.walkable(s.px + d[0], s.py + d[1]):
                s.mdir = d

    def draw_world(s, surf):
        ox = oy = 0
        if s.mdir:
            ox, oy = s.mdir[0] * s.mf * 4, s.mdir[1] * s.mf * 4
        ppx, ppy = s.px * T + ox, s.py * T + oy
        mw, mh = len(s.map[0]) * T, len(s.map) * T
        cx = min(max(ppx + T // 2 - W // 2, 0), mw - W)
        cy = min(max(ppy + T // 2 - H // 2, 0), mh - H)
        for ty in range(cy // T, min(len(s.map), (cy + H) // T + 2)):
            for tx in range(cx // T, min(len(s.map[0]), (cx + W) // T + 2)):
                surf.blit(s.tiles[s.map[ty][tx]], (tx * T - cx, ty * T - cy))
        x, y = ppx - cx, ppy - cy
        pygame.draw.rect(surf, C0, (x + 9, y + 26, 5, 5)); pygame.draw.rect(surf, C0, (x + 18, y + 26, 5, 5))
        pygame.draw.rect(surf, C1, (x + 7, y + 13, 18, 14)); pygame.draw.rect(surf, C0, (x + 7, y + 13, 18, 14), 2)
        pygame.draw.rect(surf, C2, (x + 10, y + 3, 12, 11)); pygame.draw.rect(surf, C0, (x + 10, y + 3, 12, 11), 2)
        pygame.draw.rect(surf, C0, (x + 8, y + 1, 16, 5))
        if s.face[1] >= 0:
            ex = 4 * s.face[0]
            pygame.draw.rect(surf, C0, (x + 13 + ex, y + 8, 2, 2)); pygame.draw.rect(surf, C0, (x + 18 + ex, y + 8, 2, 2))
        pygame.draw.rect(surf, C0, (x + 25, y + 17, 3, 7))   # бутылка
        if s.world_msg:
            box(surf, (6, 214, W - 12, 68))
            for i, ln in enumerate(wrap(s.world_msg[0], W - 40)[:3]):
                text(surf, ln, 16, 224 + i * 20)

    # --- экраны
    def draw_party(s, surf, title="Команда"):
        surf.fill(C3)
        text(surf, title, 10, 8, FONT_L)
        for i, c in enumerate(s.party):
            y = 44 + i * 40
            if i == s.cursor:
                pygame.draw.rect(surf, C2, (4, y - 4, W - 8, 38))
            surf.blit(sprite(c.cid, 32), (8, y - 2))
            text(surf, f"{c.name}  Lv{c.level}", 48, y)
            text(surf, c.type, 230, y, FONT_S)
            hp_bar(surf, 48, y + 20, 110, c)
            text(surf, f"{c.hp}/{c.maxhp}", 190, y + 18, FONT_S)

    def draw_dex(s, surf):
        surf.fill(C3)
        text(surf, f"Бомждекс  {len(s.caught)}/{len(CREATURES)}", 10, 8, FONT_L)
        top = max(0, min(s.cursor - 4, len(CREATURES) - 9))
        for row, i in enumerate(range(top, min(top + 9, len(CREATURES)))):
            y = 44 + row * 26
            if i == s.cursor:
                pygame.draw.rect(surf, C2, (4, y - 3, 180, 24))
            nm = CREATURES[i][0] if i in s.seen else "???"
            mark = "*" if i in s.caught else " "
            text(surf, f"{i + 1:02d} {mark} {nm}", 10, y)
        if s.cursor in s.seen:
            surf.blit(sprite(s.cursor, 96), (200, 60))
            c = CREATURES[s.cursor]
            text(surf, c[1], 206, 164, FONT_S)
            text(surf, f"HP {c[2]} АТК {c[3]}", 200, 184, FONT_S)
            text(surf, f"ЗАЩ {c[4]} СКО {c[5]}", 200, 200, FONT_S)

    def draw(s):
        b, st = s.buf, s.state
        if st == "title":
            b.fill(C3)
            text(b, "БОМЖЕМОН", 62, 80, FONT_L)
            text(b, "красная и синяя", 92, 120, FONT)
            surf = sprite(CID["Крыса"], 96)
            b.blit(surf, (112, 150))
            if pygame.time.get_ticks() // 500 % 2:
                text(b, "нажми Z", 120, 262)
        elif st == "starter":
            b.fill(C3)
            text(b, "Выбери первого кореша:", 40, 20)
            for i, n in enumerate(["Крыса", "Дворняга", "Дворовый кот"]):
                x = 14 + i * 100
                if i == s.cursor:
                    pygame.draw.rect(b, C2, (x - 6, 70, 94, 150)); pygame.draw.rect(b, C0, (x - 6, 70, 94, 150), 3)
                b.blit(sprite(CID[n], 80), (x, 90))
                text(b, n, x, 180, FONT_S)
                text(b, CREATURES[CID[n]][1], x, 198, FONT_S)
        elif st in ("world", "menu") or s.trans:
            s.draw_world(b)
            if st == "menu":
                box(b, (190, 10, 120, 100))
                for i, o in enumerate(["Команда", "Бомждекс", "Закрыть"]):
                    text(b, ("> " if i == s.cursor else "  ") + o, 200, 20 + i * 22)
                text(b, f"Коробки: {s.boxes}", 200, 88, FONT_S)
            if s.trans and (s.trans // 5) % 2:
                b.fill(C0)
        elif st == "party":
            s.draw_party(b)
        elif st == "dex":
            s.draw_dex(b)
        elif st == "battle":
            s.battle.draw(b)
        pygame.transform.scale(b, (W * SCALE, H * SCALE), s.screen)
        pygame.display.flip()

    def run(s):
        while True:
            for e in pygame.event.get():
                if e.type == pygame.QUIT:
                    pygame.quit(); sys.exit()
                if e.type == pygame.KEYDOWN:
                    s.on_key(e.key)
            s.update()
            s.draw()
            s.clock.tick(60)


if __name__ == "__main__":
    Game().run()
