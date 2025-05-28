import sys
from deezer import Deezer

from src.backend.downloader import Downloader
from src.backend.spotify import SpotifyConverter
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
from src.backend.sc import SoundCloudClient


class Controller:
    """Controller class"""

    DEEZER_ARL = "DEEZER_ARL"

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
        """Start backend"""
        self.setup_config()
        self.subscribe(app)
        self.login()

    def setup_config(self):
        """Setup configurations"""
        self.config: Config = Config()
        self.converter: SpotifyConverter = SpotifyConverter(
            self.dz, self.config, self.task_controller
        )
        self.sc: SoundCloudClient = SoundCloudClient(self.task_controller, self.config)

    def login(self):
        """Logins a client to spotify and deezer"""
        self.arl = self.config.get_env_variable(self.DEEZER_ARL)
        self.dz = Deezer()  # känns shady men fuck it
        self.converter.dz = self.dz
        self.deezer_utils.dz = self.dz
        self.deezer_connected = self.dz.login_via_arl(self.arl)
        self.spotify_connected = self.converter.login()
        self.dispatcher.publish_login_status_message(
            self.spotify_connected, self.deezer_connected
        )

    def can_stream_with_bit_rate(self, bit_rate: str) -> bool:
        """Checks if user can stream with the given bit rate"""
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
        if self.converter.valid_url(query):
            task_id = self.task_controller.create_conversion_task(query)
            self.task_controller.queue_conversion_task(task_id)
            self.job_runner.push(
                SpotifyJob(
                    task_id,
                    query,
                    self.dz,
                    self.dispatcher,
                    self.converter,
                    self.task_controller,
                    self.config,
                )
            )
        elif self.sc.valid_url(query):
            task_id = self.task_controller.create_conversion_task(query)
            self.task_controller.queue_conversion_task(task_id)
            self.job_runner.push(
                SoundCloudJob(
                    task_id,
                    self.sc,
                    self.dispatcher,
                    self.task_controller,
                    self.config,
                )
            )
        else:
            # default fallback is search downloads
            # query is id of song on deezer
            download_obj = self.deezer_utils.create_download_obj(query)
            self.task_controller.queue_conversion_task(download_obj.task.id)
            self.job_runner.push(
                SearchDownloadJob(
                    download_obj,
                    self.dz,
                    self.dispatcher,
                    self.task_controller,
                    self.config,
                )
            )

    def valid_url(self, url) -> bool:
        return self.converter.valid_url(url) or self.sc.valid_url(url)

    def search(self, query):
        """Search for song on deezer"""
        return self.deezer_utils.search(query)

    def subscribe(self, subscriber) -> None:
        """Subscribe to message system"""
        self.dispatcher.subsribe(subscriber)

    def get_tasks(self) -> list[dict]:
        """Returns all active tasks"""
        return self.task_controller.get_all_tasks()

    def remove_task(self, task_id) -> None:
        """Marks a task as non-active (removed/cancelled)"""
        self.task_controller.cancel_task(task_id)

    def remove_all_tasks(self) -> None:
        """Marks many tasks as non-active"""
        self.converter.restart_executor()
        self.task_controller.cancel_all()
