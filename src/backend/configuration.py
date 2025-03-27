import yaml
import os
from pathlib import Path
import dotenv
from dotenv import load_dotenv


class Config:

    def __init__(self, config_path: str = "../../config/config.yml"):
        self.config_path = Path(
            os.path.join(os.path.dirname(os.path.abspath(__file__)), config_path)
        )

    def _env_path(self):
        return Path(
            os.path.join(
                os.path.dirname(os.path.abspath(__file__)),
                self.load_config()["env_file"],
            )
        ).absolute()

    def load_config(self) -> dict:
        if not self.config_path.exists():
            raise FileNotFoundError(f"Config file was not found")

        with open(self.config_path, "r") as file:
            return yaml.safe_load(file)

    def save_config(self, config: dict):
        with open(self.config_path, "w") as file:
            yaml.dump(config, file, default_flow_style=False)

    def update_config(self, updates: dict):
        # load in config
        config = self.load_config()
        # update the values
        config.update(updates)
        # save the updates
        self.save_config(config)

    def load_env_variables(self):
        # load variables in as env variables on computer
        dotenv.load_dotenv(self._env_path())

    def update_env_variables(self, key: str, value: str):
        # update value in env file
        dotenv.set_key(self._env_path(), key, value)
        # reload all variables in memory
        os.environ[key] = value
