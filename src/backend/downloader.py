import requests
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from ssl import SSLError
from requests.exceptions import (
    ConnectionError as RequestsConnectionError,
    ReadTimeout,
    ChunkedEncodingError,
)
from urllib3.exceptions import SSLError as u3SSLError
import time
from requests.exceptions import MissingSchema
from typing import Optional

from deezer import Deezer
from deezer import DeezerError
from deemix.utils import crypto

from src.backend.models import Track
from src.backend.exceptions import *
from src.backend.tagger import tag_file
from src.backend.configuration import Config
from src.backend.task_controller import TaskController
from src.backend.message_dispatcher import MessageDispatcher
from src.backend.download_objects import *

USER_AGENT_HEADER = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/79.0.3945.130 Safari/537.36"
)


class Downloader:

    def __init__(
        self,
        dz: Deezer,
        download_obj: IDownloadObject,
        config: Config,
        task_controller: TaskController,
        dispatcher: MessageDispatcher,
    ):
        self.dz: Deezer = dz
        self.config: Config = config
        self.__download_obj: IDownloadObject = download_obj
        self.task_controller: TaskController = task_controller
        self.dispatcher: MessageDispatcher = dispatcher
        self.thread_executor = ThreadPoolExecutor(
            int(self.config.load_config()["concurrency_workers"])
        )

    def start(self):
        """start downloading a download_obj"""
        # check if d_obj is single track, album or playlist - start with playlist

        if isinstance(self.__download_obj, Single):
            self.download(self.__download_obj.task)

        elif isinstance(self.__download_obj, Collection):
            # sending all downloads to pool
            self.__download_obj.tasks.reverse()
            results = list(
                self.thread_executor.map(self.download, self.__download_obj.tasks)
            )
            self.handle_playlist_download(results)

    def download(self, task: DownloadTask):
        try:
            self._download(task)
        except DownloadException as e:
            print(e.message)
            self.task_controller.fail_task(task.id)

    def _download(self, task: DownloadTask):
        """Downloads a track to disk. This method can be run in parallell"""

        # downloads a given download object, playlist info is in self.download_obj
        if (
            task.error
            or self.task_controller.is_cancelled(task.id)
            or self.task_controller.failed(task.id)
        ):
            return
        print(f"started download of {task}")
        config = self.config.load_config()
        track = task.track

        if isinstance(self.__download_obj, Collection):
            playlist_name = self.__download_obj.title
            download_folder = Path(config["download_folder"]) / playlist_name
        else:
            download_folder = Path(config["download_folder"])

        # return if we don't want to override downloads
        if download_folder.exists() and not config["download_override"]:
            # TODO: borde faila tasken istället för att den ska bli färdig
            self.task_controller.update_task_progress(task.id, 100)
            return

        # Create download folder if it does not exist
        download_folder.mkdir(parents=True, exist_ok=True)

        # Get streaming url
        download_url = self.get_download_url(track, config["bit_rate"])

        if download_url is None:
            raise DownloadException(
                f"Track token expired for song {track.title} by {track.artist.name}"
            )

        # Creating full download path
        extension = self.get_extension()
        file_path = download_folder / (track.title + extension)

        # stream track to file

        self.stream_track_to_file(
            track=track,
            task_id=task.id,
            path=file_path,
            url=download_url,
        )

        # download image to file
        image = self.download_image(track)

        # tag file
        tag_file(track, file_path, image)
        print("download complete")

    def stream_track_to_file(self, track: Track, task_id, path: str, url: str):
        """Downloads song content to file"""

        if False:
            self.task_controller.update_task_progress(task_id, 100)
            return

        headers = {"User-Agent": USER_AGENT_HEADER}

        try:
            with requests.get(url, headers=headers, stream=True, timeout=10) as request:
                request.raise_for_status()
                blowfish_key = crypto.generateBlowfishKey(str(track.id))

                content_length = int(request.headers.get("Content-length", 0))

                if request.headers["Content-length"] == 0:
                    raise

                with open(path, "wb") as outputStream:
                    downloaded = 1  # stops at 99% if 0
                    temp = 1
                    for chunk in request.iter_content(2048 * 3):
                        if chunk:
                            if len(chunk) >= 2048:
                                chunk = (
                                    crypto.decryptChunk(blowfish_key, chunk[0:2048])
                                    + chunk[2048:]
                                )

                            outputStream.write(chunk)

                            temp += len(chunk) / content_length * 100
                            if int(temp - downloaded) >= 1:
                                downloaded = int(temp)
                                self.task_controller.update_task_progress(
                                    task_id, downloaded
                                )

        except (SSLError, u3SSLError):
            self.stream_track_to_file(track, task_id, path, url)
        except (RequestsConnectionError, ReadTimeout, ChunkedEncodingError):
            time.sleep(2)
            self.stream_track_to_file(track, task_id, path, url)
        except (MissingSchema, Exception):
            raise DownloadException("Fail during stream")

    def download_image(self, track: Track):
        """Downloads the image from deezer"""
        headers = {"User-Agent": USER_AGENT_HEADER}
        url = track.album.cover_big

        request = requests.get(url, headers=headers)
        request.raise_for_status()

        return request.content

    def get_download_url(self, track: Track, bitrate) -> Optional[str]:
        """Gets the stream link from deezer"""
        try:
            return self.dz.get_track_url(track.track_token, bitrate)
        except DeezerError as e:
            return None

    def handle_playlist_download(self, results):
        print("download complete!")

    def get_extension(self):
        match self.config.load_config()["bit_rate"]:
            case "MP3_128" | "MP3_320":
                return ".mp3"
            case "FLAC":
                return ".FLAC"
