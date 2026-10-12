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
    c = D.make_creature("rat", 10)
    assert c.hp == c.max_hp > 0 and 1 <= len(c.moves) <= 4
    assert [m["id"] for m in c.moves][-1] == "shawarma"   # последние 4 выученных к 10 уровню
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

    def rate(hp_frac, sp="rat"):
        n = 0
        for _ in range(600):
            w = D.make_creature(sp, 5)
            w.hp = max(1, int(w.max_hp * hp_frac))
            bt = Battle(D, [D.make_creature("stray_dog", 50)], [w], wild=True, bag={"box": 1}, rng=rng)
            bt.submit(("item", "box"))
            n += bt.result == "caught"
        return n / 600
    full, low = rate(1.0), rate(0.05)
    easy_boss = rate(1.0, "rat_king")
    print(f"   крыса: полное HP {full:.0%}, 5% HP {low:.0%}; крысиный король при полном HP {easy_boss:.0%}")
    assert low > full > easy_boss and low > 0.9


def test_status_and_moves():
    rng = random.Random(1)
    tgt = D.make_creature("stray_dog", 20)
    bt = Battle(D, [D.make_creature("black_cat", 30)], [tgt], wild=True, rng=rng)
    bt._try_status(bt.enemy, "slp", [], forced=True)
    assert tgt.status == "slp"
    bt._try_status(bt.enemy, "psn", [], forced=True)
    assert tgt.status == "slp"          # второй статус не вешается
    t2 = D.make_creature("toad", 10)
    bt2 = Battle(D, [D.make_creature("rat", 10)], [t2], wild=True, rng=rng)
    bt2._try_status(bt2.enemy, "psn", [], forced=True)
    assert t2.status is None            # ядовитому яд не страшен


def test_exp_and_levelup():
    rng = random.Random(3)
    me = D.make_creature("stray_dog", 10)
    foe = D.make_creature("rat", 3)
    foe.hp = 1
    bt = Battle(D, [me], [foe], wild=True, rng=rng)
    exp0 = me.exp
    while not bt.over:
        bt.submit(("move", 0))
    assert bt.result == "win" and me.exp > exp0


def test_evolution():
    rat = D.make_creature("rat", 15)
    assert evolution.level_evolution(rat) is None
    rat.level = 16
    rat.recalc()
    into = evolution.level_evolution(rat)
    assert into == "rat_boss"
    evolution.evolve(D, rat, into)
    assert rat.species_id == "rat_boss" and rat.hp <= rat.max_hp
    m = D.make_creature("mouse", 10)
    assert evolution.item_evolution(m, "moldy_cheese") == "mouse_mutant"
    assert evolution.item_evolution(m, "box") is None
    fp = D.make_creature("fat_pigeon", 20)
    assert evolution.item_evolution(fp, "pigeon_costume") == "pigeon_king"


def test_fusion_and_save():
    st = PlayerState()
    st.add_creature(D.make_creature("stray_dog", 10))
    for lv in (5, 6, 7, 8):
        st.add_creature(D.make_creature("rat", lv))
    assert fusion.available(D, st) == []
    st.add_creature(D.make_creature("rat", 9))
    assert len(fusion.available(D, st)) == 1
    king = fusion.craft(D, st, "rat_king")
    assert king and king.species_id == "rat_king" and king.level == 10
    assert not any(c.species_id == "rat" for c in st.party + st.storage)
    st.bag["box"] = 7
    st.badges.append("badge_dump")
    with tempfile.TemporaryDirectory() as tmp:
        save.save(st, 1, tmp)
        st2 = save.load(D, 1, tmp)
    assert st2.to_dict() == st.to_dict()


def test_encounter_tables():
    rng = random.Random(5)
    seen = {D.roll_encounter("dump", rng).species_id for _ in range(500)}
    assert {"rat", "mouse", "pigeon"} <= seen
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
    res = tournament(D, n=15)
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
    c = D.make_creature("rat", 10)
    got, need, frac = c.exp_progress()
    assert got == 0 and need == 11 ** 3 - 10 ** 3 and frac == 0
    c.exp += need // 2
    got, need2, frac = c.exp_progress()
    assert need2 == need and 0.45 < frac < 0.55
    c.level = 100
    assert c.exp_progress() == (0, 0, 1.0)


def test_moveset():
    from game.systems import moveset
    c = D.make_creature("tramp", 30)            # у бомжа 6 приёмов в learnset -> влезают 4
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
    hints = moveset.evolution_hints(D, D.make_creature("rat", 5))
    assert any("Крыса-босс" in h for h in hints) and any("Крысиный король" in h for h in hints)


def test_pending_from_levelup():
    """Существо с 4 приёмами при повышении уровня откладывает новый приём в очередь."""
    c = D.make_creature("rat", 13)               # на 14 уровне выучит rat_scuffle
    c.exp = 14 ** 3 - 1
    foe = D.make_creature("rat", 3)
    foe.hp = 1
    c.moves = c.moves[:3] + [{"id": "peck", "pp": 5, "max_pp": 35}]
    bt = Battle(D, [c], [foe], wild=True, rng=random.Random(2))
    while not bt.over:
        bt.submit(("move", 0))
    assert c.level >= 14 and "rat_scuffle" in c.pending_moves


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
