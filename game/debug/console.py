"""Консоль отладки: команды без pygame (тестируются отдельно). Интерфейс - game/scenes/console_scene.py.

Номера существ в команде - как в списке `party` (с 1). Виды, предметы и приёмы можно писать по id или по русскому имени
(имена с пробелами - в кавычках)."""
import difflib
import os
import shlex

from game.battle.creature import MAX_LEVEL, exp_for_level
from game.systems import evolution, leveling, moveset, trade

STATUSES = ["psn", "brn", "par", "slp", "none"]
COMMANDS = {}


class CommandError(Exception):
    pass


def cmd(name, usage, help_, args=(), aliases=()):
    def deco(fn):
        entry = {"name": name, "fn": fn, "usage": usage, "help": help_, "args": args}
        COMMANDS[name] = entry
        for a in aliases:
            COMMANDS[a] = dict(entry, alias=True)
        return fn
    return deco


class Console:
    def __init__(self, data, get_state, hooks=None):
        self.data, self.get_state, self.hooks = data, get_state, hooks or {}
        self.log, self.history = [], []

    # ------------------------------------------------------------ выполнение
    def run(self, line):
        """Выполняет строку, пишет в журнал, возвращает новые строки."""
        line = line.strip()
        if not line:
            return []
        self.history.append(line)
        start = len(self.log)
        self.log.append("> " + line)
        try:
            parts = shlex.split(line)
            name, args = parts[0].lower(), parts[1:]
            if name not in COMMANDS:
                near = difflib.get_close_matches(name, COMMANDS, n=3)
                raise CommandError(f"Неизвестная команда «{name}»." + (f" Может, {', '.join(near)}?" if near else " Список: help"))
            out = COMMANDS[name]["fn"](self, args)
            self.log.extend([out] if isinstance(out, str) else (out or []))
        except CommandError as e:
            self.log.append(f"Ошибка: {e}")
        except ValueError as e:
            self.log.append(f"Ошибка: {e}")
        return self.log[start:]

    # ------------------------------------------------------------ помощники для команд
    @property
    def state(self):
        st = self.get_state()
        if st is None:
            raise CommandError("Сначала начни игру (новая игра, продолжить или отладочный хаб).")
        return st

    def hook(self, name):
        if name not in self.hooks:
            raise CommandError("Это сейчас недоступно (нужна карта мира или другой экран).")
        return self.hooks[name]

    def num(self, arg, lo, hi, what="число"):
        try:
            v = int(arg)
        except (TypeError, ValueError):
            raise CommandError(f"{what}: нужно целое число, а не «{arg}».")
        if not lo <= v <= hi:
            raise CommandError(f"{what}: от {lo} до {hi}.")
        return v

    def mon(self, arg):
        party = self.state.party
        if not party:
            raise CommandError("Команда пуста.")
        return party[self.num(arg, 1, len(party), "номер существа") - 1]

    def resolve(self, arg, table, label):
        """id, точное русское имя или однозначное начало -> ключ таблицы."""
        a = str(arg).lower()
        if a in table:
            return a
        by_name = {(v.get("name", "")).lower(): k for k, v in table.items()}
        if a in by_name:
            return by_name[a]
        starts = [k for k in table if k.startswith(a)] + [k for n, k in by_name.items() if n.startswith(a)]
        starts = sorted(set(starts))
        if len(starts) == 1:
            return starts[0]
        pool = list(table) + list(by_name)
        near = starts[:5] or difflib.get_close_matches(a, pool, n=4)
        raise CommandError(f"{label} «{arg}» не найден." + (f" Похожие: {', '.join(near)}" if near else " Список: list"))

    def species(self, arg):
        return self.resolve(arg, self.data.species, "Вид")

    def item(self, arg):
        return self.resolve(arg, self.data.items, "Предмет")

    def move(self, arg):
        return self.resolve(arg, self.data.moves, "Приём")

    def label(self, c):
        return f"{c.name} (Lv{c.level})"

    def pool(self, kind):
        d = self.data
        return {"species": list(d.species), "item": list(d.items), "move": list(d.moves), "trainer": list(d.trainers),
                "status": STATUSES, "list": ["species", "items", "moves", "trainers", "types"], "dex": ["all", "clear"]}.get(kind, [])

    # ------------------------------------------------------------ автодополнение
    def complete(self, line):
        """-> (новая строка, варианты). Вызывать по Tab."""
        parts = line.split(" ")
        cur = parts[-1]
        if len(parts) == 1:
            pool = sorted(k for k, v in COMMANDS.items() if not v.get("alias"))
        else:
            spec = COMMANDS.get(parts[0].lower())
            i = len(parts) - 2
            pool = self.pool(spec["args"][i]) if spec and i < len(spec["args"]) else []
        cands = sorted(x for x in pool if x.startswith(cur.lower()))
        if not cands:
            return line, []
        common = os.path.commonprefix(cands)
        new = common + (" " if len(cands) == 1 else "")
        return " ".join(parts[:-1] + [new]), cands


