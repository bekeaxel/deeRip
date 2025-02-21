import os
from concurrent.futures import ThreadPoolExecutor
from queue import Queue

from deezer import Deezer

# from deemix.types.DownloadObjects import *

from src.backend.downloader import Downloader
from src.backend.converter import Converter
from src.backend.deezer_utils import DeezerUtils
from src.backend.configuration import Config
from src.backend.tasks import *
from src.ui.messages import *
from src.backend.message_dispatcher import MessageDispatcher
from src.backend.task_controller import TaskController
from src.backend.download_objects import *
from src.backend.types import *


class Controller:
    """Controller class"""

    def __init__(self):
        self._config: Config = Config()
        self._config.load_env_variables()
        self._dispatcher: MessageDispatcher = MessageDispatcher()
        self._task_controller: TaskController = TaskController(self._dispatcher)
        self._deezer: Deezer = Deezer()
        self._converter: Converter = Converter(
            self._deezer, self._config, self._task_controller
        )
        self._deezer_utils: DeezerUtils = DeezerUtils(
            self._deezer, self._task_controller
        )
        self._executor: ThreadPoolExecutor = ThreadPoolExecutor(max_workers=4)
        self._download_queue: dict[UUID, IDownloadObject] = {}
        self._current_downloader = None
        self._conversion_queue: Queue[UUID] = Queue()
        self._busy = False
        self._deezer_connected = False
        self._spotify_connected = False

    def login(self):
        """Logins a client"""
        self.arl = os.getenv("DEEZER_ARL")
        self._deezer = Deezer()  # känns shady men fuck it
        self._converter.dz = self._deezer
        self._deezer_utils.dz = self._deezer
        self._deezer_connected = self._deezer.login_via_arl(self.arl)
        self._spotify_connected = self._converter.login()
        self._dispatcher.publish_login_status_message(
            self._spotify_connected, self._deezer_connected
        )

    def valid_url(self, link: str) -> bool:
        return self._converter.valid_url(link)

    def can_stream_with_bit_rate(self, bit_rate: str) -> bool:
        match bit_rate:
            case "MP3_320":
                print(f"can stream hq {self._deezer.current_user.get("can_stream_hq")}")
                return self._deezer.current_user.get("can_stream_hq")
            case _:
                return True

    def create_conversion_task(self, spotify_link: str) -> str:
        print("creating conversion task")
        task_id = self._task_controller.create_conversion_task(spotify_link)
        self.add_conversion_task(task_id)
        return str(task_id)

    def add_conversion_task(self, task_id: UUID) -> None:
        print("add_conversion")
        if not self._busy:
            print("no queue, starting task")
            self._executor.submit(self.run_conversion_task, task_id)
        else:
            self._conversion_queue.put(task_id)

    def start_next_conversion_task(self) -> None:
        if self._conversion_queue.qsize() > 0:
            task_id: UUID = self._conversion_queue.get()
            self.run_conversion_task(task_id)

    def run_conversion_task(self, task_id: UUID) -> None:
        """Runs a conversion task."""
        print(f"conversion task {task_id} started")
        self._busy = True
        self._task_controller.start_task(task_id)
        link = self._task_controller.get_task(task_id).link

        try:
            download_obj: IDownloadObject = self._converter.generate_download_obj(
                link, task_id
            )

            print(f"conversion task {task_id} finished")

            download_tasks = []

            if isinstance(download_obj, Single):

                download_tasks.append(
                    {
                        "task_id": str(download_obj.task.id),
                        "song_id": download_obj.song_id,
                        "title": download_obj.title,
                        "artist": download_obj.artist,
                        "album": download_obj.album,
                        "error": download_obj.task.error,
                    }
                )

            if isinstance(download_obj, Collection):
                for task in download_obj.tasks:

                    download_tasks.append(
                        {
                            "task_id": str(task.id),
                            "song_id": task.track.id,
                            "title": task.track.title,
                            "artist": task.track.artist.name,
                            "album": task.track.album.title,
                            "error": task.error,
                        }
                        if not task.error
                        else {
                            "task_id": str(task.id),
                            "song_id": task.error_obj.id,
                            "title": task.error_obj.title,
                            "artist": task.error_obj.artist,
                            "album": task.error_obj.album,
                            "error": task.error,
                        }
                    )

            self._download_queue[task_id] = download_obj
            self._dispatcher.publish_conversion_complete_message(
                task_id, download_tasks
            )

        # fånga alla olika exceptions här. låt de inte gå. Kanske skicak meddelande till frontend sen.

        except ConversionCancelledException:
            print("conversion cancelled")
            # start next if there is any
            self._busy = False
        except (
            InvalidSpotifyLinkException,
            TrackNotFoundOnDeezerException,
            Exception,
        ) as e:
            self._busy = False
            print(e)
            print(type(e))
            print("krash i controller")
            print(e.message)

    def download(self, task_id: UUID) -> None:
        """Creates download tasks and starts downloading them"""
        print("start_download called")

        download_obj = self._download_queue[task_id]

        self._current_downloader = Downloader(
            self._deezer,
            download_obj,
            self._config,
            self._task_controller,
            self._dispatcher,
        )

        self._current_downloader.start()

        # if there are conversion objects in queue we start them after download is finished.
        self._busy = False
        self.start_next_conversion_task()

    def create_download(self, song_id: int):
        self._deezer_utils.create_download_obj()

    def search(self, query):
        return self._deezer_utils.search(query)

    def get_tasks(self) -> list[dict]:
        return self._task_controller.get_all_tasks()

    def subscribe(self, subscriber) -> None:
        self._dispatcher.subsribe(subscriber)

    def remove_task(self, task_id) -> None:
        self._task_controller.cancel_task(task_id)

    def remove_all_tasks(self) -> None:
        print("clearing queue")
        if downloader := self._current_downloader:
            downloader.restart_executor()
            self._currently_running = None

        self._converter.restart_executor()
        self._conversion_queue = Queue()
        self._task_controller.cancel_all()
        self._busy = False
