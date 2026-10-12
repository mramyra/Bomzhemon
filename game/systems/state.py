"""Состояние игрока: всё, что попадает в сохранение."""
import random

from game.battle.creature import Creature

PARTY_MAX = 6


class PlayerState:
    def __init__(self):
        self.party, self.storage = [], []
        self.bag = {"box": 5}
        self.money = 0
        self.badges = []
        self.seen, self.caught = set(), set()
        self.defeated = set()           # id побеждённых тренеров
        self.pos = {"map": "dump", "x": None, "y": None}   # None - ещё не ставили на карту
        self.flags = {}
        self.seed = random.randrange(2 ** 31)   # сид расстановки существ и предметов на карте
        self.play_seconds = 0

    def add_creature(self, c):
        """Возвращает 'party' или 'storage'."""
        self.seen.add(c.species_id)
        self.caught.add(c.species_id)
        if len(self.party) < PARTY_MAX:
            self.party.append(c)
            return "party"
        self.storage.append(c)
        return "storage"

    def add_item(self, item_id, n=1):
        self.bag[item_id] = self.bag.get(item_id, 0) + n

    def heal_party(self):
        for c in self.party:
            c.heal_full()

    def has_usable(self):
        return any(c.hp > 0 for c in self.party)

    def to_dict(self):
        return {"version": 1, "party": [c.to_dict() for c in self.party], "storage": [c.to_dict() for c in self.storage],
                "bag": self.bag, "money": self.money, "badges": self.badges, "seen": sorted(self.seen),
                "caught": sorted(self.caught), "defeated": sorted(self.defeated), "pos": self.pos,
                "flags": self.flags, "seed": self.seed, "play_seconds": self.play_seconds}

    @classmethod
    def from_dict(cls, data, d):
        s = cls()
        s.party = [Creature.from_dict(data, x) for x in d["party"]]
        s.storage = [Creature.from_dict(data, x) for x in d["storage"]]
        s.bag, s.money, s.badges = d["bag"], d["money"], d["badges"]
        s.seen, s.caught, s.defeated = set(d["seen"]), set(d["caught"]), set(d["defeated"])
        s.pos, s.flags, s.seed, s.play_seconds = d["pos"], d["flags"], d["seed"], d["play_seconds"]
        return s
