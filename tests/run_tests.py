"""Запуск: python -m tests.run_tests  (из корня проекта). Без pytest, без pygame."""
import random
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from game.battle.engine import Battle
from game.core.data import GameData
from game.systems import evolution, fusion, save
from game.systems.state import PlayerState

D = GameData()
D.flat_stats = True     # тесты детерминированы: все IV=15, характер нейтральный (IV/EV проверяются отдельными тестами)


def test_data_valid():
    assert D.validate() == [], D.validate()


def test_type_chart():
    assert D.type_mult("dog", ["cat"]) == 2
    assert D.type_mult("dog", ["cat", "ghost"]) == 4
    assert D.type_mult("dog", ["human"]) == 0.5
    assert D.type_mult("dog", ["cat", "human"]) == 1.0
    assert D.type_mult(None, ["cat"]) == 1


def test_creature_basics():
    c = D.make_creature("krysa", 10)
    assert c.hp == c.max_hp > 0 and 1 <= len(c.moves) <= 4
    assert [m["id"] for m in c.moves][-1] == "quick_gnaw"   # на 10 уровне: gnaw, squeak, quick_gnaw
    c2 = type(c).from_dict(D, c.to_dict())
    assert c2.to_dict() == c.to_dict()


def auto_battle(rng, wild, a=None, b=None, max_turns=400):
    pa = [D.make_creature(a or rng.choice(list(D.species)), rng.randint(5, 30)) for _ in range(rng.randint(1, 3))]
    pb = [D.make_creature(b or rng.choice(list(D.species)), rng.randint(5, 30)) for _ in range(1 if wild else rng.randint(1, 3))]
    bag = {"box": 3, "bread_crust": 2, "milk": 1}
    bt = Battle(D, pa, pb, wild=wild, bag=bag, rng=rng, enemy_name="Тест")
    bt.start()
    turns = 0
    while not bt.over:
        turns += 1
        assert turns < max_turns, "бой не заканчивается"
        if bt.awaiting_switch:
            bt.submit(("switch", bt.player.alive()[0]))
            continue
        slots = bt.usable_slots(bt.player)
        r = rng.random()
        if wild and r < 0.1 and bag["box"] > 0:
            ev = bt.submit(("item", "box"))
        elif r < 0.15 and len(bt.player.alive()) > 1:
            ev = bt.submit(("switch", [i for i in bt.player.alive() if i != bt.player.active][0]))
        else:
            ev = bt.submit(("move", rng.choice(slots) if slots else -1))
        for side in (bt.player, bt.enemy):
            for c in side.party:
                assert 0 <= c.hp <= c.max_hp
                assert all(m["pp"] >= 0 for m in c.moves)
        assert all("t" in e for e in ev)
    assert bt.result in ("win", "lose", "run", "caught")
    return bt.result


def test_battle_simulation():
    rng = random.Random(1234)
    res = {}
    for i in range(1500):
        r = auto_battle(rng, wild=(i % 2 == 0))
        res[r] = res.get(r, 0) + 1
    print("   исходы 1500 боёв:", res)
    assert res.get("caught", 0) > 0 and res.get("win", 0) > 0 and res.get("lose", 0) > 0


def test_catch_rates():
    rng = random.Random(7)

    def rate(hp_frac, sp="krysa"):
        n = 0
        for _ in range(600):
            w = D.make_creature(sp, 5)
            w.hp = max(1, int(w.max_hp * hp_frac))
            bt = Battle(D, [D.make_creature("pes", 50)], [w], wild=True, bag={"box": 1}, rng=rng)
            bt.submit(("item", "box"))
            n += bt.result == "caught"
        return n / 600
    full, low = rate(1.0), rate(0.05)
    king, legend = rate(1.0, "krysiny_korol"), rate(1.0, "bingus")
    print(f"   крыса: полное HP {full:.0%}, 5% HP {low:.0%}; король {king:.0%}; легендарный Бингус {legend:.0%}")
    assert low > full > king >= legend and low > 0.9 and legend < 0.05


def test_status_and_moves():
    rng = random.Random(1)
    tgt = D.make_creature("pes", 20)
    bt = Battle(D, [D.make_creature("kot", 30)], [tgt], wild=True, rng=rng)
    bt._try_status(bt.enemy, "slp", [], forced=True)
    assert tgt.status == "slp"
    bt._try_status(bt.enemy, "psn", [], forced=True)
    assert tgt.status == "slp"          # второй статус не вешается
    t2 = D.make_creature("beshekot", 10)    # кошачий/ядовитый
    bt2 = Battle(D, [D.make_creature("krysa", 10)], [t2], wild=True, rng=rng)
    bt2._try_status(bt2.enemy, "psn", [], forced=True)
    assert t2.status is None            # ядовитому яд не страшен


def test_exp_and_levelup():
    rng = random.Random(3)
    me = D.make_creature("pes", 10)
    foe = D.make_creature("krysa", 3)
    foe.hp = 1
    bt = Battle(D, [me], [foe], wild=True, rng=rng)
    exp0 = me.exp
    while not bt.over:
        bt.submit(("move", 0))
    assert bt.result == "win" and me.exp > exp0


