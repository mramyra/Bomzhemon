"""Движок боя. Никакого pygame: получает действия, возвращает список событий для интерфейса.

Действия игрока (submit):
  ("move", slot)            - использовать приём
  ("switch", party_index)   - сменить существо
  ("item", item_id[, idx])  - предмет (idx - цель для лечилок)
  ("run",)                  - сбежать (только в бою с дикими)

События (dict, ключ "t"): msg, hp, status, switch_in, level, faint, catch, end.
"""
import math
import random

from game.battle import stats
from game.battle.creature import STAGE_KEYS
from game.systems import leveling

STATUS_TEXT = {"psn": "отравился", "brn": "обжёгся", "par": "затрясся (тремор)", "slp": "отключился"}
STAGE_TEXT = {"atk": "Атака", "def": "Защита", "spa": "Спец. атака", "spd": "Спец. защита", "spe": "Скорость"}
STRUGGLE = {"id": "struggle", "name": "Отчаяние", "type": None, "category": "physical",
            "power": 50, "accuracy": None, "pp": 1, "priority": 0, "effect": {}}


def stage_mult(s):
    return (2 + s) / 2 if s >= 0 else 2 / (2 - s)


class Side:
    def __init__(self, name, party):
        self.name, self.party = name, party
        self.active = next(i for i, c in enumerate(party) if c.hp > 0)
        self.reset()

    @property
    def mon(self):
        return self.party[self.active]

    def reset(self):
        self.stages = dict.fromkeys(STAGE_KEYS, 0)
        self.confused = 0
        self.flinch = False

    def alive(self):
        return [i for i, c in enumerate(self.party) if c.hp > 0]


