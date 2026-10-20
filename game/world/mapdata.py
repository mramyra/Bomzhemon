"""Карта из Tiled (JSON, .tmj). Чистые данные, без pygame - проверяется тестами.

Требования к карте в Tiled (Tile Layer Format = CSV, размер тайла 32x32):
  - тайловый слой "ground" (обязателен); необязательный "top" (рисуется поверх игрока, коллизий нет)
  - группа объектов "objects": прямоугольники 32x32 с полем Type (class):
      player_start, barrel, dumpster, item_spot, trainer, leader, trader (Меняла), pc (ПК)
    у trainer/leader свойство trainer_id (ключ из data/trainers.json), свойство facing (up/down/left/right)
  - свойства тайлов в тайлсете: solid (bool) - нельзя пройти; encounter (bool) - здесь встречаются существа
"""
import json
from collections import deque
from pathlib import Path

BLOCKING = {"barrel", "dumpster", "trainer", "leader", "trader", "pc"}
DIRS = {"up": (0, -1), "down": (0, 1), "left": (-1, 0), "right": (1, 0)}


class MapObject:
    def __init__(self, raw, tw, th):
        self.id, self.name, self.type = raw["id"], raw.get("name", ""), raw.get("type") or raw.get("class", "")
        self.x, self.y = int(raw["x"] // tw), int(raw["y"] // th)
        self.props = {p["name"]: p["value"] for p in raw.get("properties", [])}

    @property
    def blocking(self):
        return self.type in BLOCKING


class MapData:
    def __init__(self, raw, folder):
        self.w, self.h, self.tw, self.th = raw["width"], raw["height"], raw["tilewidth"], raw["tileheight"]
        self.layers, self.objects, self.tile_props = {}, [], {}
        self.tileset = None
        for ts in raw["tilesets"]:
            first = ts["firstgid"]
            for t in ts.get("tiles", []):
                self.tile_props[first + t["id"]] = {p["name"]: p["value"] for p in t.get("properties", [])}
            self.tileset = {"first": first, "columns": ts["columns"], "tw": ts["tilewidth"], "th": ts["tileheight"],
                            "image": (Path(folder) / ts["image"]).resolve()}
        for ly in raw["layers"]:
            if ly["type"] == "tilelayer":
                self.layers[ly["name"]] = ly["data"]
            elif ly["type"] == "objectgroup":
                self.objects += [MapObject(o, self.tw, self.th) for o in ly["objects"]]
        if "ground" not in self.layers:
            raise ValueError("в карте нет слоя 'ground'")

    @classmethod
    def load(cls, path):
        path = Path(path)
        with open(path, encoding="utf-8") as f:
            return cls(json.load(f), path.parent)

    def gid(self, x, y, layer="ground"):
        return self.layers[layer][y * self.w + x] if layer in self.layers and 0 <= x < self.w and 0 <= y < self.h else 0

    def prop(self, x, y, name):
        return bool(self.tile_props.get(self.gid(x, y), {}).get(name, False))

    def objects_of(self, *types):
        return [o for o in self.objects if o.type in types]

    def object_at(self, x, y):
        return next((o for o in self.objects if o.x == x and o.y == y and o.type != "item_spot"), None)

    def inside(self, x, y):
        return 0 <= x < self.w and 0 <= y < self.h

    def blocked(self, x, y):
        if not self.inside(x, y) or self.prop(x, y, "solid"):
            return True
        o = self.object_at(x, y)
        return bool(o and o.blocking)

    def start(self):
        o = self.objects_of("player_start")
        return (o[0].x, o[0].y) if o else (1, 1)

    def reachable(self, frm=None):
        """Клетки, до которых можно дойти от старта (BFS по 4 направлениям)."""
        sx, sy = frm or self.start()
        seen, q = {(sx, sy)}, deque([(sx, sy)])
        while q:
            x, y = q.popleft()
            for dx, dy in DIRS.values():
                n = (x + dx, y + dy)
                if n not in seen and not self.blocked(*n):
                    seen.add(n)
                    q.append(n)
        return seen
