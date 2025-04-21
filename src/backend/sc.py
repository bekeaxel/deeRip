from pathlib import Path
import re
import requests
from bs4 import BeautifulSoup
from uuid import UUID
from concurrent.futures import ThreadPoolExecutor

from src.backend.exceptions import SoundCloudError
from src.backend.models import SoundCloudTrack, SoundCloudPlaylist
from src.backend.task_controller import TaskController
from src.backend.configuration import Config
from src.backend.download_objects import *
from src.backend.tasks import *
from src.backend.tagger import tag_file

BASE_URL_SOUNDCLOUD = "https://soundcloud.com"
BASE_URL_SOUNDCLOUD_TRACK = (
    "https://api-v2.soundcloud.com/tracks/TRACK_ID?client_id=CLIENT_ID"
)
JS_EXTENSION = ".js"
MP3_EXTENSION = ".mp3"
SC_CLIENT_ID = "SC_CLIENT_ID"
HEADERS = {"User-Agent": "Mozilla/5.0"}


class SoundCloudClient:

    session = requests.Session()

    def __init__(self, task_controller: TaskController, config: Config):
        self.task_controller: TaskController = task_controller
        self.config: Config = config
        self.client_id = self.config.get_env_variable(SC_CLIENT_ID)
        self.thread_executor = ThreadPoolExecutor(
            int(self.config.load_config()["concurrency_workers"])
        )

    def valid_url(cls, link) -> bool:
        regex = r"https:\/\/soundcloud.com\/"
        return bool(re.match(regex, link))

    def generate_download_obj(self, task_id: UUID) -> IDownloadObject:

        task: ConversionTask = self.task_controller.get_task(task_id)

        # parse soundcloud track
        obj = self.resolve_url(task.url, task_id)

        print(obj)
        if isinstance(obj, SoundCloudTrack):
            return self.generate_track_download_obj(obj, task_id)
        elif isinstance(obj, SoundCloudPlaylist):
            return self.generate_playlist_download_obj(obj, task_id)
        else:
            raise SoundCloudError("Could not parse object")

    def generate_track_download_obj(self, track: SoundCloudTrack, task_id: UUID):
        track.progressive_mp3_streaming_url = self.get_streaming_url_for_track(track)

        _, download_task = self.task_controller.create_download_task(
            track, conversion_task_id=task_id
        )
        self.task_controller.increment_task_progress(task_id, 100)
        return Single(task_id, "sc", track.title, track.artist, None, download_task)

    def generate_playlist_download_obj(
        self, playlist: SoundCloudPlaylist, task_id: UUID
    ):
        collection = Collection(task_id, playlist.title)
        collection.size = len(playlist.tracks)

        for track in playlist.tracks:
            track.progressive_mp3_streaming_url = self.get_streaming_url_for_track(
                track
            )
            _, download_task = self.task_controller.create_download_task(
                track, conversion_task_id=task_id
            )
            collection.tasks.append(download_task)
            self.task_controller.increment_task_progress(
                task_id, (1 / (collection.size * 2)) * 100
            )

        return collection

    def fetch_client_id(self):
        """Scrapes client id from SoundCloud"""
        resp = self.session.get(BASE_URL_SOUNDCLOUD)
        soup = BeautifulSoup(resp.text, "html.parser")

        for script in soup.find_all("script", src=True):
            if "a-v2" in script["src"] and (src := script["src"]).endswith(
                JS_EXTENSION
            ):
                js = self.session.get(src).text
                match = re.search(r'client_id["=:]\s*"?([a-zA-Z0-9]{32})"?', js)
                if match:
                    return match.group(1)

        return "-1"

    def format_url(cls, sc_url, client_id):
        """Formats the given url to a callable url"""
        prefix = "https://api-v2.soundcloud.com/resolve?url="
        suffix = f"&client_id={client_id}"

        return prefix + sc_url + suffix

    def try_get(self, url, task_id: UUID, fn: callable):
        try:
            return fn(url, task_id)
        except Exception:
            print("sound cloud client id expired. Fetching new")
            self.client_id = self.fetch_client_id()
            if self.client_id == "-1":
                raise SoundCloudError("Error fetching client id")
            self.config.update_env_variable(SC_CLIENT_ID, self.client_id)
            return self.try_get(url, fn)

    def resolve_url(self, url, task_id: UUID):
        """Calls SoundCloud API getting info on object"""
        return self.try_get(url, task_id, self._resolve_url)

    def _resolve_url(self, url, task_id: UUID):
        """Calls SoundCloud API getting info on object"""
        full_url = self.format_url(url, self.client_id)
        print(f"url = {full_url}")
        response = self.session.get(full_url, headers=HEADERS, timeout=10)
        response.raise_for_status()
        print(f"reponse before json: {response.content}")
        data: dict = response.json()
        if data.get("kind") == "track":
            return SoundCloudTrack.parse_track(data)
        elif data.get("kind") == "playlist":
            data = self._resolve_all(data, task_id)
            return SoundCloudPlaylist.parse_playlist(data)

    def _resolve_all(self, data: dict, task_id: UUID):

        ids = [track.get("id") for track in data.get("tracks")]
        size = len(ids)
        tracks = []

        for id in ids:
            url = BASE_URL_SOUNDCLOUD_TRACK.replace("TRACK_ID", str(id)).replace(
                "CLIENT_ID", self.client_id
            )
            response = self.session.get(url, headers=HEADERS, timeout=10)
            tracks.append(response.json())
            self.task_controller.increment_task_progress(task_id, 1 / (2 * size) * 100)

        return {"title": data.get("title"), "tracks": tracks}

    def get_streaming_url_for_track(self, track: SoundCloudTrack):
        """Get streaming url for track"""
        for transcoding in track.transcodings:
            if transcoding.get("format").get("protocol") == "progressive":
                url = transcoding.get("url")
                return self.try_get(url, None, self._get_streaming_url_for_track)

    def _get_streaming_url_for_track(self, url, task_id):
        """Private method for getting streaming url for track"""
        full_url = url + f"?client_id={self.client_id}"
        r = requests.get(full_url, headers=HEADERS, timeout=10)
        r.raise_for_status()
        data = r.json()
        return data["url"]

    def download(self, download_obj: IDownloadObject):
        """Download a download_obj"""
        if isinstance(download_obj, Single):
            self.download_track(download_obj)
        elif isinstance(download_obj, Collection):
            self.download_playlist(download_obj)
        else:
            raise SoundCloudError("Wrong type of IDownloadObject")

    def download_track(self, download_obj: Single):
        """Download a Single"""
        task = download_obj.task

        if task.is_cancelled:
            raise SoundCloudError("Download task cancelled")

        self._download_track(task.track, task.id)

    def _download_track(self, track: SoundCloudTrack, task_id: UUID):
        """Downloads a SoundCloudTrack"""
        if self.task_controller.is_cancelled((task_id)):
            # should not fail cancelled task, just stop downloading
            return

        try:
            print(f"started download of {track.title}")
            self.task_controller.start_task(task_id)

            config = self.config.load_config()

            # get path
            download_folder = config["download_folder"]
            path = download_folder + "/" + track.title + MP3_EXTENSION

            # check if download is allowed
            if Path(path).exists() and not config["download_override"]:
                raise SoundCloudError("File with given path already exists")

            # create file
            Path(download_folder).mkdir(parents=True, exist_ok=True)

            # stream to file
            self.stream_to_disk(track.progressive_mp3_streaming_url, path, task_id)

            # tag file
            image = self.download_image(track.image_url)
            self.tag_file(track, path, image)

        except:
            self.task_controller.fail_task(task_id)

    def download_playlist(self, download_obj: Collection):
        """Download a SoundCloudPlaylist"""
        for task in download_obj.tasks:
            self.thread_executor.submit(self._download_track, task.track, task.id)

    def download_image(self, image_url):
        """Download image from url"""
        try:
            response = self.session.get(image_url, headers=HEADERS, timeout=10)
            response.raise_for_status()
            return response.content
        except Exception:
            raise SoundCloudError("Error while downloading image")

    def tag_file(self, track, path, image):
        try:
            tag_file(track, path, image)
        except Exception:
            raise SoundCloudError("Error while tagging image")

    def stream_to_disk(self, stream_url, path, task_id: UUID):
        """Stream a url to disk"""
        try:
            with self.session.get(stream_url, stream=True, timeout=10) as response:
                response.raise_for_status()
                content_length = int(response.headers.get("Content-length", 0))

                if content_length == 0:
                    raise SoundCloudError("Response while streaming is empty")

                with open(path, "wb") as output_stream:
                    downloaded = 1  # stops at 99% if 0
                    temp = 1
                    for chunk in response.iter_content(2048 * 3):
                        if chunk:
                            output_stream.write(chunk)

                            temp += len(chunk) / content_length * 100
                            if int(temp - downloaded) >= 1:
                                downloaded = int(temp)
                                self.task_controller.update_task_progress(
                                    task_id, downloaded
                                )
        except Exception:
            raise SoundCloudError("Error while streaming track")