class Battle:
    def __init__(self, data, player_party, enemy_party, wild=False, bag=None, rng=None, enemy_name=None):
        self.data, self.rng = data, rng or random.Random()
        self.player, self.enemy = Side("player", player_party), Side("enemy", enemy_party)
        self.wild, self.bag = wild, bag if bag is not None else {}
        self.enemy_name = enemy_name or "Враг"
        self.over, self.result, self.awaiting_switch = False, None, False
        self.caught, self.run_attempts, self.turn = None, 0, 0
        self.participants = {id(self.player.mon)}

    # ------------------------------------------------------------ утилиты
    @staticmethod
    def msg(ev, text):
        ev.append({"t": "msg", "text": text})

    def snapshot(self, side):
        m = side.mon
        return {"side": side.name, "species": m.species_id, "name": m.name, "level": m.level,
                "hp": m.hp, "max": m.max_hp, "status": m.status}

    def start(self):
        ev = []
        if self.wild:
            self.msg(ev, f"Из кустов вылез дикий {self.enemy.mon.name}!")
        else:
            self.msg(ev, f"{self.enemy_name} хочет подраться!")
        ev.append({"t": "switch_in", **self.snapshot(self.enemy)})
        ev.append({"t": "switch_in", **self.snapshot(self.player)})
        self.msg(ev, f"Вперёд, {self.player.mon.name}!")
        return ev

    def eff_stat(self, side, key):
        v = side.mon.stat(key) * stage_mult(side.stages[key])
        if key == "atk" and side.mon.status == "brn":
            v /= 2
        if key == "spe" and side.mon.status == "par":
            v /= 2
        return max(1, int(v))

    def move_of(self, side, slot):
        return STRUGGLE if slot == -1 else self.data.moves[side.mon.moves[slot]["id"]]

    def usable_slots(self, side):
        return [i for i, m in enumerate(side.mon.moves) if m["pp"] > 0]

    # ------------------------------------------------------------ ход
    def submit(self, action):
        ev = []
        if self.over:
            return ev
        if self.awaiting_switch:
            if action[0] == "switch" and self._can_switch(action[1]):
                self._send_out(self.player, action[1], ev)
                self.awaiting_switch = False
            return ev
        if not self._validate(action, ev):
            return ev
        self.turn += 1
        self.player.flinch = self.enemy.flinch = False
        entries = [self._entry(self.player, action), self._entry(self.enemy, self._enemy_action())]
        self.rng.shuffle(entries)  # случайный порядок при полном равенстве
        entries.sort(key=lambda e: (-e["prio"], -e["spe"]))
        for e in entries:
            if self.over or self.awaiting_switch:
                break
            self._do(e, ev)
        if not self.over and not self.awaiting_switch:
            self._end_of_turn(ev)
        return ev

    def _entry(self, side, act):
        prio = 0
        if act[0] in ("switch", "item", "run"):
            prio = 7
        elif act[0] == "move":
            prio = self.move_of(side, act[1])["priority"]
        return {"side": side, "mon": side.mon, "act": act, "prio": prio, "spe": self.eff_stat(side, "spe")}

    def _validate(self, a, ev):
        k = a[0]
        if k == "move":
            if a[1] == -1:
                return not self.usable_slots(self.player)
            if not (0 <= a[1] < len(self.player.mon.moves)) or self.player.mon.moves[a[1]]["pp"] <= 0:
                self.msg(ev, "Силы на этот приём больше нет!")
                return False
            return True
        if k == "switch":
            return self._can_switch(a[1]) and a[1] != self.player.active
        if k == "run":
            if not self.wild:
                self.msg(ev, "От бомжлидера не убежать!")
                return False
            return True
        if k == "item":
            if self.bag.get(a[1], 0) <= 0 or a[1] not in self.data.items:
                return False
            kind = self.data.items[a[1]]["kind"]
            if kind == "catch":
                if not self.wild:
                    self.msg(ev, "Чужих существ коробкой не ловят!")
                    return False
                return True
            if kind in ("heal", "cure") and len(a) > 2 and 0 <= a[2] < len(self.player.party):
                t = self.player.party[a[2]]
                if t.hp <= 0 or (kind == "heal" and t.hp >= t.max_hp) or (kind == "cure" and t.status not in self.data.items[a[1]]["cures"]):
                    self.msg(ev, "Это ничего не даст.")
                    return False
                return True
        return False

    def _can_switch(self, i):
        return 0 <= i < len(self.player.party) and self.player.party[i].hp > 0 and i != self.player.active

    def _do(self, e, ev):
        side, mon, act = e["side"], e["mon"], e["act"]
        if side.mon is not mon or mon.hp <= 0:
            return
        foe = self.enemy if side is self.player else self.player
        k = act[0]
        if k == "switch":
            self.msg(ev, f"{mon.name}, назад!")
            self._send_out(side, act[1], ev)
        elif k == "item":
            self._use_item(act, ev)
        elif k == "run":
            self._try_run(ev)
        elif k == "move":
            self._use_move(side, foe, act[1], ev)

    # ------------------------------------------------------------ приёмы
    def _use_move(self, side, foe, slot, ev):
        mon = side.mon
        move = self.move_of(side, slot)
        who = self._who(side)
        if mon.status == "slp":
            mon.status_turns -= 1
            if mon.status_turns > 0:
                self.msg(ev, f"{who} спит без задних ног.")
                return
            mon.status = None
            ev.append({"t": "status", "side": side.name, "status": None})
            self.msg(ev, f"{who} проснулся!")
        if side.flinch:
            self.msg(ev, f"{who} в страхе и не может двигаться!")
            return
        if mon.status == "par" and self.rng.random() < 0.25:
            self.msg(ev, f"{who} трясёт, ходить не может!")
            return
        if side.confused > 0:
            side.confused -= 1
            if side.confused == 0:
                self.msg(ev, f"{who} пришёл в себя.")
            else:
                self.msg(ev, f"{who} в ступоре...")
                if self.rng.random() < 0.33:
                    dmg = self._raw_damage(mon.level, 40, self.eff_stat(side, "atk"), self.eff_stat(side, "def"))
                    self.msg(ev, f"{who} бьёт сам себя!")
                    self._damage(side, dmg, ev)
                    return
        if slot != -1:
            mon.moves[slot]["pp"] -= 1
        self.msg(ev, f"{who} использует «{move['name']}»!")
        if move["accuracy"] is not None and self.rng.randint(1, 100) > move["accuracy"]:
            self.msg(ev, "Промах!")
            return
        fx = move["effect"]
        if move["category"] != "status":
            dmg, mult, crit = self._calc(side, foe, move)
            if mult == 0:
                self.msg(ev, "Не действует.")
                return
            if crit:
                self.msg(ev, "Критический удар!")
            if mult > 1:
                self.msg(ev, "Очень эффективно!")
            elif mult < 1:
                self.msg(ev, "Малоэффективно...")
            if self._damage(foe, dmg, ev):
                return  # цель выбыла
        if "heal" in fx:
            self._heal_self(side, fx["heal"], ev)
        if "status" in fx and self.rng.randint(1, 100) <= fx["status"]["chance"]:
            self._try_status(foe, fx["status"]["id"], ev, forced=move["category"] == "status")
        if "confuse" in fx and foe.confused == 0 and self.rng.randint(1, 100) <= fx["confuse"]:
            foe.confused = self.rng.randint(2, 4)
            self.msg(ev, f"{self._who(foe)} впал в ступор!")
        if "flinch" in fx and self.rng.randint(1, 100) <= fx["flinch"]:
            foe.flinch = True
        if "stat" in fx:
            s = fx["stat"]
            self._stage(side if s["who"] == "self" else foe, s["stat"], s["stages"], ev)

    def _raw_damage(self, level, power, a, d):
        return (((2 * level // 5 + 2) * power * a // d) // 50) + 2

    def _calc(self, side, foe, move):
        mon, tgt = side.mon, foe.mon
        phys = move["category"] == "physical"
        a = self.eff_stat(side, "atk" if phys else "spa")
        d = self.eff_stat(foe, "def" if phys else "spd")
        dmg = self._raw_damage(mon.level, move["power"], a, d)
        crit = self.rng.random() < 1 / 16
        if crit:
            dmg = int(dmg * 1.5)
        dmg = int(dmg * self.rng.uniform(0.85, 1.0))
        if move["type"] in mon.types:
            dmg = int(dmg * 1.5)
        mult = self.data.type_mult(move["type"], tgt.types)
        return max(1, int(dmg * mult)) if mult else 0, mult, crit

    def _who(self, side):
        return side.mon.name if side is self.player or not self.wild else f"Дикий {side.mon.name}"

    def _damage(self, side, amount, ev):
        """Наносит урон. True, если существо выбыло."""
        m = side.mon
        before = m.hp
        m.hp = max(0, m.hp - amount)
        ev.append({"t": "hp", "side": side.name, "from": before, "to": m.hp, "max": m.max_hp})
        if m.hp == 0:
            self._faint(side, ev)
            return True
        return False

    def _heal_self(self, side, pct, ev):
        m = side.mon
        if m.hp >= m.max_hp:
            self.msg(ev, f"{self._who(side)} и так в полном порядке.")
            return
        before = m.hp
        m.hp = min(m.max_hp, m.hp + max(1, m.max_hp * pct // 100))
        ev.append({"t": "hp", "side": side.name, "from": before, "to": m.hp, "max": m.max_hp})
        self.msg(ev, f"{self._who(side)} подкрепился.")

    def _try_status(self, side, status, ev, forced=False):
        m = side.mon
        if m.status:
            if forced:
                self.msg(ev, "Не подействовало.")
            return
        if status == "psn" and "poison" in m.types:
            if forced:
                self.msg(ev, "Ядовитому яд не страшен.")
            return
        m.status = status
        m.status_turns = self.rng.randint(2, 4) if status == "slp" else 0
        ev.append({"t": "status", "side": side.name, "status": status})
        self.msg(ev, f"{self._who(side)} {STATUS_TEXT[status]}!")

    def _stage(self, side, stat, delta, ev):
        cur = side.stages[stat]
        new = max(-6, min(6, cur + delta))
        if new == cur:
            self.msg(ev, f"{STAGE_TEXT[stat]} {self._who(side)} уже не изменится.")
            return
        side.stages[stat] = new
        word = ("резко " if abs(delta) > 1 else "") + ("вырос" if delta > 0 else "упал")
        self.msg(ev, f"{STAGE_TEXT[stat]} {self._who(side)} {word}!")

    # ------------------------------------------------------------ выбывание, смена, опыт
    def _faint(self, side, ev):
        ev.append({"t": "faint", "side": side.name})
        self.msg(ev, f"{self._who(side)} вырубился!")
        if side is self.enemy:
            self._award_exp(ev)
            alive = side.alive()
            if alive:
                self._send_out(side, alive[0], ev)
            else:
                self._finish("win", ev)
        else:
            if side.alive():
                self.awaiting_switch = True
            else:
                self.msg(ev, "У тебя не осталось бойцов...")
                self._finish("lose", ev)

    def _send_out(self, side, idx, ev):
        side.active = idx
        side.reset()
        if side is self.player:
            self.participants.add(id(side.mon))
            self.msg(ev, f"Вперёд, {side.mon.name}!")
        else:
            self.participants = {id(self.player.mon)}
            self.msg(ev, f"{self.enemy_name} выпускает {side.mon.name}!")
        ev.append({"t": "switch_in", **self.snapshot(side)})

    def _award_exp(self, ev):
        foe = self.enemy.mon
        total = foe.species["base_exp"] * foe.level // 7
        if not self.wild:
            total = int(total * 1.5)
        winners = [c for c in self.player.party if id(c) in self.participants and c.hp > 0]
        if not winners:
            return
        share = max(1, total // len(winners))
        gain = stats.ev_yield(foe.species)
        for c in winners:
            self.msg(ev, f"{c.name} получает {share} опыта.")
            c.gain_ev(gain)
            for kind, val in leveling.apply_exp(self.data, c, share):
                if kind == "level":
                    self.msg(ev, f"{c.name} вырос до {val} уровня!")
                    continue
                name = self.data.moves[val]["name"]
                self.msg(ev, f"{c.name} выучил «{name}»!" if kind == "learned" else f"{c.name} хочет выучить «{name}», но голова забита (4 приёма).")
            if c is self.player.mon:
                ev.append({"t": "level", **self.snapshot(self.player)})

    def _finish(self, result, ev):
        self.over, self.result = True, result
        ev.append({"t": "end", "result": result})

    # ------------------------------------------------------------ предметы, побег
    def _use_item(self, act, ev):
        item_id = act[1]
        item = self.data.items[item_id]
        self.bag[item_id] -= 1
        if item["kind"] == "catch":
            self._throw(item["bonus"], ev)
            return
        target = self.player.party[act[2]]
        self.msg(ev, f"Ты скармливаешь {item['name'].lower()} существу {target.name}.")
        if item["kind"] == "heal":
            before = target.hp
            target.hp = min(target.max_hp, target.hp + item["amount"])
            if target is self.player.mon:
                ev.append({"t": "hp", "side": "player", "from": before, "to": target.hp, "max": target.max_hp})
        else:
            target.status, target.status_turns = None, 0
            if target is self.player.mon:
                ev.append({"t": "status", "side": "player", "status": None})
            self.msg(ev, f"{target.name} отпустило.")

    def _throw(self, bonus, ev):
        w = self.enemy.mon
        self.msg(ev, "Ты накидываешь коробку!")
        sb = 2 if w.status == "slp" else (1.5 if w.status else 1)
        a = (3 * w.max_hp - 2 * w.hp) * w.species["catch_rate"] * bonus * sb / (3 * w.max_hp)
        if a >= 255:
            shakes = 4
        else:
            b = 1048560 / math.sqrt(math.sqrt(16711680 / max(a, 1)))
            shakes = 0
            for _ in range(4):
                if self.rng.randrange(65536) < b:
                    shakes += 1
                else:
                    break
        ok = shakes == 4
        ev.append({"t": "catch", "shakes": shakes, "ok": ok})
        if ok:
            self.msg(ev, f"Готово! {w.name} теперь твой.")
            self.caught = w
            self._finish("caught", ev)
        else:
            self.msg(ev, ["Выскочил сразу!", "Почти!", "Чуть-чуть не хватило!", "Ну вот, опять!"][shakes])

    def _try_run(self, ev):
        self.run_attempts += 1
        a, b = self.eff_stat(self.player, "spe"), self.eff_stat(self.enemy, "spe")
        f = (a * 128 // b + 30 * self.run_attempts) % 256
        if a >= b or self.rng.randrange(256) < f:
            self.msg(ev, "Ты свалил по-тихому.")
            self._finish("run", ev)
        else:
            self.msg(ev, "Не удалось сбежать!")

    # ------------------------------------------------------------ конец хода, ИИ
    def _end_of_turn(self, ev):
        order = sorted([self.player, self.enemy], key=lambda s: -self.eff_stat(s, "spe"))
        for side in order:
            if self.over or self.awaiting_switch:
                return
            m = side.mon
            if m.hp > 0 and m.status in ("psn", "brn"):
                self.msg(ev, f"{self._who(side)} мучается ({'отравление' if m.status == 'psn' else 'ожог'}).")
                self._damage(side, max(1, m.max_hp // (8 if m.status == "psn" else 16)), ev)

    def _enemy_action(self):
        return self.ai_pick(self.enemy)

    def ai_pick(self, side, smart=None):
        """Выбор приёма ИИ для любой стороны. Дикие бьют случайно, тренеры - по оценке урона."""
        foe = self.player if side is self.enemy else self.enemy
        slots = self.usable_slots(side)
        if not slots:
            return ("move", -1)
        if smart is None:
            smart = not self.wild
        if not smart:
            return ("move", self.rng.choice(slots))
        mon, tgt = side.mon, foe.mon

        def score(i):
            mv = self.data.moves[mon.moves[i]["id"]]
            if "heal" in mv["effect"]:
                return 70 if mon.hp < mon.max_hp * 0.5 else 1
            if mv["category"] == "status":
                return 25 if not tgt.status else 5
            s = mv["power"] * self.data.type_mult(mv["type"], tgt.types)
            return s * (1.5 if mv["type"] in mon.types else 1) * (mv["accuracy"] or 100) / 100
        return ("move", max(slots, key=lambda i: score(i) * self.rng.uniform(0.8, 1.2)))