# ================================================================ команды
@cmd("help", "help [команда]", "Список команд или справка по одной.", ("cmd",), aliases=("?",))
def c_help(con, a):
    if a:
        e = COMMANDS.get(a[0].lower())
        if not e:
            raise CommandError("Нет такой команды.")
        return [f"{e['usage']}", f"  {e['help']}"]
    names = sorted(k for k, v in COMMANDS.items() if not v.get("alias"))
    return ["Команды: " + ", ".join(names), "help <команда> - подробности. Tab - автодополнение, стрелки вверх/вниз - история."]


@cmd("clear", "clear", "Очистить журнал.", aliases=("cls",))
def c_clear(con, a):
    con.log.clear()


@cmd("party", "party", "Список команды.", aliases=("p",))
def c_party(con, a):
    st = con.state
    rows = [f"{i}. {c.name} [{c.species_id}] Lv{c.level} HP {c.hp}/{c.max_hp}" + (f" {c.status}" if c.status else "") + (" +приём" if c.pending_moves else "")
            for i, c in enumerate(st.party, 1)]
    return rows or ["Команда пуста."]


@cmd("storage", "storage", "Список заначки.")
def c_storage(con, a):
    rows = [f"{i}. {c.name} [{c.species_id}] Lv{c.level}" for i, c in enumerate(con.state.storage, 1)]
    return rows or ["Заначка пуста."]


@cmd("info", "info <номер>", "Подробности существа: опыт, статы, приёмы.", ("int",), aliases=("i",))
def c_info(con, a):
    if not a:
        raise CommandError("Укажи номер: info 1")
    c, d = con.mon(a[0]), con.data
    got, need, _ = c.exp_progress()
    st = ", ".join(f"{k} {c.max_hp if k == 'hp' else c.stat(k)}" for k in ("hp", "atk", "def", "spa", "spd", "spe"))
    mv = ", ".join(f"{d.moves[m['id']]['name']} {m['pp']}/{m['max_pp']}" for m in c.moves)
    out = [f"{c.name} [{c.species_id}] {'/'.join(c.types)} Lv{c.level}  HP {c.hp}/{c.max_hp}  {c.status or 'в норме'}",
           f"Опыт {c.exp} (до след. уровня {need - got if need else '-'})", st, f"Приёмы: {mv}"]
    if c.pending_moves:
        out.append("Ждут выучки: " + ", ".join(c.pending_moves))
    out += moveset.evolution_hints(d, c)
    return out


@cmd("give", "give <вид> [уровень=5] [кол-во=1]", "Выдать существо (в команду, если есть место, иначе в заначку).", ("species", "int", "int"))
def c_give(con, a):
    if not a:
        raise CommandError("Укажи вид: give rat 10")
    sid = con.species(a[0])
    lvl = con.num(a[1], 1, MAX_LEVEL, "уровень") if len(a) > 1 else 5
    n = con.num(a[2], 1, 30, "количество") if len(a) > 2 else 1
    out = []
    for _ in range(n):
        c = con.data.make_creature(sid, lvl)
        out.append(f"Выдан {con.label(c)} -> {'команда' if con.state.add_creature(c) == 'party' else 'заначка'}")
    return out if n <= 3 else [f"Выдано {n} x {con.data.species[sid]['name']} Lv{lvl} (команда/заначка)."]


@cmd("giveall", "giveall [уровень=10]", "Выдать по одному существу каждого вида (в основном в заначку).", ("int",))
def c_giveall(con, a):
    lvl = con.num(a[0], 1, MAX_LEVEL, "уровень") if a else 10
    for sid in con.data.species:
        con.state.add_creature(con.data.make_creature(sid, lvl))
    return [f"Выдано видов: {len(con.data.species)}. Заначка: {len(con.state.storage)}, команда: {len(con.state.party)}."]


