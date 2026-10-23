"""Выход из игры и в главное меню: вопрос «сохранять ли?». Один сценарий для паузы и для закрытия окна (крестик, Alt+F4)."""
from game.scenes.base import ChoiceScene, MessageScene
from game.scenes.saveload import SlotScene
from game.systems import save


def _world(app):
    return next((s for s in app.stack if getattr(s, "is_world", False)), None)


def _exit(app, to_menu):
    if to_menu:
        from game.scenes.title import go_title
        go_title(app)
    else:
        app.quit()


def _save_and_exit(app, world, to_menu):
    st = app.state
    loc = app.data.districts.get(world.district, {}).get("name", "")
    if st.slot:                 # слот этой сессии известен - пишем в него
        try:
            world.sync_pos()
            save.save(st, st.slot, location=loc)
        except save.SaveError as e:
            app.push(MessageScene(app, [f"Ошибка: {e}"]))
            return
        _exit(app, to_menu)
    else:                       # слота нет - выбираем, куда сохранить
        app.push(SlotScene(app, "save", on_done=lambda: _exit(app, to_menu), prepare=world.sync_pos))


def ask_exit(app, to_menu):
    """Спрашивает, сохранять ли перед выходом. В бою сохранить нельзя - предлагается только выйти или остаться."""
    world = _world(app)
    if world is None or app.state is None:      # сохранять нечего (титульный экран, отладочный хаб)
        _exit(app, to_menu)
        return
    q = "Выйти в главное меню?" if to_menu else "Выйти из игры?"
    if any(getattr(s, "is_battle", False) for s in app.stack):
        scene = ChoiceScene(app, q + " В бою сохранить нельзя, прогресс с последнего сохранения будет потерян.",
                            ["Выйти без сохранения", "Отмена"], lambda i: _exit(app, to_menu) if i == 0 else None)
    else:
        def choose(i):
            if i == 0:
                _save_and_exit(app, world, to_menu)
            elif i == 1:
                _exit(app, to_menu)
        scene = ChoiceScene(app, q + " Несохранённый прогресс будет потерян.", ["Сохранить и выйти", "Выйти без сохранения", "Отмена"], choose)
    scene.is_exit_prompt = True
    app.push(scene)


def request_quit(app):
    """Закрытие окна: если идёт игра - спросить; повторное закрытие при открытом вопросе выходит сразу."""
    if not app.stack or any(getattr(s, "is_exit_prompt", False) for s in app.stack):
        app.quit()
    else:
        ask_exit(app, to_menu=False)
