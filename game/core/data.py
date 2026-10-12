"""Загрузка и валидация контента из data/*.json. Весь контент живёт в JSON, не в коде."""
import json
import random
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parents[2] / "data"


class GameData:
    def __init__(self, folder=DATA_DIR):
        def load(name):
            with open(Path(folder) / name, encoding="utf-8") as f:
                return json.load(f)

        t = load("types.json")
        self.types = {x["id"]: x for x in t["types"]}
        self.chart = t["chart"]
        self.moves = load("moves.json")
        self.species = load("species.json")
        self.items = load("items.json")
        self.fusions = load("fusions.json")
        self.trainers = load("trainers.json")
        self.districts = load("districts.json")

    # ---- типы
    def type_mult(self, atk_type, def_types):
        if atk_type is None:
            return 1.0
        m = 1.0
        for d in def_types:
            m *= self.chart.get(atk_type, {}).get(d, 1.0)
        return m

    # ---- фабрики
    def make_creature(self, species_id, level):
        from game.battle.creature import Creature
        return Creature.create(self, species_id, level)

    def roll_encounter(self, district_id, rng=None):
        rng = rng or random
        enc = self.districts[district_id]["encounters"]
        e = rng.choices(enc, weights=[x["weight"] for x in enc])[0]
        return self.make_creature(e["species"], rng.randint(e["min"], e["max"]))

    def roll_item(self, district_id, rng=None):
        rng = rng or random
        spawns = self.districts[district_id]["item_spawns"]
        return rng.choices(spawns, weights=[x["weight"] for x in spawns])[0]["item"]

    # ---- проверка целостности (запускается в тестах)
    def validate(self):
        errs = []
        for tid, row in self.chart.items():
            if tid not in self.types:
                errs.append(f"chart: неизвестный тип {tid}")
            for d in row:
                if d not in self.types:
                    errs.append(f"chart[{tid}]: неизвестный тип {d}")
        for mid, m in self.moves.items():
            if m["type"] not in self.types:
                errs.append(f"move {mid}: тип {m['type']}")
            if m["category"] not in ("physical", "special", "status"):
                errs.append(f"move {mid}: категория")
        for sid, s in self.species.items():
            for t in s["types"]:
                if t not in self.types:
                    errs.append(f"species {sid}: тип {t}")
            for lvl, mv in s["learnset"]:
                if mv not in self.moves:
                    errs.append(f"species {sid}: приём {mv}")
            for ev in s["evolutions"]:
                if ev["into"] not in self.species:
                    errs.append(f"species {sid}: эволюция в {ev['into']}")
                if ev["method"] == "item" and ev["item"] not in self.items:
                    errs.append(f"species {sid}: предмет {ev['item']}")
            if not any(l == 1 for l, _ in s["learnset"]):
                errs.append(f"species {sid}: нет приёмов на 1 уровне")
        for fid in self.fusions:
            for sp in fid["inputs"]:
                if sp not in self.species:
                    errs.append(f"fusion {fid['id']}: {sp}")
            if fid["result"] not in self.species:
                errs.append(f"fusion {fid['id']}: result")
        for tid, tr in self.trainers.items():
            for sp, _ in tr["party"]:
                if sp not in self.species:
                    errs.append(f"trainer {tid}: {sp}")
        for did, d in self.districts.items():
            for e in d["encounters"]:
                if e["species"] not in self.species:
                    errs.append(f"district {did}: {e['species']}")
            for i in d["item_spawns"]:
                if i["item"] not in self.items:
                    errs.append(f"district {did}: item {i['item']}")
        return errs