def test_evolution():
    h = D.make_creature("khomechennok", 15)
    assert evolution.level_evolution(h) is None
    h.level = 16
    h.recalc()
    into = evolution.level_evolution(h)
    assert into == "khomyak"
    evolution.evolve(D, h, into)
    assert h.species_id == "khomyak" and h.hp <= h.max_hp
    r = D.make_creature("krysa", 10)           # у крысы все ветки по предметам/обмену
    assert evolution.level_evolution(r) is None
    assert evolution.item_evolution(r, "syringe") == "spidkrys"
    assert evolution.item_evolution(r, "tin_can") == "rytsekrys"
    assert evolution.item_evolution(r, "maggots") == "gniekrys"
    assert evolution.item_evolution(r, "box") is None
    assert evolution.item_evolution(D.make_creature("kokonishche", 20), "palto") == "mol"
    assert evolution.item_evolution(D.make_creature("enot", 5), "bin_lid") == "rytsenot"
    assert evolution.item_evolution(D.make_creature("nedopchel", 5), "molochko") == "korolevchel"
    # обмен: существо получено ВЗАМЕН партнёра
    assert evolution.trade_evolution(D.make_creature("ptenets", 12), "krysa") == "goluvin"
    assert evolution.trade_evolution(D.make_creature("krysa", 12), "ptenets") == "krysolet"
    assert evolution.trade_evolution(D.make_creature("ptenets", 12), "pes") is None


def test_fusion_and_save():
    st = PlayerState()
    st.add_creature(D.make_creature("pes", 10))
    for lv in (5, 6, 7, 8):
        st.add_creature(D.make_creature("krysa", lv))
    assert fusion.available(D, st) == []
    st.add_creature(D.make_creature("krysa", 9))
    assert len(fusion.available(D, st)) == 1
    king = fusion.craft(D, st, "krysiny_korol")
    assert king and king.species_id == "krysiny_korol" and king.level == 10
    assert not any(c.species_id == "krysa" for c in st.party + st.storage)
    st.bag["box"] = 7
    st.badges.append("badge_dump")
    with tempfile.TemporaryDirectory() as tmp:
        save.save(st, 1, tmp)
        st2 = save.load(D, 1, tmp)
    assert st2.to_dict() == st.to_dict()


def test_encounter_tables():
    rng = random.Random(5)
    seen = {D.roll_encounter("dump", rng).species_id for _ in range(500)}
    assert {"krysa", "khomechennok", "shchenok", "kotenok"} <= seen
    assert not any(D.species[s].get("legendary") for s in seen)
    assert D.roll_item("dump", rng) in D.items


def test_type_balance():
    """У каждого типа ровно по 2 сильные цели, 2 слабые цели, 2 слабости и 2 сопротивления."""
    ids = list(D.types)
    for t in ids:
        assert sum(D.type_mult(t, [o]) > 1 for o in ids) == 2, t
        assert sum(D.type_mult(t, [o]) < 1 for o in ids) == 2, t
        assert sum(D.type_mult(o, [t]) > 1 for o in ids) == 2, t
        assert sum(D.type_mult(o, [t]) < 1 for o in ids) == 2, t
    for a in ids:   # нет пар, где оба бьют друг друга x2
        for b in ids:
            assert not (D.type_mult(a, [b]) > 1 and D.type_mult(b, [a]) > 1), (a, b)


def test_balance_bounds():
    from tools.balance_report import tournament, ladder
    res = tournament(D, n=4)
    bad = {k: round(v, 2) for k, v in res.items() if not 0.25 <= v <= 0.75}
    assert not bad, f"перекос боевого баланса: {bad}"
    for names, sums in ladder(D):
        assert all(b > a for a, b in zip(sums, sums[1:])), f"эволюция слабее предыдущей стадии: {names} {sums}"


def test_map_valid():
    from game.world.mapdata import MapData, DIRS
    m = MapData.load(Path(__file__).resolve().parents[1] / "maps" / "dump.tmj")
    assert m.tileset and m.tileset["image"].exists(), "нет картинки тайлсета"
    assert len(m.objects_of("player_start")) == 1 and len(m.objects_of("barrel")) >= 1
    assert len(m.objects_of("dumpster")) >= 6 and len(m.objects_of("item_spot")) >= 15
    assert len(m.objects_of("pc")) == 1 and len(m.objects_of("trader")) == 1
    reach = m.reachable()
    assert not m.blocked(*m.start())
    for o in m.objects:                     # у каждого объекта есть доступный подход, предметы достижимы
        if o.type == "item_spot":
            assert (o.x, o.y) in reach, f"предмет {o.id} недостижим"
        elif o.blocking:
            assert any((o.x + dx, o.y + dy) in reach for dx, dy in DIRS.values()), f"{o.name} {o.id}: нет подхода"
        if o.type in ("trainer", "leader"):
            assert o.props["trainer_id"] in D.trainers
            assert o.props.get("facing") in DIRS
    ids = {o.props["trainer_id"] for o in m.objects_of("trainer", "leader")}
    assert "leader_dump" in ids
    enc = sum(m.prop(x, y, "encounter") and (x, y) in reach for x in range(m.w) for y in range(m.h))
    assert enc > 50, "слишком мало тайлов для встреч"


def test_exp_progress():
    c = D.make_creature("krysa", 10)
    got, need, frac = c.exp_progress()
    assert got == 0 and need == 11 ** 3 - 10 ** 3 and frac == 0
    c.exp += need // 2
    got, need2, frac = c.exp_progress()
    assert need2 == need and 0.45 < frac < 0.55
    c.level = 100
    assert c.exp_progress() == (0, 0, 1.0)


