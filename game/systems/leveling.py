"""Начисление опыта и повышение уровней (общий код для боя и консоли)."""
from game.battle.creature import MAX_LEVEL, exp_for_level


def apply_exp(data, c, amount):
    """Начисляет опыт, повышает уровни, учит приёмы из learnset.
    Возвращает события по порядку: ("level", N), ("learned", move_id), ("pending", move_id)."""
    out = []
    c.exp += amount
    while c.level < MAX_LEVEL and c.exp >= exp_for_level(c.level + 1):
        c.level_up()
        out.append(("level", c.level))
        for lv, mv in c.species["learnset"]:
            if lv == c.level and mv not in [m["id"] for m in c.moves] and mv not in c.pending_moves:
                out.append(("learned" if c.learn(data, mv) else "pending", mv))
    return out
