"""Существо (экземпляр): уровень, HP, приёмы, статус, IV/EV/характер. Чистая логика, без pygame."""
from game.battle import stats as S

STAGE_KEYS = ("atk", "def", "spa", "spd", "spe")
MAX_LEVEL = 100


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
        self.iv = dict.fromkeys(S.STAT_KEYS, S.IV_DEFAULT)     # врождённый потенциал 0..31
        self.ev = dict.fromkeys(S.STAT_KEYS, 0)                 # тренировка (растёт от побед)
        self.nature = S.NEUTRAL
        self.declined_evolution_level = None    # уровень, на котором игрок отменил эволюцию (спросим снова на следующем)
        self.moves = []                 # [{"id","pp","max_pp"}]
        self.pending_moves = []         # приёмы, которые не влезли (макс. 4)
        self.recalc()

    # ---- создание
    @classmethod
    def create(cls, data, species_id, level, rng=None, iv=None, ev=None, nature=None, flat=False):
        """iv: None (случайные) / число (все одинаковые) / словарь. flat=True - все IV=15, характер нейтральный (для тестов и баланса)."""
        c = cls(species_id, data.species[species_id])
        c.level = level
        c.exp = exp_for_level(level)
        if iv is None and flat:
            iv = S.IV_DEFAULT
        if iv is None:
            c.iv = S.roll_ivs(rng, perfect=3 if c.species.get("legendary") else 0)
        elif isinstance(iv, int):
            c.iv = dict.fromkeys(S.STAT_KEYS, max(0, min(S.IV_MAX, iv)))
        else:
            c.iv = {k: max(0, min(S.IV_MAX, int(iv[k]))) for k in S.STAT_KEYS}
        if ev:
            c.ev = {k: int(ev.get(k, 0)) for k in S.STAT_KEYS}
        c.nature = nature if nature in S.NATURES else (S.NEUTRAL if flat else S.roll_nature(rng))
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

    def value(self, key):
        """Итоговое значение любой из шести характеристик (включая hp)."""
        return self.max_hp if key == "hp" else self._stats[key]

    @property
    def ev_total(self):
        return sum(self.ev.values())

    @property
    def iv_total(self):
        return sum(self.iv.values())

    def recalc(self):
        b = self.species["base"]
        self.max_hp = S.calc_hp(b["hp"], self.level, self.iv["hp"], self.ev["hp"])
        self._stats = {k: S.calc_other(b[k], self.level, self.iv[k], self.ev[k], S.nature_mult(self.nature, k)) for k in STAGE_KEYS}

    def refresh_stats(self):
        """Пересчёт характеристик: если максимум HP вырос, текущее HP растёт на ту же величину."""
        old = self.max_hp
        self.recalc()
        if self.hp > 0 and self.max_hp > old:
            self.hp += self.max_hp - old
        self.hp = min(self.hp, self.max_hp)

    # ---- прокачка
    def level_up(self):
        self.level += 1
        self.refresh_stats()

    def gain_ev(self, amounts):
        """Начислить EV (словарь {характеристика: очки}) с учётом лимитов 252 на характеристику и 510 всего. True - что-то изменилось."""
        changed = False
        for k, n in amounts.items():
            room = min(n, S.EV_STAT_MAX - self.ev[k], S.EV_TOTAL_MAX - self.ev_total)
            if room > 0:
                self.ev[k] += room
                changed = True
        if changed:
            self.refresh_stats()
        return changed

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
                "iv": dict(self.iv), "ev": dict(self.ev), "nature": self.nature, "declined_evo": self.declined_evolution_level,
                "moves": [dict(m) for m in self.moves], "pending_moves": list(self.pending_moves)}

    @classmethod
    def from_dict(cls, data, d):
        c = cls(d["species"], data.species[d["species"]])
        c.level, c.exp, c.hp = d["level"], d["exp"], d["hp"]
        c.status, c.status_turns, c.nickname = d["status"], d["status_turns"], d["nickname"]
        c.moves, c.pending_moves = [dict(m) for m in d["moves"]], list(d["pending_moves"])
        # сохранения старых версий без IV/EV/характера: средние IV, нулевые EV, нейтральный характер
        iv, ev = d.get("iv") or {}, d.get("ev") or {}
        c.iv = {k: max(0, min(S.IV_MAX, int(iv.get(k, S.IV_DEFAULT)))) for k in S.STAT_KEYS}
        c.ev = {k: max(0, min(S.EV_STAT_MAX, int(ev.get(k, 0)))) for k in S.STAT_KEYS}
        c.nature = d.get("nature") if d.get("nature") in S.NATURES else S.NEUTRAL
        c.declined_evolution_level = d.get("declined_evo")
        c.recalc()
        return c
