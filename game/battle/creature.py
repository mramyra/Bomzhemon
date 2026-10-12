"""Существо (экземпляр): уровень, HP, приёмы, статус. Чистая логика, без pygame."""

STAGE_KEYS = ("atk", "def", "spa", "spd", "spe")
MAX_LEVEL = 100


def calc_stat(base, level, is_hp=False):
    v = (2 * base * level) // 100
    return v + level + 10 if is_hp else v + 5


def exp_for_level(level):
    return level ** 3


class Creature:
    def __init__(self, species_id, species):
        self.species_id = species_id
        self.species = species          # dict из species.json
        self.level = 1
        self.exp = 1
        self.hp = 1
        self.status = None              # psn / brn / par / slp
        self.status_turns = 0
        self.nickname = None
        self.moves = []                 # [{"id","pp","max_pp"}]
        self.pending_moves = []         # приёмы, которые не влезли (макс. 4)
        self.recalc()

    # ---- создание
    @classmethod
    def create(cls, data, species_id, level):
        c = cls(species_id, data.species[species_id])
        c.level = level
        c.exp = exp_for_level(level)
        c.recalc()
        c.hp = c.max_hp
        known = [m for lv, m in c.species["learnset"] if lv <= level]
        for mid in known[-4:]:
            c.moves.append({"id": mid, "pp": data.moves[mid]["pp"], "max_pp": data.moves[mid]["pp"]})
        return c

    # ---- свойства
    @property
    def name(self):
        return self.nickname or self.species["name"]

    @property
    def types(self):
        return self.species["types"]

    def stat(self, key):
        return self._stats[key]

    def recalc(self):
        b = self.species["base"]
        self._stats = {k: calc_stat(b[k], self.level) for k in STAGE_KEYS}
        self.max_hp = calc_stat(b["hp"], self.level, is_hp=True)

    # ---- прокачка
    def level_up(self):
        old = self.max_hp
        self.level += 1
        self.recalc()
        self.hp += self.max_hp - old

    def learn(self, data, move_id):
        """True - выучил сразу, False - в очередь (нет места)."""
        if any(m["id"] == move_id for m in self.moves) or move_id in self.pending_moves:
            return True
        if len(self.moves) < 4:
            pp = data.moves[move_id]["pp"]
            self.moves.append({"id": move_id, "pp": pp, "max_pp": pp})
            return True
        self.pending_moves.append(move_id)
        return False

    def exp_progress(self):
        """(набрано на этом уровне, нужно до следующего, доля 0..1). На максимальном уровне (0, 0, 1.0)."""
        if self.level >= MAX_LEVEL:
            return 0, 0, 1.0
        base, nxt = exp_for_level(self.level), exp_for_level(self.level + 1)
        got = max(0, self.exp - base)
        return got, nxt - base, min(1.0, got / (nxt - base))

    def heal_full(self):
        self.hp = self.max_hp
        self.status, self.status_turns = None, 0
        for m in self.moves:
            m["pp"] = m["max_pp"]

    # ---- сохранение
    def to_dict(self):
        return {"species": self.species_id, "level": self.level, "exp": self.exp, "hp": self.hp,
                "status": self.status, "status_turns": self.status_turns, "nickname": self.nickname,
                "moves": [dict(m) for m in self.moves], "pending_moves": list(self.pending_moves)}

    @classmethod
    def from_dict(cls, data, d):
        c = cls(d["species"], data.species[d["species"]])
        c.level, c.exp, c.hp = d["level"], d["exp"], d["hp"]
        c.status, c.status_turns, c.nickname = d["status"], d["status_turns"], d["nickname"]
        c.moves, c.pending_moves = [dict(m) for m in d["moves"]], list(d["pending_moves"])
        c.recalc()
        return c
