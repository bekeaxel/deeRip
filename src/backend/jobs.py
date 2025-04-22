from abc import ABC, abstractmethod
import string, random

from src.backend.spotify import SpotifyConverter
from src.backend.sc import SoundCloudClient
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
        task_id: UUID,
        url: str,
        dz: Deezer,
        dispather: MessageDispatcher,
        converter: SpotifyConverter,
        task_controller: TaskController,
        config: Config,
    ):
        self.task_id: UUID = task_id  # conversion task id
        self.url: str = url
        self.dz: Deezer = dz
        self.dispatcher: MessageDispatcher = dispather
        self.task_controller: TaskController = task_controller
        self.converter: SpotifyConverter = converter
        self.config: Config = config
        self.cancelled = False
        super().__init__()

    def __str__(self):
        return f"spotify job, conversion task: {self.task_id}, url: {self.url}"

    def run(self):
        if self.task_controller.is_cancelled(self.task_id):
            return
        # start conversion task
        self.task_controller.start_task(self.task_id)

        # convert and create download tasks
        try:
            download_obj: IDownloadObject = self.converter.generate_download_obj(
                self.task_controller.get_task(self.task_id).url, self.task_id
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

    def __str__(self):
        return f"Search job, download_obj: {self.download_obj}"

    def run(self):
        Downloader(
            self.dz,
            self.download_obj,
            self.config,
            self.task_controller,
            self.dispatcher,
        ).start()


class SoundCloudJob(IJob):
    def __init__(
        self,
        conversion_task_id: UUID,
        sc: SoundCloudClient,
        dispather: MessageDispatcher,
        task_controller: TaskController,
        config: Config,
    ):
        self.conversion_task_id: UUID = conversion_task_id  # conversion task id
        self.sc: SoundCloudClient = sc
        self.dispatcher: MessageDispatcher = dispather
        self.task_controller: TaskController = task_controller
        self.config: Config = config
        self.cancelled = False
        super().__init__()

    def __str__(self):
        return f"Soundcloud job, conversion task: {self.conversion_task_id}"

    def run(self):
        print("sc job started")

        if self.task_controller.is_cancelled(self.conversion_task_id):
            return

        try:
            self.task_controller.start_task(self.conversion_task_id)
            download_obj: IDownloadObject = self.sc.generate_download_obj(
                self.conversion_task_id
            )
            self.task_controller.finish_task(self.conversion_task_id)
            # converting to DTO
            download_tasks = []

            if isinstance(download_obj, Single):

                download_tasks.append(
                    {
                        "task_id": str(download_obj.task.id),
                        "song_id": download_obj.song_id,
                        "title": download_obj.title,
                        "artist": download_obj.artist,
                        "album": "",
                        "error": download_obj.task.error,
                        "index": download_obj.task.index,
                    }
                )
            elif isinstance(download_obj, Collection):
                for task in download_obj.tasks:
                    download_tasks.append(
                        {
                            "task_id": str(task.id),
                            "song_id": "sc",
                            "title": task.track.title,
                            "artist": task.track.artist,
                            "album": "",
                            "error": task.error,
                            "index": task.index,
                        }
                    )

            download_tasks.sort(key=lambda x: x.get("index"), reverse=True)
            self.dispatcher.publish_conversion_complete_message(
                self.conversion_task_id, download_tasks
            )

            print(f"tasks after conversion {download_tasks}")

        except SoundCloudError as e:
            print(f"error: {e.message}")
            self.task_controller.fail_task(self.conversion_task_id)
            self.cancelled = True
            return

        if not self.cancelled:
            try:
                self.sc.download(download_obj)
            except SoundCloudError as e:
                print("should not be caught here")

        # convert tracks (conversion task)
        # dowload tracks (download tasks)
        # snacka med frontend skicka