@cmd("level", "level <номер> <уровень> [keep]", "Поставить уровень (опыт и приёмы пересобираются; keep - оставить приёмы).", ("int", "int", "keep"), aliases=("lvl",))
def c_level(con, a):
    if len(a) < 2:
        raise CommandError("level <номер> <уровень>")
    c = con.mon(a[0])
    lvl = con.num(a[1], 1, MAX_LEVEL, "уровень")
    ratio = c.hp / c.max_hp
    c.level, c.exp = lvl, exp_for_level(lvl)
    c.recalc()
    c.hp = max(1, round(c.max_hp * ratio))
    if not (len(a) > 2 and a[2] == "keep"):
        fresh = con.data.make_creature(c.species_id, lvl)
        c.moves, c.pending_moves = fresh.moves, []
    out = [f"{c.name}: уровень {lvl}, HP {c.hp}/{c.max_hp}."]
    nxt = evolution.level_evolution(c)
    if nxt:
        out.append(f"Можно эволюционировать: evolve {a[0]}  (или checkevo)")
    return out


@cmd("exp", "exp <номер> <кол-во>", "Начислить опыт как после боя (с повышением уровней и ждущими приёмами).", ("int", "int"))
def c_exp(con, a):
    if len(a) < 2:
        raise CommandError("exp <номер> <кол-во>")
    c = con.mon(a[0])
    out = [f"{c.name} +{con.num(a[1], 1, 10 ** 7, 'опыт')} опыта."]
    for kind, val in leveling.apply_exp(con.data, c, int(a[1])):
        if kind == "level":
            out.append(f"  уровень {val}")
        else:
            out.append(f"  {'выучил' if kind == 'learned' else 'хочет выучить'} {con.data.moves[val]['name']}")
    if evolution.level_evolution(c):
        out.append("  готов к эволюции: checkevo")
    return out


@cmd("evolve", "evolve <номер> [вид]", "Эволюция: без вида - первая возможная (даже если условие не выполнено), с видом - принудительно в любой вид.", ("int", "species"))
def c_evolve(con, a):
    if not a:
        raise CommandError("evolve <номер> [вид]")
    c, d = con.mon(a[0]), con.data
    old = c.name
    if len(a) > 1:
        into, how = con.species(a[1]), "принудительно"
    else:
        into = evolution.level_evolution(c)
        how = "по уровню"
        if not into and c.species["evolutions"]:
            into, how = c.species["evolutions"][0]["into"], "условие проигнорировано"
    if not into:
        return [f"{c.name} не эволюционирует. (Вид можно указать явно: evolve {a[0]} <вид>)"]
    evolution.evolve(d, c, into)
    return [f"{old} -> {c.species['name']} ({how}). HP {c.hp}/{c.max_hp}."]


@cmd("checkevo", "checkevo", "Прогнать проверку эволюций по уровню у всей команды (как после боя).")
def c_checkevo(con, a):
    out = []
    for c in con.state.party:
        into = evolution.level_evolution(c)
        while into:
            old = c.name
            evolution.evolve(con.data, c, into)
            out.append(f"{old} эволюционировал в {c.species['name']}!")
            into = evolution.level_evolution(c)
    return out or ["Эволюций нет."]


@cmd("useitem", "useitem <номер> <предмет>", "Применить предмет эволюции/лечения к существу как в сумке (предмет не тратится).", ("int", "item"))
def c_useitem(con, a):
    if len(a) < 2:
        raise CommandError("useitem <номер> <предмет>")
    c, iid = con.mon(a[0]), con.item(a[1])
    it = con.data.items[iid]
    if it["kind"] == "evolution":
        into = evolution.item_evolution(c, iid)
        if not into:
            return [f"{c.name} не реагирует на «{it['name']}»."]
        old = c.name
        evolution.evolve(con.data, c, into)
        return [f"{old} -> {c.species['name']} (предмет «{it['name']}»)."]
    if it["kind"] == "heal":
        c.hp = min(c.max_hp, c.hp + it["amount"])
        return [f"{c.name}: HP {c.hp}/{c.max_hp}."]
    if it["kind"] == "cure":
        c.status = None
        return [f"{c.name} отпустило."]
    return ["Этот предмет применяется только в бою."]


