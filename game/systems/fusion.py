"""Крафт: N существ одного вида превращаются в одно новое (5 крыс -> Крысиный король)."""


def _pool(state):
    return state.party + state.storage


def available(data, state):
    """Список рецептов, на которые хватает существ."""
    out = []
    for f in data.fusions:
        counts = {}
        for c in _pool(state):
            counts[c.species_id] = counts.get(c.species_id, 0) + 1
        if all(counts.get(sp, 0) >= n for sp, n in f["inputs"].items()):
            out.append(f)
    return out


def craft(data, state, fusion_id):
    """Выполняет крафт. Возвращает созданное существо или None.
    Расходуются существа с наименьшим уровнем, результат - средний уровень + 3.
    Нельзя расходовать последнего боеспособного бойца в команде."""
    f = next((x for x in data.fusions if x["id"] == fusion_id), None)
    if f is None or f not in available(data, state):
        return None
    chosen = []
    for sp, n in f["inputs"].items():
        mons = sorted([c for c in _pool(state) if c.species_id == sp], key=lambda c: c.level)[:n]
        chosen += mons
    remaining = [c for c in state.party if c not in chosen and c.hp > 0]
    if not remaining and not any(c not in chosen for c in state.storage):
        return None
    lvl = min(100, sum(c.level for c in chosen) // len(chosen) + 3)
    for c in chosen:
        (state.party if c in state.party else state.storage).remove(c)
    result = data.make_creature(f["result"], lvl, iv={k: round(sum(c.iv[k] for c in chosen) / len(chosen)) for k in chosen[0].iv},
                                nature=chosen[0].nature)
    state.add_creature(result)
    return result
