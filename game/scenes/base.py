from game.ui.widgets import panel, text, wrap, arrow


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