@cmd("trade", "trade <номер> [получить]", "Обмен с Меняльщиком: без второго аргумента - варианты, с ним - выполнить (получаешь вид и он эволюционирует).", ("int", "species"))
def c_trade(con, a):
    if not a:
        raise CommandError("trade <номер> [получить]")
    give, d = con.mon(a[0]), con.data
    opts = trade.options_for(d, give.species_id)
    if not opts:
        return [f"За {give.name} обмена нет."]
    if len(a) < 2:
        return [f"За {give.name} можно получить: " + ", ".join(f"{rs} (станет {into})" for rs, into in opts)]
    rs = con.species(a[1])
    match = [o for o in opts if o[0] == rs]
    if not match:
        raise CommandError("Такого обмена нет. Варианты: trade " + a[0])
    new = trade.execute(d, con.state, give, rs, match[0][1])
    return [f"{give.name} -> {new.name} (Lv{new.level})."]


@cmd("item", "item <предмет> [кол-во=1]", "Выдать предмет.", ("item", "int"))
def c_item(con, a):
    if not a:
        raise CommandError("item <предмет> [кол-во]")
    iid = con.item(a[0])
    n = con.num(a[1], 1, 999, "количество") if len(a) > 1 else 1
    con.state.add_item(iid, n)
    return [f"+{n} {con.data.items[iid]['name']} (теперь {con.state.bag[iid]})."]


@cmd("bag", "bag", "Содержимое сумки.")
def c_bag(con, a):
    rows = [f"{con.data.items[k]['name']} [{k}] x{n}" for k, n in con.state.bag.items() if n > 0]
    return rows or ["Сумка пуста."]


@cmd("heal", "heal", "Вылечить всю команду.")
def c_heal(con, a):
    con.state.heal_party()
    return ["Команда здорова."]


@cmd("hp", "hp <номер> <значение>", "Поставить HP (удобно для тестов ловли и статусов).", ("int", "int"))
def c_hp(con, a):
    if len(a) < 2:
        raise CommandError("hp <номер> <значение>")
    c = con.mon(a[0])
    c.hp = con.num(a[1], 0, c.max_hp, "HP")
    return [f"{c.name}: HP {c.hp}/{c.max_hp}."]


@cmd("status", "status <номер> <psn|brn|par|slp|none>", "Повесить статус.", ("int", "status"))
def c_status(con, a):
    if len(a) < 2 or a[1] not in STATUSES:
        raise CommandError("status <номер> <psn|brn|par|slp|none>")
    c = con.mon(a[0])
    c.status = None if a[1] == "none" else a[1]
    c.status_turns = 3 if c.status == "slp" else 0
    return [f"{c.name}: {c.status or 'в норме'}."]


@cmd("teach", "teach <номер> <приём> [ячейка 1-4]", "Научить приёму. Без ячейки: в свободную или в очередь выучки, если 4 приёма.", ("int", "move", "int"))
def c_teach(con, a):
    if len(a) < 2:
        raise CommandError("teach <номер> <приём> [ячейка]")
    c, mid = con.mon(a[0]), con.move(a[1])
    name = con.data.moves[mid]["name"]
    if len(a) > 2:
        forgot = moveset.learn_move(con.data, c, mid, con.num(a[2], 1, len(c.moves), "ячейка") - 1)
        return [f"{c.name}: «{name}» вместо «{con.data.moves[forgot]['name']}»." if forgot else f"{c.name} и так знает «{name}»."]
    if any(m["id"] == mid for m in c.moves):
        return [f"{c.name} и так знает «{name}»."]
    return [f"{c.name} выучил «{name}»." if c.learn(con.data, mid) else f"{c.name}: «{name}» ждёт в очереди выучки (откроется после боя или в окне Команда)."]


@cmd("store", "store <номер>", "Убрать существо из команды в заначку.", ("int",))
def c_store(con, a):
    st = con.state
    if not a:
        raise CommandError("store <номер>")
    if len(st.party) <= 1:
        raise CommandError("Последнего бойца в заначку не убрать.")
    c = st.party.pop(con.num(a[0], 1, len(st.party), "номер существа") - 1)
    st.storage.append(c)
    return [f"{c.name} -> заначка."]


