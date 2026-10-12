"""Общий сценарий боёв: запуск и разбор итогов (используется картой мира и отладочным хабом)."""
from game.battle.engine import Battle
from game.scenes.base import MessageScene
from game.scenes.battle_scene import BattleScene
from game.scenes.screens import learn_chain
from game.systems import evolution


def after_battle(app, b, result, tid=None):
    """Применяет итоги боя к состоянию игрока, возвращает список сообщений."""
    st, d, msgs = app.state, app.data, []
    if result == "caught":
        where = st.add_creature(b.caught)
        msgs.append(f"{b.caught.name} " + ("в команде." if where == "party" else "отправлен в заначку (команда полна)."))
    elif result == "win" and tid:
        tr = d.trainers[tid]
        st.defeated.add(tid)
        st.money += tr["reward"]
        msgs.append(f"{tr['name']} проиграл и отдаёт {tr['reward']} монет.")
        if tr.get("badge") and tr["badge"] not in st.badges:
            st.badges.append(tr["badge"])
            msgs.append("Получен значок бомжлидера!")
    elif result == "lose":
        st.heal_party()
        msgs.append("Тебя откачали. Всё как будто ничего и не было.")
    for c in st.party:
        into = evolution.level_evolution(c)
        while into:
            old = c.name
            evolution.evolve(d, c, into)
            msgs.append(f"{old} эволюционировал в {c.species['name']}!")
            into = evolution.level_evolution(c)
    return msgs


def _run(app, battle, tid, on_finish):
    def done(result):
        msgs = after_battle(app, battle, result, tid)

        def finish():   # после сообщений - предложить выучить ждущие приёмы, потом вернуть управление
            learn_chain(app, [c for c in app.state.party if c.pending_moves], (lambda: on_finish(result)) if on_finish else None)
        if msgs:
            app.push(MessageScene(app, msgs, on_done=finish))
        else:
            finish()
    app.push(BattleScene(app, battle, done))


def start_wild(app, district, on_finish=None):
    st, d = app.state, app.data
    foe = d.roll_encounter(district)
    st.seen.add(foe.species_id)
    _run(app, Battle(d, st.party, [foe], wild=True, bag=st.bag), None, on_finish)


def start_trainer(app, tid, on_finish=None):
    st, d = app.state, app.data
    tr = d.trainers[tid]
    party = [d.make_creature(sp, lv) for sp, lv in tr["party"]]
    st.seen.update(c.species_id for c in party)
    _run(app, Battle(d, st.party, party, wild=False, bag=st.bag, enemy_name=tr["name"]), tid, on_finish)
