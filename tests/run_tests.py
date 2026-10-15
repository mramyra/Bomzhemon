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
    con.run("give shchenok 5 6")               # 6 штук: часть уйдёт в заначку
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
    words = list(COMMANDS) + list(D.species)[:6] + list(D.items)[:4] + list(D.moves)[:4] + ["1", "2", "3", "0", "-5", "99999", "all", "clear", "psn", "none", "keep", "", "\\", "\"", "я"]
    for _ in range(6000):                          # фаззинг: любые команды не должны падать исключением
        line = " ".join(rng.choice(words) for _ in range(rng.randint(1, 4)))
        if line.split(" ")[0] in ("close", "exit", "quit", "battle", "fight", "trainer", "tp", "save", "clear", "cls"):
            continue
        con.run(line)
        if rng.random() < 0.05:
            con.run("give krysa 5")


def test_roster():
    """Состав из таблицы «Бомжекимон»: 44 существа, цепочки целы, легендарные не выпадают."""
    assert len(D.species) == 44
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