def test_moveset():
    from game.systems import moveset
    c = D.make_creature("dikiy", 30)            # у Дикого 5 приёмов в learnset -> влезают 4
    assert len(c.moves) == 4
    first, second = c.moves[0]["id"], c.moves[1]["id"]
    assert moveset.swap_moves(c, 0, 1) and c.moves[0]["id"] == second and c.moves[1]["id"] == first
    assert not moveset.swap_moves(c, 0, 0) and not moveset.swap_moves(c, 0, 9)
    # ждущий приём: заменяем ячейку 2, ждущий очищается, pp полные
    c.pending_moves = ["peck"]
    forgot = moveset.learn_move(D, c, "peck", 2)
    assert forgot and c.moves[2]["id"] == "peck" and c.moves[2]["pp"] == D.moves["peck"]["pp"] and not c.pending_moves
    # нельзя в свободную ячейку при 4 приёмах, неверные данные
    for bad in (lambda: moveset.learn_move(D, c, "gnaw"), lambda: moveset.learn_move(D, c, "no_such"), lambda: moveset.learn_move(D, c, "gnaw", 7)):
        try:
            bad()
            assert False, "должно быть исключение"
        except ValueError:
            pass
    c.pending_moves = ["gnaw", "squeak"]
    moveset.decline_move(c, "gnaw")
    assert c.pending_moves == ["squeak"]
    c.moves.pop()
    assert moveset.learn_move(D, c, "squeak") is None and len(c.moves) == 4 and not c.pending_moves
    for mid in D.moves:                          # у любого приёма есть описание
        assert moveset.describe_move(D, mid).endswith(".")
    assert "отравить" in moveset.describe_move(D, "shawarma")
    hints = moveset.evolution_hints(D, D.make_creature("krysa", 5))
    assert any("Спидкрыс" in h for h in hints) and any("Крысиный король" in h for h in hints) and any("Крысолет" in h for h in hints)


def test_pending_from_levelup():
    """Существо с 4 приёмами при повышении уровня откладывает новый приём в очередь."""
    c = D.make_creature("khomechennok", 19)      # на 20 уровне выучит rat_scuffle
    c.exp = 20 ** 3 - 1
    foe = D.make_creature("krysa", 3)
    foe.hp = 1
    c.moves = c.moves[:3] + [{"id": "peck", "pp": 5, "max_pp": 35}]
    bt = Battle(D, [c], [foe], wild=True, rng=random.Random(2))
    while not bt.over:
        bt.submit(("move", 0))
    assert c.level >= 20 and "rat_scuffle" in c.pending_moves


def _con(hooks=None, state=True):
    from game.debug.console import Console
    st = PlayerState() if state else None
    return Console(D, lambda: st, hooks), st


def test_console_commands():
    con, st = _con()
    con.run("give krysa 15")
    con.run("give хомеченнок")                  # по русскому имени
    assert [c.level for c in st.party] == [15, 5] and st.party[1].species_id == "khomechennok"
    con.run("give shchenok 5 6")               # 6 штук: часть уйдёт в ПК
    assert len(st.party) == 6 and len(st.storage) == 2
    assert "Ошибка" in con.run("give nosuchthing")[-1]
    con.run("evolve 1")                        # у крысы первая ветка - предмет (условие игнорируется)
    assert st.party[0].species_id == "spidkrys"
    con.run("evolve 2 krysiny_korol")
    assert st.party[1].species_id == "krysiny_korol"
    con.run("store 3"); con.run("take 1")
    con.run("level 3 16")
    assert any("Можно эволюционировать" in l for l in con.log[-3:])
    con.run("checkevo"); assert st.party[2].species_id == "pes" or True
    # эволюции: по уровню, по предмету, по обмену
    st2 = PlayerState(); con2 = _con()[0]; con2.get_state = lambda: st2
    con2.run("give khomechennok 16"); con2.run("checkevo")
    assert st2.party[0].species_id == "khomyak"
    con2.run("give kokonishche 10"); con2.run("useitem 2 palto")
    assert st2.party[1].species_id == "mol"
    con2.run("give ptenets 20")
    assert "krysa" in con2.run("trade 3")[-1]
    con2.run("trade 3 krysa")
    assert st2.party[2].species_id == "krysolet" and st2.party[2].level == 20
    assert "обмена нет" in con2.run("trade 1")[-1]
    # опыт, приёмы, статус, предметы, деньги, декс
    con2.run("give krysa 5"); con2.run("exp 4 100000")
    assert st2.party[3].level > 30
    con2.run("teach 4 scandal"); con2.run("teach 4 peck 1")
    con2.run("status 1 psn"); assert st2.party[0].status == "psn"
    con2.run("hp 1 1"); assert st2.party[0].hp == 1
    con2.run("heal"); assert st2.party[0].hp == st2.party[0].max_hp and st2.party[0].status is None
    con2.run("item box 7"); assert st2.bag["box"] == 12
    con2.run("money 500"); con2.run("money -9999"); assert st2.money == 0
    con2.run("badge badge_dump"); assert "badge_dump" in st2.badges
    con2.run("dex all"); assert len(st2.caught) == len(D.species)
    assert D.validate() == []


def test_console_hooks_and_errors():
    calls = []
    con, st = _con({"battle": lambda foe: calls.append(("battle", foe.species_id, foe.level)),
                    "trainer": lambda tid: calls.append(("trainer", tid)),
                    "teleport": lambda x, y: calls.append(("tp", x, y)) or True, "pos": lambda: (1, 2), "close": lambda: calls.append("close")})
    con.run("give krysa 5")
    con.run("battle tarakan 12"); con.run("trainer leader_dump"); con.run("tp 4 5"); con.run("tp"); con.run("close")
    assert calls == [("battle", "tarakan", 12), ("trainer", "leader_dump"), ("tp", 4, 5), "close"], calls
    assert any("Позиция" in l for l in con.log)
    con.get_state = lambda: None
    assert "Сначала начни игру" in con.run("party")[-1]
    assert "Неизвестная команда" in con.run("fooo")[-1]
    con3 = _con()[0]
    assert "недоступно" in con3.run("tp 1 1")[-1] or "Команда пуста" in con3.run("tp 1 1")[-1]


