from game.ui.widgets import Menu, panel, text, wrap, arrow


class Scene:
    transparent = False     # True - сцена рисуется поверх предыдущей

    def __init__(self, app):
        self.app = app

    def handle(self, action):
        pass

    def update(self, dt):
        pass

    def draw(self, surf):
        pass


class MessageScene(Scene):
    """Окошко с репликами внизу экрана. По завершении вызывает on_done."""
    transparent = True

    def __init__(self, app, lines, on_done=None):
        super().__init__(app)
        self.lines, self.i, self.on_done = [l for l in lines if l] or ["..."], 0, on_done

    def handle(self, a):
        if a in ("ok", "back"):
            self.i += 1
            if self.i >= len(self.lines):
                self.app.pop()
                if self.on_done:
                    self.on_done()

    def draw(self, surf):
        panel(surf, (8, 232, 464, 80))
        for k, ln in enumerate(wrap(self.lines[self.i], 440)[:3]):
            text(surf, ln, 20, 242 + k * 22)
        arrow(surf, 452, 292, 6)


class ChoiceScene(Scene):
    """Вопрос с вариантами по центру экрана. Z - выбрать, X - последний вариант (или cancel). После выбора окно
    закрывается, затем вызывается on_choice(номер)."""
    transparent = True

    def __init__(self, app, question, options, on_choice, cancel=None):
        super().__init__(app)
        self.q, self.opts, self.cb = question, list(options), on_choice
        self.cancel = len(options) - 1 if cancel is None else cancel
        self.menu = Menu(self.opts)

    def handle(self, a):
        r = self.menu.handle(a)
        if r in ("ok", "back"):
            i = self.menu.i if r == "ok" else self.cancel
            self.app.pop()
            self.cb(i)

    def draw(self, surf):
        lines = wrap(self.q, 380)
        h = 24 + len(lines) * 18 + len(self.opts) * 24
        y0 = (320 - h) // 2
        panel(surf, (40, y0, 400, h))
        for k, ln in enumerate(lines):
            text(surf, ln, 56, y0 + 12 + k * 18, 15)
        self.menu.draw(surf, 60, y0 + 18 + len(lines) * 18, row_h=24, size=15)
