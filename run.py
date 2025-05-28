import sys

IS_DEV = not hasattr(sys, "_MEIPASS")

from src.frontend.app import DeeRipApp

if __name__ == "__main__":
    app = DeeRipApp(dev_mode=IS_DEV)
    app.run()
