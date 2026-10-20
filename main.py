"""Бомжемон. Запуск: python main.py"""
import traceback

from game.core import paths
from game.core.app import App
from game.scenes.title import TitleScene


def main():
    try:
        app = App()
        app.push(TitleScene(app))
        app.run()
    except SystemExit:
        raise
    except BaseException:   # в оконной сборке консоли нет - пишем причину в crash.log рядом с игрой
        try:
            paths.CRASH_LOG.write_text(traceback.format_exc(), encoding="utf-8")
        except OSError:
            pass
        raise


if __name__ == "__main__":
    main()