@cmd("take", "take <номер в заначке>", "Достать существо из заначки в команду.", ("int",))
def c_take(con, a):
    st = con.state
    if not a:
        raise CommandError("take <номер>  (список: storage)")
    if len(st.party) >= 6:
        raise CommandError("Команда полна (6).")
    if not st.storage:
        raise CommandError("Заначка пуста.")
    c = st.storage.pop(con.num(a[0], 1, len(st.storage), "номер в заначке") - 1)
    st.party.append(c)
    return [f"{c.name} -> команда."]


@cmd("money", "money <число>", "Прибавить (или отнять, если минус) монеты.", ("int",))
def c_money(con, a):
    if not a:
        return [f"Монеты: {con.state.money}"]
    con.state.money = max(0, con.state.money + con.num(a[0], -10 ** 7, 10 ** 7, "монеты"))
    return [f"Монеты: {con.state.money}"]


@cmd("badge", "badge <id>", "Выдать значок (id из trainers.json, поле badge).", ())
def c_badge(con, a):
    if not a:
        return ["Значки: " + (", ".join(con.state.badges) or "нет")]
    if a[0] not in con.state.badges:
        con.state.badges.append(a[0])
    return ["Значки: " + ", ".join(con.state.badges)]


@cmd("dex", "dex <all|clear>", "Заполнить Бомждекс (встречены и пойманы) или очистить.", ("dex",))
def c_dex(con, a):
    st = con.state
    if not a or a[0] not in ("all", "clear"):
        return [f"Встречено {len(st.seen)}, поймано {len(st.caught)} из {len(con.data.species)}. dex all | dex clear"]
    ids = set(con.data.species) if a[0] == "all" else {c.species_id for c in st.party + st.storage}
    st.seen, st.caught = set(ids), set(ids)
    return [f"Бомждекс: {len(st.caught)}/{len(con.data.species)}."]


@cmd("list", "list <species|items|moves|trainers|types>", "Показать id из данных.", ("list",), aliases=("ls",))
def c_list(con, a):
    d = con.data
    tables = {"species": d.species, "items": d.items, "moves": d.moves, "trainers": d.trainers, "types": d.types}
    if not a or a[0] not in tables:
        raise CommandError("list <species|items|moves|trainers|types>")
    t = tables[a[0]]
    return [", ".join(f"{k} ({v.get('name', k)})" for k, v in t.items())]


@cmd("battle", "battle <вид> [уровень=5]", "Дикий бой с выбранным существом (закроет консоль).", ("species", "int"), aliases=("fight",))
def c_battle(con, a):
    if not a:
        raise CommandError("battle <вид> [уровень]")
    if not con.state.has_usable():
        raise CommandError("Нет боеспособных существ: heal")
    sid = con.species(a[0])
    lvl = con.num(a[1], 1, MAX_LEVEL, "уровень") if len(a) > 1 else 5
    con.hook("battle")(con.data.make_creature(sid, lvl))
    return [f"Бой: {con.data.species[sid]['name']} Lv{lvl}."]


@cmd("trainer", "trainer <id>", "Бой с тренером или лидером (сбрасывает его победу).", ("trainer",))
def c_trainer(con, a):
    if not a:
        raise CommandError("trainer <id>  (список: list trainers)")
    if not con.state.has_usable():
        raise CommandError("Нет боеспособных существ: heal")
    tid = con.resolve(a[0], con.data.trainers, "Тренер")
    con.state.defeated.discard(tid)
    con.hook("trainer")(tid)
    return [f"Бой с тренером: {con.data.trainers[tid]['name']}."]


@cmd("tp", "tp <x> <y>", "Телепорт по карте (клетки). Без аргументов - показать позицию.", ("int", "int"))
def c_tp(con, a):
    if not a:
        return [f"Позиция: {con.hook('pos')()}"]
    if len(a) < 2:
        raise CommandError("tp <x> <y>")
    x, y = con.num(a[0], 0, 999, "x"), con.num(a[1], 0, 999, "y")
    return [f"Телепорт в ({x}, {y})." if con.hook("teleport")(x, y) else "Туда нельзя (стена или за картой)."]


@cmd("save", "save", "Сохранить игру в слот 1.")
def c_save(con, a):
    con.hook("save")()
    return ["Сохранено."]


@cmd("close", "close", "Закрыть консоль.", aliases=("exit", "quit"))
def c_close(con, a):
    con.hook("close")()
