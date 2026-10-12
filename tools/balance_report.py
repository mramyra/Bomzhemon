"""Баланс-отчёт. python -m tools.balance_report [боёв_на_пару]
1) НОРМИРОВАННЫЙ турнир: все существа получают одинаковую сумму статов, ур. 30, свои типы и приёмы.
   Показывает перекосы типов/приёмов/распределения статов, а не "кто старше". Честно: 35..65%.
2) ЛЕСТНИЦА стадий: сумма базовых статов должна расти с эволюцией.
Правим data/species.json (статы, learnset), data/moves.json (сила/pp), data/types.json (таблица)."""
import copy
import random
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from game.battle.engine import Battle
from game.core.data import GameData

NORM_BST, LEVEL = 360, 30


def normalized(d):
    nd = copy.copy(d)
    nd.species = copy.deepcopy(d.species)
    for s in nd.species.values():
        tot = sum(s["base"].values())
        s["base"] = {k: max(10, round(v * NORM_BST / tot)) for k, v in s["base"].items()}
    return nd


def duel(d, a, b, rng):
    pa, pb = d.make_creature(a, LEVEL), d.make_creature(b, LEVEL)
    bt = Battle(d, [pa], [pb], wild=False, rng=rng)
    bt.start()
    for _ in range(300):
        if bt.over:
            break
        bt.submit(bt.ai_pick(bt.player, smart=True))
    return pa.hp > 0 and pb.hp <= 0, pb.hp > 0 and pa.hp <= 0


def tournament(d, n=40, seed=1):
    rng, nd, ids = random.Random(seed), normalized(d), list(d.species)
    out = {}
    for a in ids:
        w = t = 0
        for b in ids:
            if a != b:
                for _ in range(n):
                    win, lose = duel(nd, a, b, rng)
                    w += win
                    t += win or lose
        out[a] = w / max(1, t)
    return out


def ladder(d):
    """[(цепочка, суммы статов)] для каждой линии эволюции."""
    bst = lambda sid: sum(d.species[sid]["base"].values())
    nxt = {sid: [e["into"] for e in s["evolutions"]] for sid, s in d.species.items()}
    for f in d.fusions:
        for sp in f["inputs"]:
            nxt[sp] = nxt[sp] + [f["result"]]
    roots = set(d.species) - {t for v in nxt.values() for t in v}
    lines = []

    def walk(sid, chain):
        chain = chain + [sid]
        if not nxt[sid]:
            lines.append(chain)
        for n in nxt[sid]:
            walk(n, chain)
    for r in sorted(roots):
        walk(r, [])
    return [([d.species[s]["name"] for s in ch], [bst(s) for s in ch]) for ch in lines]


if __name__ == "__main__":
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 40
    d = GameData()
    print(f"== Нормированный турнир (сумма статов {NORM_BST}, ур. {LEVEL}) ==")
    for sid, wr in sorted(tournament(d, n).items(), key=lambda x: -x[1]):
        sp = d.species[sid]
        print(f"{sp['name']:<20}{'/'.join(sp['types']):<18}{wr:>4.0%}{'  <-- выбивается' if not 0.35 <= wr <= 0.65 else ''}")
    print("\n== Лестница стадий (сумма базовых статов) ==")
    for names, sums in ladder(d):
        print("  " + " -> ".join(f"{n} ({s})" for n, s in zip(names, sums)))
