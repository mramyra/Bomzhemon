"""Обмен с NPC-Менялой (позже - по сети). Эволюция по обмену: существо B эволюционирует,
когда его получают ВЗАМЕН существа вида A (поле evolutions: method=trade, partner=A).
Менялa отдаёт существо B того же уровня, что и отданное, и оно сразу эволюционирует."""
from game.systems import evolution


def options_for(data, given_species):
    """[(что получаешь, во что оно эволюционирует)] за существо этого вида."""
    out = []
    for sid, sp in data.species.items():
        for e in sp["evolutions"]:
            if e["method"] == "trade" and e["partner"] == given_species:
                out.append((sid, e["into"]))
    return out


def tradable(data, state):
    """[(существо, варианты)] - кого из твоих можно отдать Меняле."""
    return [(c, o) for c in state.party + state.storage for o in [options_for(data, c.species_id)] if o]


def execute(data, state, give, receive_species, into):
    """Меняет give на нового получаемого. Новое существо ставится на место отданного. Возвращает его."""
    if (receive_species, into) not in options_for(data, give.species_id):
        raise ValueError("такого обмена нет")
    pool = state.party if give in state.party else state.storage
    if give not in pool:
        raise ValueError("существа нет у игрока")
    new = data.make_creature(receive_species, give.level)
    given_species = give.species_id
    assert evolution.trade_evolution(new, given_species) == into
    evolution.evolve(data, new, into)
    new.hp = new.max_hp
    pool[pool.index(give)] = new
    state.seen.update({receive_species, into})
    state.caught.add(into)
    return new