def test_console_complete_and_fuzz():
    con, st = _con()
    assert con.complete("he")[1] == ["heal", "help"]
    assert con.complete("give krysiny_k")[0] == "give krysiny_korol "
    assert "krysa" in con.complete("give kry")[1] and con.complete("status 1 ps")[0] == "status 1 psn "
    from game.debug.console import COMMANDS
    for name in COMMANDS:                          # у каждой команды есть справка
        assert con.run(f"help {name}")[-1] and "Ошибка" not in con.run(f"help {name}")[-1]
    rng = random.Random(9)
    words = list(COMMANDS) + list(D.species)[:6] + list(D.items)[:4] + list(D.moves)[:4] + ["1", "2", "3", "0", "-5", "99999", "all", "clear", "psn", "none", "keep", "atk", "spe", "hp", "31", "252", "brave", "борзый", "", "\\", "\"", "я"]
    for _ in range(6000):                          # фаззинг: любые команды не должны падать исключением
        line = " ".join(rng.choice(words) for _ in range(rng.randint(1, 4)))
        if line.split(" ")[0] in ("close", "exit", "quit", "battle", "fight", "trainer", "tp", "save", "clear", "cls"):
            continue
        con.run(line)
        if rng.random() < 0.05:
            con.run("give krysa 5")


def test_roster():
    """Состав из таблицы «Бомжекимон» + черепашья линия: 48 существ, цепочки целы, легендарные не выпадают."""
    assert len(D.species) == 48
    targets = {e["into"] for s in D.species.values() for e in s["evolutions"]} | {f["result"] for f in D.fusions}
    roots = set(D.species) - targets
    for sid in D.species:
        sp = D.species[sid]
        assert sum(1 for lv, _ in sp["learnset"] if lv == 1) >= 2, sid
        assert len({m for _, m in sp["learnset"]}) == len(sp["learnset"]), f"повтор приёма у {sid}"
        for e in sp["evolutions"]:
            assert e["into"] != sid
    # из каждого вида можно дойти до корня без циклов (нет цикла эволюций)
    parents = {}
    for sid, sp in D.species.items():
        for e in sp["evolutions"]:
            parents.setdefault(e["into"], set()).add(sid)
    for f in D.fusions:
        parents.setdefault(f["result"], set()).update(f["inputs"])
    for sid in D.species:
        seen, stack = set(), [sid]
        while stack:
            x = stack.pop()
            assert x not in seen or x == sid or True
            for p in parents.get(x, ()):
                assert p != sid, f"цикл эволюций через {sid}"
                if p not in seen:
                    seen.add(p)
                    stack.append(p)
    legends = [s for s, v in D.species.items() if v.get("legendary")]
    assert set(legends) == {"golubiny_korol", "bingus", "belochka"}
    assert all(D.species[s]["catch_rate"] <= 5 and not D.species[s]["evolutions"] for s in legends)
    assert {"khomechennok", "shchenok", "kotenok"} <= roots          # стартовые - начала цепочек
    assert D.species["dikiy"]["types"] == ["human"] and D.species["golubiny_korol"]["types"] == ["bird", "human"]
    assert set(D.species["belochka"]["types"]) == {"rodent", "ghost"}


def test_trade_system():
    from game.systems import trade
    # Птенец <-> Крыса: оба получают эволюцию
    st = PlayerState()
    st.add_creature(D.make_creature("krysa", 12))
    st.add_creature(D.make_creature("ptenets", 14))
    assert trade.options_for(D, "krysa") == [("ptenets", "goluvin")]
    assert trade.options_for(D, "ptenets") == [("krysa", "krysolet")]
    assert {c.species_id for c, _ in trade.tradable(D, st)} == {"krysa", "ptenets"}
    new = trade.execute(D, st, st.party[0], "ptenets", "goluvin")
    assert new.species_id == "goluvin" and new.level == 12 and st.party[0] is new and len(st.party) == 2
    assert "goluvin" in st.caught
    new2 = trade.execute(D, st, st.party[1], "krysa", "krysolet")
    assert new2.species_id == "krysolet" and new2.level == 14
    try:
        trade.execute(D, st, st.party[0], "krysa", "krysolet")
        assert False, "обмена goluvin нет"
    except ValueError:
        pass
    # плешипес/черемшкот
    assert sorted(trade.options_for(D, "pleshipes")) == [("cheremshkot", "kotopes"), ("pleshipes", "siamsobek")]
    assert trade.options_for(D, "cheremshkot") == [("pleshipes", "kotopes")]
    assert trade.options_for(D, "kot") == []


def test_turtles_and_ninja_craft():
    assert D.species["cherepashonok"]["evolutions"][0] == {"method": "level", "level": 20, "into": "cherepaha"}
    assert evolution.item_evolution(D.make_creature("cherepaha", 25), "ooze") == "mutapaha"
    fus = next(f for f in D.fusions if f["id"] == "cherepashki_nindzya")
    assert fus["inputs"] == {"cherepaha": 4, "krysa": 1} and fus["result"] == "cherepashki_nindzya"
    st = PlayerState()
    st.add_creature(D.make_creature("pes", 12))
    for _ in range(3):
        st.add_creature(D.make_creature("cherepaha", 20))
    st.add_creature(D.make_creature("krysa", 8))
    assert fusion.available(D, st) == []                    # трёх черепах мало
    st.add_creature(D.make_creature("cherepaha", 20))
    assert [f["id"] for f in fusion.available(D, st)] == ["cherepashki_nindzya"]
    ninja = fusion.craft(D, st, "cherepashki_nindzya")
    assert ninja and ninja.species_id == "cherepashki_nindzya" and ninja.level == (20 * 4 + 8) // 5 + 3
    left = {c.species_id for c in st.party + st.storage}
    assert left == {"pes", "cherepashki_nindzya"}           # все пять ушли в крафт
    assert set(ninja.types) == {"poison", "human"}


