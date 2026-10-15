"""Генерирует карту-заглушку и тайлсет для Tiled. python -m tools.make_placeholder_map [seed]
Результат: maps/dump.tmj и assets/tiles/placeholder_tileset.png. Потом открываешь dump.tmj в Tiled и правишь руками;
свой тайлсет подключается заменой PNG (те же 32x32 и порядок/номера тайлов) или новым тайлсетом в Tiled."""
import json
import random
import struct
import sys
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from game.world.mapdata import MapData  # noqa: E402

T, W, H = 32, 48, 36
ASPHALT, WALL, TRASH, FENCE, PUDDLE, CONCRETE, MARK, RUBBLE = range(8)
SOLID, ENCOUNTER = {WALL, FENCE, RUBBLE}, {TRASH}
NAMES = ["асфальт", "стена", "свалка (встречи)", "забор", "лужа", "бетон", "разметка", "завал"]


# ---------------------------------------------------------------- тайлсет PNG (без внешних библиотек)
def tile_pixels(tid):
    r = random.Random(tid * 31 + 7)
    px = [[(0, 0, 0)] * T for _ in range(T)]
    base = {ASPHALT: (92, 92, 100), WALL: (150, 100, 80), TRASH: (104, 128, 72), FENCE: (92, 92, 100),
            PUDDLE: (92, 92, 100), CONCRETE: (172, 170, 162), MARK: (92, 92, 100), RUBBLE: (92, 92, 100)}[tid]
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
    return px


def write_tileset(path):
    n = 8
    rows = []
    tiles = [tile_pixels(i) for i in range(n)]
    for y in range(T):
        rows.append(b"".join(bytes(c) for t in tiles for c in t[y]))
    raw = b"".join(b"\x00" + r for r in rows)
    def chunk(t, d):
        return struct.pack(">I", len(d)) + t + d + struct.pack(">I", zlib.crc32(t + d) & 0xFFFFFFFF)
    png = (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", T * n, T, 8, 2, 0, 0, 0))
           + chunk(b"IDAT", zlib.compress(raw, 9)) + chunk(b"IEND", b""))
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_bytes(png)


# ---------------------------------------------------------------- карта
def build(seed):
    r = random.Random(seed)
    g = [[ASPHALT] * W for _ in range(H)]
    for x in range(W):
        g[0][x] = g[H - 1][x] = FENCE
    for y in range(H):
        g[y][0] = g[y][W - 1] = FENCE
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
    ax, ay = W - 10, H - 10                 # арена лидера: расчищаем 7x7
    for yy in range(ay, ay + 7):
        for xx in range(ax, ax + 7):
            g[yy][xx] = CONCRETE
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


def make(seed):
    for attempt in range(200):
        r, g, start, (ax, ay) = build(seed + attempt)
        free = lambda x, y: g[y][x] not in SOLID
        taken = {start, (5, 3), (ax + 3, ay + 3)}
        if not (free(*start) and free(5, 3) and free(4, 3) and free(5, 4)):
            continue
        objs = [("player_start", "start", *start, {}), ("barrel", "barrel", 5, 3, {})]
        objs.append(("leader", "leader_dump", ax + 3, ay + 3, {"trainer_id": "leader_dump", "facing": "left"}))
        # достижимые клетки до расстановки блокирующих объектов
        seen, q = {start}, [start]
        while q:
            x, y = q.pop()
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                n = (x + dx, y + dy)
                if 0 <= n[0] < W and 0 <= n[1] < H and n not in seen and free(*n):
                    seen.add(n)
                    q.append(n)
        cand = [c for c in sorted(seen) if abs(c[0] - start[0]) + abs(c[1] - start[1]) > 3 and c not in taken and not (ax - 1 <= c[0] <= ax + 7 and ay - 1 <= c[1] <= ay + 7)]
        if len(cand) < 80:
            continue
        r.shuffle(cand)
        for tid in ("granny_zina", "tramp_petya"):
            x, y = cand.pop()
            objs.append(("trainer", tid, x, y, {"trainer_id": tid, "facing": r.choice(["up", "down", "left", "right"])}))
        near = [c for c in cand if 6 <= abs(c[0] - start[0]) + abs(c[1] - start[1]) <= 14]
        x, y = near[0] if near else cand[0]
        cand.remove((x, y))
        objs.append(("trader", "Меняла", x, y, {}))
        for _ in range(8):
            x, y = cand.pop()
            objs.append(("dumpster", "dumpster", x, y, {}))
        for _ in range(26):
            x, y = cand.pop()
            objs.append(("item_spot", "item", x, y, {}))
        return g, objs
    raise RuntimeError("не удалось собрать карту")


def write_map(seed=1):
    g, objs = make(seed)
    gids = [g[y][x] + 1 for y in range(H) for x in range(W)]
    tiles = []
    for tid in range(8):
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
           "tilesets": [{"firstgid": 1, "name": "placeholder_tileset", "image": "../assets/tiles/placeholder_tileset.png", "imagewidth": T * 8, "imageheight": T,
                         "columns": 8, "tilecount": 8, "tilewidth": T, "tileheight": T, "margin": 0, "spacing": 0, "tiles": tiles}]}
    (ROOT / "maps").mkdir(exist_ok=True)
    with open(ROOT / "maps" / "dump.tmj", "w", encoding="utf-8") as f:
        json.dump(tmj, f, ensure_ascii=False)
    write_tileset(ROOT / "assets" / "tiles" / "placeholder_tileset.png")
    return MapData.load(ROOT / "maps" / "dump.tmj")


if __name__ == "__main__":
    m = write_map(int(sys.argv[1]) if len(sys.argv) > 1 else 1)
    enc = sum(m.prop(x, y, "encounter") for x in range(m.w) for y in range(m.h))
    print(f"карта {m.w}x{m.h}: объектов {len(m.objects)}, тайлов встреч {enc}, достижимых клеток {len(m.reachable())}")
