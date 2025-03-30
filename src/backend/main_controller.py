import os
from concurrent.futures import ThreadPoolExecutor
from queue import Queue
import shutil
from pathlib import Path

from deezer import Deezer

# from deemix.types.DownloadObjects import *

from src.backend.downloader import Downloader
from src.backend.converter import Converter
from src.backend.deezer_utils import DeezerUtils
from src.backend.configuration import Config
from src.backend.tasks import *
from src.frontend.messages import *
from src.backend.message_dispatcher import MessageDispatcher
from src.backend.task_controller import TaskController
from src.backend.download_objects import *
from src.backend.types import *
from src.backend.jobs import *
from src.backend.job_runner import JobRunner


class Controller:
    """Controller class"""

    def __init__(self):

        self.dispatcher: MessageDispatcher = MessageDispatcher()
        self.task_controller: TaskController = TaskController(self.dispatcher)
        self.dz: Deezer = Deezer()

        self.deezer_utils: DeezerUtils = DeezerUtils(
            self.dz, self.task_controller, self.dispatcher
        )
        self.job_runner: JobRunner = JobRunner()
        self.deezer_connected = False
        self.spotify_connected = False

    def start_up(self, app):
        self.setup_config()
        self.subscribe(app)
        self.login()
        # check if config fiel exists

    def setup_config(self):
        if not Path("config/config.yml").exists():
            shutil.copy("config/config_default.yml", "config/config.yml")

        if not Path("config/tokens.env").exists():
            shutil.copy("config/tokens_default.env", "config/tokens.env")

        self.config: Config = Config()
        self.config.load_env_variables()
        self.converter: Converter = Converter(
            self.dz, self.config, self.task_controller
        )

    def login(self):
        """Logins a client"""
        self.arl = os.getenv("DEEZER_ARL")
        self.dz = Deezer()  # känns shady men fuck it
        self.converter.dz = self.dz
        self.deezer_utils.dz = self.dz
        self.deezer_connected = self.dz.login_via_arl(self.arl)
        self.spotify_connected = self.converter.login()
        self.dispatcher.publish_login_status_message(
            self.spotify_connected, self.deezer_connected
        )

    def valid_url(self, link: str) -> bool:
        return self.converter.valid_url(link)

    def can_stream_with_bit_rate(self, bit_rate: str) -> bool:
        match bit_rate:
            case "FLAC":
                return self.dz.current_user.get("can_stream_lossless")
            case "MP3_320":
                return self.dz.current_user.get("can_stream_hq")
            case _:
                return True

    def create_job(self, query: str) -> None:
        """Creates a job and puts in the queue of the job runner. Returns task_id"""
        # måste skapa task innan den läggs i jobbkön för att kunna visa den i frontend
        if self.valid_url(query):
            task_id = self.task_controller.create_conversion_task(query)
            self.job_runner.push(
                SpotifyJob(
                    task_id,
                    self.dz,
                    self.dispatcher,
                    self.converter,
                    self.task_controller,
                    self.config,
                )
            )
        else:
            # here, query is id of song on deezer
            download_obj = self.deezer_utils.create_download_obj(query)
            self.job_runner.push(
                SearchDownloadJob(
                    download_obj,
                    self.dz,
                    self.dispatcher,
                    self.task_controller,
                    self.config,
                )
            )
            # fallback is search downloads

    def search(self, query):
        return self.deezer_utils.search(query)

    def get_tasks(self) -> list[dict]:
        return self.task_controller.get_all_tasks()

    def subscribe(self, subscriber) -> None:
        self.dispatcher.subsribe(subscriber)

    def remove_task(self, task_id) -> None:
        self.task_controller.cancel_task(task_id)

    def remove_all_tasks(self) -> None:
        self.converter.restart_executor()
        self.task_controller.cancel_all()