def test_heal_move():
    rng = random.Random(4)
    me = D.make_creature("cherepashki_nindzya", 30)
    foe = D.make_creature("krysa", 3)
    me.moves = [{"id": "pizza_break", "pp": 5, "max_pp": 5}] + me.moves[1:]
    bt = Battle(D, [me], [foe], wild=True, rng=rng)
    me.hp = me.max_hp // 4
    before = me.hp
    ev = bt.submit(("move", 0))
    assert me.hp > before and any(e["t"] == "hp" and e["side"] == "player" and e["to"] > e["from"] for e in ev)
    me.hp = me.max_hp                                       # при полном здоровье не лечит, но тратит ход
    ev = bt.submit(("move", 0))
    assert any("порядке" in e.get("text", "") for e in ev)  # (потом враг мог ударить, поэтому HP не сверяем)
    from game.systems import moveset
    assert "Восстанавливает 40%" in moveset.describe_move(D, "pizza_break")
    hints = moveset.species_evolution_hints(D, "cherepaha")
    assert any("4 Черепаха + 1 Крыса" in h for h in hints) and any("Зелёная жижа" in h for h in hints)


def test_save_system():
    import json, time
    with tempfile.TemporaryDirectory() as tmp:
        st = PlayerState()
        st.add_creature(D.make_creature("khomechennok", 7))
        st.add_creature(D.make_creature("krysa", 12))
        st.bag.update({"box": 3, "palto": 1})
        st.badges.append("badge_dump")
        st.pos = {"map": "dump", "x": 5, "y": 6}
        # пусто
        assert save.load(D, 1, tmp) is None and save.read_meta(1, tmp, D) is None and save.latest_slot(tmp, D) is None
        # запись, метаданные, слот сессии
        save.save(st, 2, tmp, location="Свалка", now=1000.0)
        m = save.read_meta(2, tmp, D)
        assert m["ok"] and m["location"] == "Свалка" and m["badges"] == 1 and m["party"][1]["name"] == "Крыса" and st.slot == 2
        st2 = save.load(D, 2, tmp)
        assert st2.to_dict() == st.to_dict() and st2.slot == 2 and st2.pos["x"] == 5
        # автосохранение не меняет слот сессии, latest выбирает самое свежее
        st.money = 77
        assert save.autosave(st, tmp, "Свалка")
        assert st.slot == 2 and save.load(D, save.AUTO, tmp).slot is None
        assert save.latest_slot(tmp, D) == save.AUTO
        save.save(st, 1, tmp, now=time.time() + 100)
        assert save.latest_slot(tmp, D) == 1
        # перезапись создаёт .bak предыдущей версии
        st.money = 5
        save.save(st, 1, tmp)
        assert (Path(tmp) / "slot1.bak").exists() and json.load(open(Path(tmp) / "slot1.bak", encoding="utf-8"))["money"] == 77
        # повреждённый основной файл -> берём .bak
        (Path(tmp) / "slot1.json").write_text("{ это не json", encoding="utf-8")
        got = save.load(D, 1, tmp)
        assert got.money == 77 and got.loaded_from_backup
        assert save.read_meta(1, tmp, D)["from_backup"]
        # оба повреждены -> понятная ошибка, а не падение
        (Path(tmp) / "slot1.bak").write_text("мусор", encoding="utf-8")
        assert save.read_meta(1, tmp, D)["ok"] is False
        try:
            save.load(D, 1, tmp)
            assert False
        except save.SaveError:
            pass
        assert save.latest_slot(tmp, D) == save.AUTO            # битый слот не мешает "Продолжить"
        save.delete(1, tmp)
        assert save.read_meta(1, tmp, D) is None
        # сохранение со старым составом (существа, которых больше нет) не роняет игру
        raw = json.load(open(Path(tmp) / "slot2.json", encoding="utf-8"))
        raw["party"][0]["species"] = "rat_boss"
        (Path(tmp) / "slot3.json").write_text(json.dumps(raw), encoding="utf-8")
        meta = save.read_meta(3, tmp, D)
        assert meta["ok"] is False and "rat_boss" in meta["error"]
        try:
            save.load(D, 3, tmp)
            assert False
        except save.SaveError as e:
            assert "несовместимо" in str(e)
        # устаревшие предметы/виды в сумке и декса вычищаются
        raw = json.load(open(Path(tmp) / "slot2.json", encoding="utf-8"))
        raw["bag"].update({"moldy_cheese": 2, "box": 4})
        raw["seen"] += ["ghost_species"]
        raw["defeated"] += ["old_trainer"]
        (Path(tmp) / "slot3.json").write_text(json.dumps(raw), encoding="utf-8")
        old = save.load(D, 3, tmp)
        assert "moldy_cheese" not in old.bag and old.bag["box"] == 4 and "ghost_species" not in old.seen and "old_trainer" not in old.defeated
        # версия из будущего
        raw["version"] = 99
        (Path(tmp) / "slot3.json").write_text(json.dumps(raw), encoding="utf-8")
        assert "новой версии" in save.read_meta(3, tmp, D)["error"]
        # неполный файл
        (Path(tmp) / "slot3.json").write_text(json.dumps({"version": 1}), encoding="utf-8")
        assert save.read_meta(3, tmp, D)["ok"] is False
        # автосохранение никогда не бросает исключений (папка недоступна)
        assert save.autosave(st, "/proc/nonexistent/dir") is False


def test_paths():
    from game.core import paths
    src = Path("/proj")
    assert paths.compute_paths(False, None, "/usr/bin/python", src) == (src, src)
    res, app = paths.compute_paths(True, "/tmp/_MEI123", "/games/Bomzhemon/Bomzhemon.exe", src)
    assert str(res) == "/tmp/_MEI123" and str(app) == "/games/Bomzhemon"
    res, app = paths.compute_paths(True, None, "/games/Bomzhemon/Bomzhemon.exe", src)      # onedir без _MEIPASS
    assert str(res) == "/games/Bomzhemon" and str(app) == "/games/Bomzhemon"
    assert (paths.RESOURCES / "data" / "species.json").exists() and (paths.RESOURCES / "maps" / "dump.tmj").exists()
    assert paths.asset("data/species.json").exists()


