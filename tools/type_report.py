"""Баланс типов: python -m tools.type_report"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from game.core.data import GameData

d = GameData()
ids = list(d.types)
name = lambda t: d.types[t]["name"]
print(f"{'тип':<11}{'бьёт x2':<44}{'слаб к':<44}{'стойкий к'}")
for t in ids:
    se = [name(o) for o in ids if d.type_mult(t, [o]) > 1]
    weak = [name(o) for o in ids if d.type_mult(o, [t]) > 1]
    res = [name(o) for o in ids if d.type_mult(o, [t]) < 1]
    print(f"{name(t):<11}{', '.join(se):<44}{', '.join(weak):<44}{', '.join(res)}")
