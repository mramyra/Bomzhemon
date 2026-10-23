"""Генерирует карты-заглушки и общий тайлсет для Tiled.
    python -m tools.make_placeholder_map [--force] [dump|vokzal ...]
Без --force существующие карты НЕ перезаписываются (чтобы не затереть то, что ты правил в Tiled). Тайлсет перезаписывается всегда,
если нет файла. Результат: maps/<id>.tmj и assets/tiles/placeholder_tileset.png. Свой тайлсет подключается заменой PNG
(тайл 32x32, те же номера тайлов) или новым тайлсетом в Tiled."""
import json
import random
import struct
import sys
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from game.world.mapdata import MapData  # noqa: E402

T = 32
ASPHALT, WALL, TRASH, FENCE, PUDDLE, CONCRETE, MARK, RUBBLE, RAIL, PLATFORM = range(10)
NTILES = 10
SOLID, ENCOUNTER = {WALL, FENCE, RUBBLE}, {TRASH, RAIL}
NAMES = ["асфальт", "стена", "свалка (встречи)", "забор", "лужа", "бетон", "разметка", "завал", "пути (встречи)", "платформа"]


# ---------------------------------------------------------------- тайлсет PNG (без внешних библиотек)
def tile_pixels(tid):
    r = random.Random(tid * 31 + 7)
    px = [[(0, 0, 0)] * T for _ in range(T)]
    base = {ASPHALT: (92, 92, 100), WALL: (150, 100, 80), TRASH: (104, 128, 72), FENCE: (92, 92, 100), PUDDLE: (92, 92, 100),
            CONCRETE: (172, 170, 162), MARK: (92, 92, 100), RUBBLE: (92, 92, 100), RAIL: (112, 104, 94), PLATFORM: (176, 172, 160)}[tid]
    for y in range(T):
        for x in range(T):
            n = r.randint(-7, 7)
            px[y][x] = tuple(max(0, min(255, c + n)) for c in base)

    def put(x, y, c):
        if 0 <= x < T and 0 <= y < T:
            px[y][x] = c
    if tid == WALL:
        for y in range(T):
            for x in range(T):
                if y % 8 == 0 or (x + (y // 8) * 8) % 16 == 0:
                    px[y][x] = (110, 76, 62)
    elif tid == TRASH:
        for _ in range(40):
            c = r.choice([(200, 60, 60), (230, 230, 220), (60, 90, 160), (210, 190, 60), (60, 60, 60)])
            x, y = r.randint(0, T - 4), r.randint(0, T - 4)
            for dx in range(r.randint(2, 4)):
                for dy in range(r.randint(1, 3)):
                    put(x + dx, y + dy, c)
    elif tid == FENCE:
        for x in range(2, T, 6):
            for y in range(T):
                put(x, y, (70, 70, 54)); put(x + 1, y, (70, 70, 54))
        for y in (8, 22):
            for x in range(T):
                put(x, y, (60, 60, 48))
    elif tid == PUDDLE:
        for y in range(T):
            for x in range(T):
                if ((x - 16) / 12) ** 2 + ((y - 17) / 7) ** 2 < 1:
                    px[y][x] = (84 + r.randint(0, 8), 116 + r.randint(0, 8), 150 + r.randint(0, 10))
    elif tid == CONCRETE:
        for i in range(T):
            put(i, 0, (140, 138, 130)); put(0, i, (140, 138, 130))
    elif tid == MARK:
        for x in range(4, 28):
            for y in (15, 16):
                put(x, y, (230, 230, 220))
    elif tid == RUBBLE:
        for _ in range(9):
            x, y, s = r.randint(2, 22), r.randint(4, 22), r.randint(5, 9)
            g = r.randint(95, 140)
            for dx in range(s):
                for dy in range(s - 1):
                    put(x + dx, y + dy, (g, g, g + 6))
    elif tid == RAIL:
        for x in range(2, T, 8):                           # шпалы
            for y in range(6, 27):
                for dx in range(4):
                    put(x + dx, y, (96, 70, 50))
        for y0 in (10, 20):                                # рельсы
            for x in range(T):
                for dy in range(3):
                    put(x, y0 + dy, (150, 150, 162) if dy == 0 else (84, 84, 96))
    elif tid == PLATFORM:
        for x in range(T):
            for y in (26, 27, 28):
                put(x, y, (230, 200, 60))
    return px


def write_tileset(path):
    tiles = [tile_pixels(i) for i in range(NTILES)]
    rows = [b"".join(bytes(c) for t in tiles for c in t[y]) for y in range(T)]
    raw = b"".join(b"\x00" + r for r in rows)

    def chunk(t, d):
        return struct.pack(">I", len(d)) + t + d + struct.pack(">I", zlib.crc32(t + d) & 0xFFFFFFFF)
    png = (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", T * NTILES, T, 8, 2, 0, 0, 0))
           + chunk(b"IDAT", zlib.compress(raw, 9)) + chunk(b"IEND", b""))
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_bytes(png)


# ---------------------------------------------------------------- каркасы карт (без объектов)
def _border(g, W, H):
    for x in range(W):
        g[0][x] = g[H - 1][x] = FENCE
    for y in range(H):
        g[y][0] = g[y][W - 1] = FENCE


def _arena(g, W, H):
    ax, ay = W - 10, H - 10                  # арена лидера 7x7
    for yy in range(ay, ay + 7):
        for xx in range(ax, ax + 7):
            g[yy][xx] = CONCRETE
    return ax, ay


def build_dump(seed, W=48, H=36):
    r = random.Random(seed)
    g = [[ASPHALT] * W for _ in range(H)]
    _border(g, W, H)
    start = (3, 3)
    for _ in range(7):                      # бетонные площадки
        w, h, x, y = r.randint(3, 6), r.randint(2, 4), r.randint(2, W - 8), r.randint(2, H - 6)
        for yy in range(y, y + h):
            for xx in range(x, x + w):
                g[yy][xx] = CONCRETE
    for _ in range(12):                     # разметка
        x, y = r.randint(2, W - 3), r.randint(2, H - 3)
        g[y][x] = MARK
    blds = []
    for _ in range(300):                    # дома
        if len(blds) >= 9:
            break
        bw, bh, = r.randint(4, 8), r.randint(3, 5)
        bx, by = r.randint(2, W - bw - 3), r.randint(2, H - bh - 3)
        if bx - 5 <= start[0] <= bx + bw + 5 and by - 5 <= start[1] <= by + bh + 5:
            continue
        if any(bx < ox + ow + 2 and ox < bx + bw + 2 and by < oy + oh + 2 and oy < by + bh + 2 for ox, oy, ow, oh in blds):
            continue
        blds.append((bx, by, bw, bh))
        for yy in range(by, by + bh):
            for xx in range(bx, bx + bw):
                g[yy][xx] = WALL
    ax, ay = _arena(g, W, H)
    for _ in range(14):                     # завалы
        x, y = r.randint(2, W - 3), r.randint(2, H - 3)
        if g[y][x] == ASPHALT and abs(x - start[0]) + abs(y - start[1]) > 4:
            g[y][x] = RUBBLE
    for _ in range(30):                     # свалки (зона встреч)
        x, y = r.randint(3, W - 4), r.randint(3, H - 4)
        for _ in range(16):
            if g[y][x] in (ASPHALT, CONCRETE, MARK) and abs(x - start[0]) + abs(y - start[1]) > 5 and not (ax - 1 <= x <= ax + 7 and ay - 1 <= y <= ay + 7):
                g[y][x] = TRASH
            x, y = min(W - 2, max(1, x + r.choice([-1, 0, 1]))), min(H - 2, max(1, y + r.choice([-1, 0, 1])))
    for _ in range(10):
        x, y = r.randint(2, W - 3), r.randint(2, H - 3)
        if g[y][x] == ASPHALT:
            g[y][x] = PUDDLE
    return r, g, start, (ax, ay)


def build_station(seed, W=56, H=36):
    """Вокзал: бетонные платформы, три полосы путей (зона встреч) с переходами, вокзал и киоски."""
    r = random.Random(seed)
    g = [[CONCRETE] * W for _ in range(H)]
    _border(g, W, H)
    start = (3, H // 2)
    bands = (7, 16, 25)
    crossings = [x for x in range(8, W - 6, 14)]
    for by in bands:
        for y in (by - 1, by + 3):
            for x in range(1, W - 1):
                g[y][x] = PLATFORM
        for y in range(by, by + 3):
            for x in range(1, W - 1):
                g[y][x] = PLATFORM if any(c <= x < c + 3 for c in crossings) else RAIL
    # здание вокзала и киоски (только на бетоне, подальше от старта и путей)
    for bx, by, bw, bh in ((8, 2, 12, 3), (30, 2, 9, 3)):
        for yy in range(by, by + bh):
            for xx in range(bx, bx + bw):
                g[yy][xx] = WALL
    blds = []
    for _ in range(200):
        if len(blds) >= 5:
            break
        bw, bh = r.randint(2, 4), r.randint(2, 3)
        bx, by = r.randint(3, W - bw - 4), r.randint(3, H - bh - 4)
        rows = range(by - 1, by + bh + 1)
        if any(g[y][x] not in (CONCRETE,) for y in rows for x in range(bx - 1, bx + bw + 1)):
            continue
        if bx - 4 <= start[0] <= bx + bw + 4 and by - 4 <= start[1] <= by + bh + 4:
            continue
        if any(bx < ox + ow + 2 and ox < bx + bw + 2 and by < oy + oh + 2 and oy < by + bh + 2 for ox, oy, ow, oh in blds):
            continue
        blds.append((bx, by, bw, bh))
        for yy in range(by, by + bh):
            for xx in range(bx, bx + bw):
                g[yy][xx] = WALL
    ax, ay = _arena(g, W, H)
    for _ in range(12):
        x, y = r.randint(2, W - 3), r.randint(2, H - 3)
        if g[y][x] == CONCRETE and abs(x - start[0]) + abs(y - start[1]) > 4 and not (ax - 1 <= x <= ax + 7 and ay - 1 <= y <= ay + 7):
            g[y][x] = RUBBLE
    for _ in range(10):
        x, y = r.randint(2, W - 3), r.randint(2, H - 3)
        if g[y][x] == CONCRETE:
            g[y][x] = PUDDLE
    for y in range(start[1] - 1, start[1] + 2):          # расчищаем старт
        for x in range(1, 8):
            g[y][x] = CONCRETE
    return r, g, start, (ax, ay)


# ---------------------------------------------------------------- расстановка объектов
THEMES = {
    "dump": {"build": build_dump, "W": 48, "H": 36, "seed": 1, "leader": "leader_dump", "trainers": ["granny_zina", "tramp_petya"],
             "trader": True, "dumpsters": 8, "items": 26,
             "exit": {"side": "east", "target": "vokzal", "spawn": "from_dump", "arrive": "from_vokzal", "requires_badge": "badge_dump",
                      "blocked_text": ["Сторож у выхода: На Вокзал без значка Михалыча не пущу. Порядок такой."]}},
    "vokzal": {"build": build_station, "W": 56, "H": 36, "seed": 2, "leader": "leader_vokzal", "trainers": ["porter_vasya", "kassirsha_lyuda"],
               "trader": False, "dumpsters": 6, "items": 24,
               "exit": {"side": "west", "target": "dump", "spawn": "from_vokzal", "arrive": "from_dump", "requires_badge": None, "blocked_text": None}},
}


def make(theme, seed=None):
    cfg = THEMES[theme]
    seed = cfg["seed"] if seed is None else seed
    W, H = cfg["W"], cfg["H"]
    for attempt in range(200):
        r, g, start, (ax, ay) = cfg["build"](seed + attempt, W, H)
        free = lambda x, y: g[y][x] not in SOLID
        barrel = (start[0] + 2, start[1])
        leader_pos = (ax + 3, ay + 3)
        taken = {start, barrel, leader_pos}
        if not (free(*start) and free(*barrel) and free(start[0] + 1, start[1]) and free(barrel[0], barrel[1] + 1)):
            continue
        objs = [("player_start", "start", *start, {}), ("barrel", "barrel", *barrel, {}),
                ("leader", cfg["leader"], *leader_pos, {"trainer_id": cfg["leader"], "facing": "left"})]
        seen, q = {start}, [start]            # достижимые клетки до расстановки блокирующих объектов
        while q:
            x, y = q.pop()
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                n = (x + dx, y + dy)
                if 0 <= n[0] < W and 0 <= n[1] < H and n not in seen and free(*n):
                    seen.add(n)
                    q.append(n)
        cand = [c for c in sorted(seen) if abs(c[0] - start[0]) + abs(c[1] - start[1]) > 3 and c not in taken
                and not (ax - 1 <= c[0] <= ax + 7 and ay - 1 <= c[1] <= ay + 7)]
        if len(cand) < 80:
            continue
        r.shuffle(cand)
        for tid in cfg["trainers"]:
            x, y = cand.pop()
            objs.append(("trainer", tid, x, y, {"trainer_id": tid, "facing": r.choice(["up", "down", "left", "right"])}))
        if cfg["trader"]:
            near = [c for c in cand if 6 <= abs(c[0] - start[0]) + abs(c[1] - start[1]) <= 14]
            x, y = near[0] if near else cand[0]
            cand.remove((x, y))
            objs.append(("trader", "Меняла", x, y, {}))
        close = [c for c in cand if 4 <= abs(c[0] - start[0]) + abs(c[1] - start[1]) <= 9]
        x, y = close[0] if close else cand[0]
        cand.remove((x, y))
        objs.append(("pc", "ПК", x, y, {}))
        for _ in range(cfg["dumpsters"]):
            x, y = cand.pop()
            objs.append(("dumpster", "dumpster", x, y, {}))
        for _ in range(cfg["items"]):
            x, y = cand.pop()
            objs.append(("item_spot", "item", x, y, {}))
        # выход в соседнюю локацию: проём в заборе с краю карты + точка появления рядом (отдельный Random - раскладка выше не меняется)
        ex = cfg["exit"]
        er = random.Random(seed * 7 + 1)
        inner_x, border_x = (W - 2, W - 1) if ex["side"] == "east" else (1, 0)
        occupied = {(o[2], o[3]) for o in objs}
        ys = [y for y in range(3, H - 3) if (inner_x, y) in seen and (inner_x, y) not in occupied and free(inner_x + (-1 if ex["side"] == "east" else 1), y)
              and not (ax - 1 <= inner_x <= ax + 7 and ay - 1 <= y <= ay + 7)]
        if not ys:
            continue
        y = er.choice(ys)
        g[y][border_x] = CONCRETE
        props = {"target": ex["target"], "spawn": ex["spawn"]}
        if ex["requires_badge"]:
            props["requires_badge"] = ex["requires_badge"]
            props["blocked_text"] = "\n".join(ex["blocked_text"])
        objs.append(("exit", f"to_{ex['target']}", border_x, y, props))
        objs.append(("spawn", ex["arrive"], inner_x, y, {"facing": "left" if ex["side"] == "east" else "right"}))
        return g, objs, (W, H)
    raise RuntimeError("не удалось собрать карту " + theme)


def write_map(theme, seed=None):
    g, objs, (W, H) = make(theme, seed)
    gids = [g[y][x] + 1 for y in range(H) for x in range(W)]
    tiles = []
    for tid in range(NTILES):
        props = []
        if tid in SOLID:
            props.append({"name": "solid", "type": "bool", "value": True})
        if tid in ENCOUNTER:
            props.append({"name": "encounter", "type": "bool", "value": True})
        if props:
            tiles.append({"id": tid, "properties": props})
    out_objs = []
    for i, (typ, name, x, y, props) in enumerate(objs, start=1):
        o = {"id": i, "name": name, "type": typ, "x": x * T, "y": y * T, "width": T, "height": T, "rotation": 0, "visible": True}
        if props:
            o["properties"] = [{"name": k, "type": "string", "value": v} for k, v in props.items()]
        out_objs.append(o)
    tmj = {"compressionlevel": -1, "height": H, "width": W, "infinite": False, "orientation": "orthogonal", "renderorder": "right-down",
           "tiledversion": "1.10.2", "tileheight": T, "tilewidth": T, "type": "map", "version": "1.10", "nextlayerid": 3, "nextobjectid": len(out_objs) + 1,
           "layers": [
               {"id": 1, "name": "ground", "type": "tilelayer", "width": W, "height": H, "x": 0, "y": 0, "opacity": 1, "visible": True, "data": gids},
               {"id": 2, "name": "objects", "type": "objectgroup", "draworder": "topdown", "x": 0, "y": 0, "opacity": 1, "visible": True, "objects": out_objs}],
           "tilesets": [{"firstgid": 1, "name": "placeholder_tileset", "image": "../assets/tiles/placeholder_tileset.png", "imagewidth": T * NTILES, "imageheight": T,
                         "columns": NTILES, "tilecount": NTILES, "tilewidth": T, "tileheight": T, "margin": 0, "spacing": 0, "tiles": tiles}]}
    (ROOT / "maps").mkdir(exist_ok=True)
    path = ROOT / "maps" / f"{theme}.tmj"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(tmj, f, ensure_ascii=False)
    return MapData.load(path)


if __name__ == "__main__":
    args = sys.argv[1:]
    force = "--force" in args
    which = [a for a in args if a in THEMES] or list(THEMES)
    write_tileset(ROOT / "assets" / "tiles" / "placeholder_tileset.png")
    for name in which:
        path = ROOT / "maps" / f"{name}.tmj"
        if path.exists() and not force:
            print(f"{name}: maps/{name}.tmj уже есть - пропускаю (чтобы пересоздать: --force)")
            continue
        m = write_map(name)
        enc = sum(m.prop(x, y, "encounter") for x in range(m.w) for y in range(m.h))
        print(f"{name}: {m.w}x{m.h}, объектов {len(m.objects)}, тайлов встреч {enc}, достижимых клеток {len(m.reachable())}")