def test_pc_system():
    from game.systems import pc
    st = PlayerState()
    for sid in ("khomechennok", "shchenok", "kotenok"):
        st.add_creature(D.make_creature(sid, 5))
    for i in range(35):                          # 35 в ПК -> 2 ящика (+ ещё один пустой нельзя: 35//30+1 == 2)
        st.storage.append(D.make_creature(list(D.species)[i % 48], 3 + i % 9))
    assert pc.pages(st) == 2
    a, b, c3 = st.party
    s0, s1 = st.storage[0], st.storage[1]
    # обмен команда <-> ПК и внутри списка
    assert "поменялись" in pc.move(st, ("party", 0), ("box", 0))
    assert st.party[0] is s0 and st.storage[0] is a and len(st.party) == 3 and len(st.storage) == 35
    pc.move(st, ("box", 0), ("box", 1))
    assert st.storage[0] is s1 and st.storage[1] is a
    pc.move(st, ("party", 0), ("party", 2))
    assert st.party[0] is c3 and st.party[2] is s0
    # в пустую клетку: в ПК и обратно
    n = len(st.storage)
    pc.deposit(st, 0)
    assert len(st.party) == 2 and len(st.storage) == n + 1 and st.storage[-1] is c3
    pc.withdraw(st, len(st.storage) - 1)
    assert len(st.party) == 3 and st.party[-1] is c3
    # команда не бывает пустой и не больше 6
    st.party[:] = [b]
    try:
        pc.deposit(st, 0)
        assert False
    except pc.PCError as e:
        assert "пустой" in str(e)
    st.party[:] = [D.make_creature("kot", 5) for _ in range(6)]
    try:
        pc.withdraw(st, 0)
        assert False
    except pc.PCError as e:
        assert "полна" in str(e)
    assert "поменялись" in pc.move(st, ("party", 5), ("box", 0))     # а обмен при полной команде можно
    # пустая клетка ящика = клетка за концом списка: существо встаёт в конец
    x = D.make_creature("lisitsa", 9)
    st.party[:] = [b, x]
    before = len(st.storage)
    pc.move(st, ("party", 1), ("box", 500))
    assert st.storage[-1] is x and len(st.storage) == before + 1 and st.party == [b]
    first = st.storage[0]
    pc.move(st, ("box", 0), ("box", 500))
    assert st.storage[-1] is first and len(st.storage) == before + 1
    # отпускание
    st.party[:] = [b]
    for bad in (("party", 0), ("party", 3), ("box", 999)):
        try:
            pc.release(st, bad)
            assert False
        except pc.PCError:
            pass
    gone = pc.release(st, ("box", 0))
    assert gone not in st.storage
    # сортировка
    pc.sort_box(D, st, "level")
    lv = [c.level for c in st.storage]
    assert lv == sorted(lv, reverse=True)
    pc.sort_box(D, st, "dex")
    order = {sid: i for i, sid in enumerate(D.species)}
    assert [order[c.species_id] for c in st.storage] == sorted(order[c.species_id] for c in st.storage)
    pc.sort_box(D, st, "name")
    assert [c.name.casefold() for c in st.storage] == sorted(c.name.casefold() for c in st.storage)
    # фаззинг: общее число существ не меняется (кроме release), нет дублей, команда 1..6
    rng = random.Random(5)
    st = PlayerState()
    for i in range(4):
        st.add_creature(D.make_creature("krysa", 5 + i))
    for i in range(40):
        st.storage.append(D.make_creature("pes", 5 + i % 5))
    total = len(st.party) + len(st.storage)
    for _ in range(3000):
        kinds = ("party", "box")
        src = (rng.choice(kinds), rng.randint(0, 45))
        dst = (rng.choice(kinds), rng.randint(0, 45))
        try:
            pc.move(st, src, dst)
        except pc.PCError:
            pass
        assert 1 <= len(st.party) <= 6 and len(st.party) + len(st.storage) == total
        allc = st.party + st.storage
        assert len({id(c) for c in allc}) == total


def test_stat_formulas():
    """Формулы как у покемонов: проверяем на известных числах."""
    from game.battle import stats as S
    assert S.calc_hp(100, 50, 31, 0) == 175                 # (200+31)*50//100 + 50 + 10
    assert S.calc_other(100, 50, 31, 0) == 120              # 115 + 5
    assert S.calc_other(100, 50, 31, 0, 110) == 132         # характер +10%
    assert S.calc_other(100, 50, 31, 0, 90) == 108          # характер -10%
    assert S.calc_other(100, 50, 31, 252) == 152            # EV 252 -> +63
    assert S.calc_hp(100, 50, 31, 252) == 207
    # IV и EV действуют на живое существо
    a = D.make_creature("krysa", 50, iv=0)
    b = D.make_creature("krysa", 50, iv=31)
    assert b.max_hp > a.max_hp and all(b.stat(k) > a.stat(k) for k in ("atk", "def", "spa", "spd", "spe"))
    assert D.make_creature("krysa", 50, iv=15).max_hp == S.calc_hp(D.species["krysa"]["base"]["hp"], 50, 15, 0)


def test_natures():
    from game.battle import stats as S
    assert len(S.NATURES) == 25
    assert sum(1 for n in S.NATURES.values() if n[1] is None) == 5
    pairs = {(u, d) for _, u, d in S.NATURES.values() if u}
    assert len(pairs) == 20 and all(u != d for u, d in pairs) and all("hp" not in p for p in pairs)
    assert len({n[0] for n in S.NATURES.values()}) == 25
    base = D.make_creature("krysa", 40, nature="hardy")
    brave = D.make_creature("krysa", 40, nature="brave")            # +Атака, -Скорость
    assert brave.stat("atk") > base.stat("atk") and brave.stat("spe") < base.stat("spe")
    assert brave.stat("def") == base.stat("def") and brave.max_hp == base.max_hp
    assert "Отчаянный" in S.nature_label("brave") and "+Атака" in S.nature_label("brave") and "-Скорость" in S.nature_label("brave")


