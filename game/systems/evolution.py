"""Эволюции: по уровню и по предмету. Крафт (слияние) - в fusion.py."""


def level_evolution(creature):
    for ev in creature.species["evolutions"]:
        if ev["method"] == "level" and creature.level >= ev["level"]:
            return ev["into"]
    return None


def pending_level_evolution(creature):
    """Эволюция по уровню, которую стоит предложить сейчас: если игрок отменил её на этом уровне - ждём следующего."""
    into = level_evolution(creature)
    return into if into and creature.declined_evolution_level != creature.level else None


def item_evolution(creature, item_id):
    for ev in creature.species["evolutions"]:
        if ev["method"] == "item" and ev["item"] == item_id:
            return ev["into"]
    return None


def trade_evolution(creature, given_species_id):
    """Существо получено в обмен на существо вида given_species_id: во что оно эволюционирует (или None)."""
    for ev in creature.species["evolutions"]:
        if ev["method"] == "trade" and ev["partner"] == given_species_id:
            return ev["into"]
    return None


def evolve(data, creature, into_id):
    """Превращает существо на месте. Сохраняет долю HP, приёмы и опыт."""
    ratio = creature.hp / creature.max_hp
    creature.species_id, creature.species = into_id, data.species[into_id]
    creature.recalc()
    creature.hp = max(1, round(creature.max_hp * ratio))
    for lv, mv in creature.species["learnset"]:
        if lv == creature.level:
            creature.learn(data, mv)
    return creature


def apply(data, state, creature, into):
    """Эволюция с записью в Бомждекс (вид считается встреченным и пойманным)."""
    evolve(data, creature, into)
    creature.declined_evolution_level = None
    state.seen.add(into)
    state.caught.add(into)
    return creature
