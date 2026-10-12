"""Работа с приёмами существа: порядок, замена, ждущие выучки, текстовые описания. Без pygame."""

STAT_RU = {"atk": "Атаку", "def": "Защиту", "spa": "Спец. атаку", "spd": "Спец. защиту", "spe": "Скорость"}
STATUS_VERB = {"psn": "отравить", "brn": "обжечь", "par": "ввести в тремор", "slp": "усыпить"}
CATEGORY_RU = {"physical": "Физ.", "special": "Спец.", "status": "Статус"}


def swap_moves(c, i, j):
    """Меняет приёмы местами. Возвращает True, если что-то поменялось."""
    n = len(c.moves)
    if i == j or not (0 <= i < n and 0 <= j < n):
        return False
    c.moves[i], c.moves[j] = c.moves[j], c.moves[i]
    return True


def learn_move(data, c, move_id, slot=None):
    """Выучить приём. slot=None - в свободную ячейку (их должно быть < 4 приёмов),
    slot=N - заменить приём в ячейке N. Возвращает id забытого приёма или None."""
    if move_id not in data.moves:
        raise ValueError(f"нет приёма {move_id}")
    if any(m["id"] == move_id for m in c.moves):
        decline_move(c, move_id)
        return None
    pp = data.moves[move_id]["pp"]
    new = {"id": move_id, "pp": pp, "max_pp": pp}
    forgot = None
    if slot is None:
        if len(c.moves) >= 4:
            raise ValueError("нет свободной ячейки, укажи slot")
        c.moves.append(new)
    else:
        if not 0 <= slot < len(c.moves):
            raise ValueError("неверная ячейка")
        forgot = c.moves[slot]["id"]
        c.moves[slot] = new
    decline_move(c, move_id)
    return forgot


def decline_move(c, move_id):
    """Убрать приём из очереди на выучку (не учить)."""
    if move_id in c.pending_moves:
        c.pending_moves.remove(move_id)


def describe_move(data, move_id):
    """Короткое описание эффекта приёма для экрана."""
    m = data.moves[move_id]
    fx, parts = m["effect"], []
    if "status" in fx:
        s = fx["status"]
        parts.append(f"{'Шанс ' + str(s['chance']) + '%: ' if s['chance'] < 100 else ''}{STATUS_VERB[s['id']]} цель")
    if "confuse" in fx:
        parts.append(f"Шанс {fx['confuse']}%: ввести цель в ступор")
    if "flinch" in fx:
        parts.append(f"Шанс {fx['flinch']}%: цель в страхе и пропустит ход")
    if "stat" in fx:
        s = fx["stat"]
        who = "цели" if s["who"] == "foe" else "себе"
        verb = "Повышает" if s["stages"] > 0 else "Снижает"
        parts.append(f"{verb} {STAT_RU[s['stat']]} {who} на {abs(s['stages'])}")
    if not parts:
        parts.append("Обычный удар." if m["category"] != "status" else "Без эффекта.")
    return "; ".join(parts) + "."


def evolution_hints(data, c):
    """Подсказки, как это существо развивается."""
    out = []
    for e in c.species["evolutions"]:
        into = data.species[e["into"]]["name"]
        out.append(f"Эволюция: Lv{e['level']} - {into}" if e["method"] == "level" else f"Эволюция: {data.items[e['item']]['name']} - {into}")
    for f in data.fusions:
        if c.species_id in f["inputs"]:
            out.append(f"Крафт: {f['inputs'][c.species_id]} шт. - {data.species[f['result']]['name']}")
    return out