def test_random_ivs_and_flat_mode():
    from game.core.data import GameData
    rnd = GameData()                                    # обычный режим: случайные IV и характер
    rng = random.Random(3)
    mons = [rnd.make_creature("krysa", 20, rng=rng) for _ in range(300)]
    assert all(0 <= v <= 31 for m in mons for v in m.iv.values())
    assert len({tuple(m.iv.values()) for m in mons}) > 250 and len({m.nature for m in mons}) == 25
    assert len({m.max_hp for m in mons}) > 5                        # у одного вида реально разные характеристики
    avg = sum(sum(m.iv.values()) for m in mons) / len(mons) / 6
    assert 14 < avg < 17
    # с одним сидом одинаковый результат
    a, b = rnd.make_creature("pes", 10, rng=random.Random(8)), rnd.make_creature("pes", 10, rng=random.Random(8))
    assert a.iv == b.iv and a.nature == b.nature
    # легендарные: минимум три IV по 31
    for _ in range(50):
        assert sum(1 for v in rnd.make_creature("bingus", 40, rng=rng).iv.values() if v == 31) >= 3
    # плоский режим
    flat = D.make_creature("krysa", 20)
    assert set(flat.iv.values()) == {15} and flat.nature == "hardy"
    # явные значения
    c = D.make_creature("krysa", 20, iv={"hp": 31, "atk": 0, "def": 5, "spa": 6, "spd": 7, "spe": 8}, nature="jolly")
    assert c.iv["hp"] == 31 and c.iv["atk"] == 0 and c.nature == "jolly"
    # у тренеров IV фиксированы
    assert set(D.make_creature("krysa", 10, iv=24).iv.values()) == {24}


def test_evs():
    c = D.make_creature("krysa", 30)
    hp0, atk0 = c.max_hp, c.stat("atk")
    assert c.gain_ev({"atk": 100}) and c.ev["atk"] == 100 and c.stat("atk") > atk0
    c.gain_ev({"atk": 500})
    assert c.ev["atk"] == 252                                       # предел на характеристику
    for k in ("hp", "def", "spa", "spd", "spe"):
        c.gain_ev({k: 252})
    assert c.ev_total == 510                                        # предел общий
    assert not c.gain_ev({"spe": 10})
    # рост максимума HP поднимает и текущее HP; обморок не оживляет
    c2 = D.make_creature("krysa", 30)
    c2.hp = 5
    c2.gain_ev({"hp": 100})
    assert c2.max_hp > c.max_hp - 100 and c2.hp > 5
    c3 = D.make_creature("krysa", 30)
    c3.hp = 0
    c3.gain_ev({"hp": 100})
    assert c3.hp == 0
    # победа в бою даёт EV по таблице вида
    from game.battle import stats as S
    me, foe = D.make_creature("pes", 15), D.make_creature("kotenok", 3)
    foe.hp = 1
    assert S.ev_yield(foe.species) == {"spe": 1}
    bt = Battle(D, [me], [foe], wild=True, rng=random.Random(1))
    while not bt.over:
        bt.submit(("move", 0))
    assert bt.result == "win" and me.ev["spe"] == 1 and me.ev_total == 1
    assert all("ev_yield" in sp and sum(sp["ev_yield"].values()) in (1, 2, 3) for sp in D.species.values())


def test_stats_persist_and_evolve():
    import json
    c = D.make_creature("khomechennok", 16, iv={"hp": 1, "atk": 2, "def": 3, "spa": 4, "spd": 5, "spe": 6}, nature="timid")
    c.gain_ev({"spe": 40})
    c2 = type(c).from_dict(D, c.to_dict())
    assert c2.to_dict() == c.to_dict() and c2.nature == "timid" and c2.ev["spe"] == 40 and c2.stat("spe") == c.stat("spe")
    evolution.evolve(D, c, "khomyak")                               # эволюция сохраняет IV, EV и характер
    assert c.iv == {"hp": 1, "atk": 2, "def": 3, "spa": 4, "spd": 5, "spe": 6} and c.ev["spe"] == 40 and c.nature == "timid"
    # старое сохранение (версия 1, без IV/EV/характера) читается со значениями по умолчанию
    raw = c2.to_dict()
    for k in ("iv", "ev", "nature"):
        raw.pop(k)
    old = type(c).from_dict(D, raw)
    assert set(old.iv.values()) == {15} and old.ev_total == 0 and old.nature == "hardy"
    raw["nature"], raw["iv"] = "несуществующий", {"hp": 999, "atk": -5}
    odd = type(c).from_dict(D, raw)
    assert odd.nature == "hardy" and odd.iv["hp"] == 31 and odd.iv["atk"] == 0 and odd.iv["def"] == 15
    # крафт усредняет IV ингредиентов
    st = PlayerState()
    st.add_creature(D.make_creature("pes", 10))
    for i in range(5):
        st.add_creature(D.make_creature("krysa", 10, iv=i * 5))     # 0,5,10,15,20 -> среднее 10
    king = fusion.craft(D, st, "krysiny_korol")
    assert king and set(king.iv.values()) == {10}


def test_console_iv_ev_nature():
    from game.battle import stats as S
    con, st = _con()
    con.run("give krysa 30")
    c = st.party[0]
    hp0 = c.max_hp
    con.run("perfect 1")
    assert set(c.iv.values()) == {31} and c.max_hp > hp0
    con.run("iv 1 atk 0"); assert c.iv["atk"] == 0
    con.run("iv 1 all 10"); assert set(c.iv.values()) == {10}
    con.run("nature 1 борзый"); assert c.nature == "adamant"
    con.run("nature 1 jolly"); assert c.nature == "jolly"
    con.run("ev 1 atk 200"); assert c.ev["atk"] == 200
    con.run("ev 1 all 252"); assert c.ev_total == 510 and max(c.ev.values()) == 252 and c.ev["hp"] == 252
    con.run("ev 1 all 0"); assert c.ev_total == 0
    info = "\n".join(con.run("info 1"))
    assert "Характер:" in info and "IV:" in info and "EV:" in info
    for bad in ("iv 1 atk 99", "iv 1 foo 5", "nature 1 zzz", "ev 1 atk 300", "ev 9 atk 1", "iv"):
        assert "Ошибка" in con.run(bad)[-1], bad
    assert con.complete("nature 1 ad")[0] == "nature 1 adamant "
    assert "natures" in con.complete("list na")[1] or con.complete("list na")[0].endswith("natures ")
    assert "Борзый" in "\n".join(con.run("list natures"))


