"""Бомжемон. Запуск: python main.py"""
from game.core.app import App
from game.scenes.title import TitleScene


def main():
    app = App()
    app.push(TitleScene(app))
    app.run()


if __name__ == "__main__":
    main()
