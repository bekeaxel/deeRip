import sys
import os


def resource_path(relative_path):
    if hasattr(sys, "_MEIPASS"):
        return os.path.join(sys._MEIPASS, relative_path)
    return relative_path


def app_version() -> str:
    """Release version stamped in at build time, "dev" when running from source"""
    try:
        with open(resource_path("VERSION")) as file:
            return file.read().strip()
    except OSError:
        return "dev"
