"""Оверлей консоли отладки. Открыть: ` (тильда/ё) или F1. Закрыть: то же или Esc."""
import pygame

from game.debug.console import Console
from game.scenes import flow
from game.scenes.base import Scene
from game.scenes.evolution_scene import EvolutionScene
from game.scenes.pc import PCScene
from game.scenes.world import DISTRICT
from game.systems import save
from game.ui.widgets import mono

W, H, LINES = 480, 214, 14


class ConsoleScene(Scene):
    transparent = True
    wants_text = True       # App отдаёт сцене сырые нажатия клавиш (ввод текста)

    def __init__(self, app):
        super().__init__(app)
        if not hasattr(app, "console"):
            app.console = Console(app.data, lambda: app.state)
        self.con = app.console
        self.con.hooks = self._hooks()
        self.line, self.hist_i, self.scroll = "", None, 0
        if not self.con.log:
            self.con.log.append("Консоль отладки. help - список команд, Tab - дополнить, стрелки - история, ` или Esc - закрыть.")
        pygame.key.set_repeat(350, 35)
        app.held.clear()

    # ---------------------------------------------------------------- связь с игрой
    def _world(self):
        return next((s for s in self.app.stack if getattr(s, "is_world", False)), None)

    def close(self):
        pygame.key.set_repeat()
        self.app.held.clear()
        if self in self.app.stack:
            self.app.stack.remove(self)

    def _hooks(self):
        app = self.app

        def battle(foe):
            w = self._world()
            self.close()
            flow.start_wild(app, DISTRICT, w._after_battle if w else None, foe=foe)

        def trainer(tid):
            w = self._world()
            self.close()
            flow.start_trainer(app, tid, w._after_battle if w else None)

        def do_save():
            w = self._world()
            if w:
                w.sync_pos()
            save.save(app.state, app.state.slot or 1, location=app.data.districts.get(app.state.pos.get("map"), {}).get("name", ""))

        def evo_anim(c, into):
            self.close()
            app.push(EvolutionScene(app, c, into, cancellable=True, cause="preview", preview=True))

        def open_pc():
            self.close()
            app.push(PCScene(app))

        hooks = {"close": self.close, "battle": battle, "trainer": trainer, "save": do_save, "pc": open_pc, "evolution_anim": evo_anim}
        if self._world():
            hooks["teleport"] = lambda x, y: self._world().teleport(x, y)
            hooks["pos"] = lambda: (self._world().x, self._world().y)
        return hooks

    # ---------------------------------------------------------------- ввод
    def on_key(self, e):
        k, con = e.key, self.con
        if k in (pygame.K_BACKQUOTE, pygame.K_F1, pygame.K_ESCAPE):
            self.close()
        elif k in (pygame.K_RETURN, pygame.K_KP_ENTER):
            line, self.line, self.hist_i, self.scroll = self.line, "", None, 0
            con.run(line)
        elif k == pygame.K_BACKSPACE:
            self.line = self.line[:-1]
        elif k == pygame.K_TAB:
            self.line, cands = con.complete(self.line)
            if len(cands) > 1:
                con.log.append("  " + "  ".join(cands[:12]) + (" ..." if len(cands) > 12 else ""))
        elif k == pygame.K_UP and con.history:
            self.hist_i = len(con.history) - 1 if self.hist_i is None else max(0, self.hist_i - 1)
            self.line = con.history[self.hist_i]
        elif k == pygame.K_DOWN and self.hist_i is not None:
            self.hist_i += 1
            if self.hist_i >= len(con.history):
                self.hist_i, self.line = None, ""
            else:
                self.line = con.history[self.hist_i]
        elif k == pygame.K_PAGEUP:
            self.scroll += 5
        elif k == pygame.K_PAGEDOWN:
            self.scroll = max(0, self.scroll - 5)
        elif e.unicode and e.unicode.isprintable():
            self.line += e.unicode

    # ---------------------------------------------------------------- рисование
    def _wrapped(self, font, width):
        out = []
        for ln in self.con.log:
            while font.size(ln)[0] > width and len(ln) > 1:
                cut = len(ln)
                while cut > 1 and font.size(ln[:cut])[0] > width:
                    cut -= 1
                out.append(ln[:cut])
                ln = "  " + ln[cut:]
            out.append(ln)
        return out

    def draw(self, surf):
        ov = pygame.Surface((W, H), pygame.SRCALPHA)
        ov.fill((10, 12, 20, 232))
        surf.blit(ov, (0, 0))
        f = mono(12)
        lines = self._wrapped(f, W - 16)
        self.scroll = min(self.scroll, max(0, len(lines) - LINES))
        end = len(lines) - self.scroll
        for i, ln in enumerate(lines[max(0, end - LINES):end]):
            surf.blit(f.render(ln, True, (200, 230, 200) if not ln.startswith(">") else (255, 230, 140)), (8, 6 + i * 13))
        cursor = "_" if pygame.time.get_ticks() // 400 % 2 else " "
        surf.blit(f.render("> " + self.line + cursor, True, (255, 255, 255)), (8, H - 18))
