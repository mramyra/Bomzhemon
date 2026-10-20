"""Простая шина событий: игровой код сообщает "что произошло", а звук/эффекты подписываются на это отдельно.
    app.events.on("evolution_start", fn)  /  app.events.emit("evolution_start", creature=c, into="khomyak")"""
import sys
import traceback


class EventBus:
    def __init__(self):
        self._handlers = {}

    def on(self, name, fn):
        self._handlers.setdefault(name, []).append(fn)

    def off(self, name, fn):
        if fn in self._handlers.get(name, []):
            self._handlers[name].remove(fn)

    def emit(self, name, **kw):
        for fn in list(self._handlers.get(name, ())):
            try:
                fn(**kw)
            except Exception:  # noqa  - ошибка в обработчике (например, звука) не должна ронять игру
                print(f"[events] ошибка обработчика {name}:", file=sys.stderr)
                traceback.print_exc()
