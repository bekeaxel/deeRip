import yaml
import os
import sys
from pathlib import Path
import dotenv
from dotenv import load_dotenv
import shutil

from src.backend.utils import resource_path


class Config:

    def __init__(self):
        self.user_config_path = Path.home() / ".deeRip" / "config.yml"
        self.user_env_path = Path.home() / ".deeRip" / "tokens.env"

        self.user_config_path.parent.mkdir(parents=True, exist_ok=True)

        if not self.user_config_path.exists():
            shutil.copy(
                resource_path("config/config_default.yml"), self.user_config_path
            )
            # set default download folder cross-platform
            config = self.load_config()
            config["download_folder"] = Path.home() / "downloads" / "deeRip"
            self.update_config(config)

        if not self.user_env_path.exists():
            shutil.copy(resource_path("config/tokens_default.env"), self.user_env_path)

        dotenv.load_dotenv(self.user_env_path)

    def load_config(self) -> dict:
        if not self.user_config_path.exists():
            raise FileNotFoundError(f"Config file was not found")

        with open(self.user_config_path, "r") as file:
            return yaml.safe_load(file)

    def save_config(self, config: dict):
        with open(self.user_config_path, "w") as file:
            yaml.dump(config, file, default_flow_style=False)

    def update_config(self, updates: dict):
        updates["download_folder"] = str(updates["download_folder"])
        config = self.load_config()
        config.update(updates)
        self.save_config(config)

    def update_env_variable(self, key: str, value: str):
        dotenv.set_key(self.user_env_path, key, value)
        os.environ[key] = value

    def get_env_variable(self, key: str):
        return os.getenv(key)
