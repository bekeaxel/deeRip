from abc import ABC, abstractmethod
import string, random

from src.backend.converter import Converter
from src.backend.task_controller import *
from src.backend.downloader import *
from src.backend.configuration import Config


def generate_random_id(length=8):
    characters = string.ascii_letters + string.digits
    return "".join(random.choice(characters) for _ in range(length))


class IJob(ABC):
    @abstractmethod
    def run(self):
        pass

    def __init__(self):
        self.id = generate_random_id()


class SpotifyJob(IJob):

    def __init__(
        self,
        task_id,
        dz: Deezer,
        dispather: MessageDispatcher,
        converter: Converter,
        task_controller: TaskController,
        config: Config,
    ):
        self.task_id = task_id  # conversion task id
        self.dz = dz
        self.dispatcher = dispather
        self.task_controller: TaskController = task_controller
        self.converter: Converter = converter
        self.config: Config = config
        self.cancelled = False
        super().__init__()

    def run(self):
        if self.task_controller.task_is_cancelled(self.task_id):
            return
        # start conversion task
        self.task_controller.start_task(self.task_id)

        # convert and create download tasks
        try:
            download_obj: IDownloadObject = self.converter.generate_download_obj(
                self.task_controller.get_task(self.task_id).link, self.task_id
            )
            self.task_controller.finish_task(self.task_id)

            # converting to DTO
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
                        "index": download_obj.task.index,
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
                            "index": task.index,
                        }
                        if not task.error
                        else {
                            "task_id": str(task.id),
                            "song_id": task.error_obj.id,
                            "title": task.error_obj.title,
                            "artist": task.error_obj.artist,
                            "album": task.error_obj.album,
                            "error": task.error,
                            "index": task.index,
                        }
                    )
                download_tasks.sort(key=lambda x: x.get("index"), reverse=True)

            # tell frontend to create download tasks
            self.dispatcher.publish_conversion_complete_message(
                self.task_id, download_tasks
            )

        # fånga alla olika exceptions här. låt de inte gå. Kanske skicak meddelande till frontend sen.

        except ConversionCancelledException:
            print("conversion cancelled")
            self.cancelled = True
        except (
            InvalidSpotifyLinkException,
            TrackNotFoundOnDeezerException,
            Exception,
        ) as e:
            self.cancelled = True

        if not self.cancelled:
            # download songs
            Downloader(
                self.dz,
                download_obj,
                self.config,
                self.task_controller,
                self.dispatcher,
            ).start()


class SearchDownloadJob(IJob):

    def __init__(
        self,
        download_obj: Single,
        dz: Deezer,
        dispather: MessageDispatcher,
        task_controller: TaskController,
        config: Config,
    ):
        self.download_obj = download_obj
        self.dz = dz
        self.dispatcher = dispather
        self.task_controller: TaskController = task_controller
        self.config: Config = config
        self.cancelled = False
        super().__init__()

    def run(self):
        Downloader(
            self.dz,
            self.download_obj,
            self.config,
            self.task_controller,
            self.dispatcher,
        ).start()


class SoundCloudJob(IJob):
    def start(self):
        print("job started")
