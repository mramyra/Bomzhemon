"""ПК: перенос существ между командой и ящиками, отпускание, сортировка. Чистая логика, без pygame.
Место задаётся парой ("party", i) или ("box", i), где i для ящиков - сквозной номер в state.storage."""

BOX_SIZE = 30       # клеток в ящике (6 x 5)
PARTY_MAX = 6


class PCError(Exception):
    pass


def _list(state, kind):
    return state.party if kind == "party" else state.storage


def get(state, loc):
    kind, i = loc
    lst = _list(state, kind)
    return lst[i] if 0 <= i < len(lst) else None


def pages(state):
    """Сколько ящиков показывать: всегда есть хотя бы один (в том числе пустой для переноса)."""
    return len(state.storage) // BOX_SIZE + 1


def move(state, src, dst):
    """Ставит существо из src в dst. В занятую клетку - меняет местами, в пустую - переносит.
    Возвращает текст результата; PCError - если так нельзя (команда пустая/полная)."""
    c = get(state, src)
    if c is None:
        raise PCError("Тут никого нет.")
    if src == dst:
        return f"{c.name} остаётся на месте."
    (sk, si), (dk, di) = src, dst
    target = get(state, dst)
    if target is not None:
        _list(state, sk)[si], _list(state, dk)[di] = target, c
        return f"{c.name} и {target.name} поменялись местами."
    if dk == "party" and sk != "party" and len(state.party) >= PARTY_MAX:
        raise PCError(f"Команда полна ({PARTY_MAX}).")
    if sk == "party" and dk != "party" and len(state.party) <= 1:
        raise PCError("Нельзя оставить команду пустой.")
    _list(state, sk).pop(si)
    dest = _list(state, dk)
    dest.insert(min(di, len(dest)), c)
    return f"{c.name}: {'в команду' if dk == 'party' else 'в ПК'}."


def deposit(state, party_index):
    return move(state, ("party", party_index), ("box", len(state.storage)))


def withdraw(state, box_index):
    return move(state, ("box", box_index), ("party", len(state.party)))


def release(state, loc):
    """Отпустить существо на волю. Возвращает его. Последнего бойца в команде отпускать нельзя."""
    c = get(state, loc)
    if c is None:
        raise PCError("Тут никого нет.")
    if loc[0] == "party" and len(state.party) <= 1:
        raise PCError("Последнего бойца отпускать нельзя.")
    _list(state, loc[0]).pop(loc[1])
    return c


SORT_MODES = {"dex": "по номеру в Бомждексе", "level": "по уровню", "name": "по имени"}


def sort_box(data, state, mode):
    order = {sid: i for i, sid in enumerate(data.species)}
    keys = {"dex": lambda c: (order[c.species_id], -c.level),
            "level": lambda c: (-c.level, order[c.species_id]),
            "name": lambda c: (c.name.casefold(), -c.level)}
    if mode not in keys:
        raise PCError("Неизвестная сортировка.")
    state.storage.sort(key=keys[mode])