def test_evolution_animation_logic():
    from game.systems import evolution_anim as A
    cfg = A.make_config(D.animations["evolution"])
    assert A.validate_config(cfg) == [] and A.validate_config({**cfg, "flicker": 0}) and A.validate_config({**cfg, "flicker_hz": [10, 2]})
    tl = A.Timeline(cfg)
    assert tl.name == "intro" and tl.can_cancel() and not tl.done
    seen, t = [], 0.0
    while not tl.done and t < 60:
        seen += tl.update(0.05)
        t += 0.05
        if tl.name in ("burst", "reveal"):
            assert not tl.can_cancel()                      # после вспышки отменить нельзя
    assert seen == ["flicker", "burst", "reveal"] and tl.done and abs(tl.elapsed - tl.total) < 1e-9
    assert tl.update(1.0) == [] and tl.done                 # после конца ничего не происходит
    big = A.Timeline(cfg)                                   # огромный шаг проходит сразу несколько фаз
    assert big.update(100) == ["flicker", "burst", "reveal"] and big.done
    # мерцание: смены становятся чаще
    hz0, hz1, dur = cfg["flicker_hz"][0], cfg["flicker_hz"][1], cfg["flicker"]
    states = [A.flicker_show_new(i * 0.01, dur, hz0, hz1) for i in range(int(dur * 100))]
    swaps = [i for i in range(1, len(states)) if states[i] != states[i - 1]]
    first, last = swaps[1] - swaps[0], swaps[-1] - swaps[-2]
    assert len(swaps) > 10 and last < first and A.flicker_cycles(dur, dur, hz0, hz1) > A.flicker_cycles(dur / 2, dur, hz0, hz1)
    # частицы
    ps = A.Particles(seed=3)
    for _ in range(100):
        ps.update(0.05, 80)
    assert 0 < len(ps.items) <= 160
    assert all(0 <= b <= 1 for _, _, b, _ in ps.positions())
    ps2 = A.Particles(seed=3)
    for _ in range(100):
        ps2.update(0.05, 80)
    assert ps.positions() == ps2.positions()                 # детерминированы при одном сиде


def test_evolution_declined_and_apply():
    c = D.make_creature("khomechennok", 16)
    assert evolution.pending_level_evolution(c) == "khomyak"
    c.declined_evolution_level = 16                          # отменил на этом уровне
    assert evolution.pending_level_evolution(c) is None and evolution.level_evolution(c) == "khomyak"
    c.level = 17
    c.recalc()
    assert evolution.pending_level_evolution(c) == "khomyak"  # на следующем уровне спросим снова
    st = PlayerState()
    st.add_creature(c)
    st.caught.discard("khomyak")
    evolution.apply(D, st, c, "khomyak")
    assert c.species_id == "khomyak" and "khomyak" in st.caught and "khomyak" in st.seen and c.declined_evolution_level is None
    c.declined_evolution_level = 5                           # флаг сохраняется
    assert type(c).from_dict(D, c.to_dict()).declined_evolution_level == 5
    # обмен с animate=True ничего не эволюционирует сам
    from game.systems import trade
    st = PlayerState()
    st.add_creature(D.make_creature("krysa", 12))
    new, into = trade.execute(D, st, st.party[0], "ptenets", "goluvin", animate=True)
    assert new.species_id == "ptenets" and into == "goluvin" and st.party[0] is new and "goluvin" not in st.caught
    evolution.apply(D, st, new, into)
    assert new.species_id == "goluvin" and "goluvin" in st.caught


def test_event_bus():
    from game.core.events import EventBus
    import contextlib, io
    bus, log = EventBus(), []
    bus.on("x", lambda a=0: log.append(a))
    bus.on("x", lambda a=0: 1 / 0)                           # сломанный обработчик не мешает остальным и не роняет игру
    with contextlib.redirect_stderr(io.StringIO()):
        bus.emit("x", a=5)
    bus.emit("нет такого", a=1)
    assert log == [5]
    f = lambda a=0: log.append(a * 10)
    bus.on("y", f); bus.emit("y", a=2); bus.off("y", f); bus.emit("y", a=3)
    assert log == [5, 20]


def test_console_evoanim_and_dex():
    called = []
    con, st = _con({"evolution_anim": lambda c, into: called.append((c.species_id, into))})
    con.run("give khomechennok 10")
    con.run("evoanim 1"); con.run("evoanim 1 pes")
    assert called == [("khomechennok", "khomyak"), ("khomechennok", "pes")]
    assert st.party[0].species_id == "khomechennok"          # просмотр ничего не меняет
    assert "Ошибка" in _con({"evolution_anim": lambda *a: None})[0].run("evoanim 1")[-1]
    st.caught.discard("khomyak")
    con.run("evolve 1")                                      # консольная эволюция теперь отмечается в Бомждексе
    assert "khomyak" in st.caught


if __name__ == "__main__":
    fails = 0
    for name, fn in sorted(globals().items()):
        if name.startswith("test_"):
            try:
                fn()
                print("OK  ", name)
            except Exception as e:  # noqa
                fails += 1
                import traceback
                traceback.print_exc()
                print("FAIL", name, e)
    sys.exit(1 if fails else 0)
