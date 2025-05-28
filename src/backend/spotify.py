import os
import re
from enum import Enum
from functools import partial
from concurrent.futures import ThreadPoolExecutor, CancelledError
from uuid import UUID
from pathlib import Path

import spotipy
from spotipy.oauth2 import SpotifyOAuth
from spotipy.exceptions import SpotifyException
from spotipy.cache_handler import CacheFileHandler

from deezer import Deezer
from deezer.errors import DataException

from src.backend.exceptions import *
from src.backend.models import *
from src.backend.configuration import Config
from src.backend.tasks import *
from src.backend.task_controller import TaskController
from src.backend.download_objects import *
from src.backend.exceptions import *
from src.backend.types import *

DEBUG = False
REDIRECT_URL = "http://127.0.0.1:8888/callback"


class SpotifyConverter:

    SPOTIFY_CLIENT_TOKEN = "SPOTIFY_CLIENT_TOKEN"
    SPOTIFY_SECRET_TOKEN = "SPOTIFY_SECRET_TOKEN"

    def __init__(self, dz: Deezer, config: Config, task_controller: TaskController):
        self.config: Config = config
        self.dz: Deezer = dz
        self.logged_in: bool = False
        self.task_controller: TaskController = task_controller
        self.thread_executor = ThreadPoolExecutor(
            int(self.config.load_config()["concurrency_workers"])
        )

    def restart_executor(self):
        self.thread_executor.shutdown(wait=False, cancel_futures=True)
        self.thread_executor = ThreadPoolExecutor(
            int(self.config.load_config()["concurrency_workers"])
        )

    def login(self):
        """Logins a user to spotify"""

        client_id = self.config.get_env_variable(self.SPOTIFY_CLIENT_TOKEN)
        client_secret = self.config.get_env_variable(self.SPOTIFY_SECRET_TOKEN)
        cache_path = Path.home() / ".deeRip" / ".spotipy_cache"
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        cache_handler = CacheFileHandler(cache_path=cache_path)
        try:
            self.sp = spotipy.Spotify(
                auth_manager=SpotifyOAuth(
                    client_id=client_id,
                    client_secret=client_secret,
                    redirect_uri=REDIRECT_URL,
                    scope="playlist-read-private",
                    cache_handler=cache_handler,
                )
            )
            self.logged_in = True
            return True
        except:
            self.logged_in = False
            return False

    def valid_url(cls, link: str):
        regex = r"https:\/\/open\.spotify\.com\/(playlist|track|album)\/[a-zA-Z0-9]+(?:\?si=[a-zA-Z0-9\-\_]+(?:&pt=[a-zA-Z0-9]+)?)?"
        return bool(re.match(regex, link))

    def extract_link_id(cls, url: str, type: DownloadType) -> str | None:
        """Extracts id of spotify link"""

        if type == DownloadType.TRACK:
            return (
                match.group(1)
                if (match := re.search(r"\/track\/([^?]+)", url))
                else None
            )
        elif type == DownloadType.PLAYLIST:
            return (
                match.group(1)
                if (match := re.search(r"\/playlist\/([^?]+)", url))
                else None
            )
        elif type == DownloadType.ALBUM:
            return (
                match.group(1)
                if (match := re.search(r"\/album\/([^?]+)", url))
                else None
            )

    def generate_download_obj(self, link: str, task_id: UUID) -> IDownloadObject:
        """generates a download object from a link (track, playlist, album)"""

        if "track" in link:
            return self._generate_track_download_obj(
                self.extract_link_id(link, DownloadType.TRACK), task_id
            )
        elif "playlist" in link:
            return self._generate_playlist_download_obj(
                self.extract_link_id(link, DownloadType.PLAYLIST), task_id
            )
        elif "album" in link:
            return self._generate_album_download_obj(
                self.extract_link_id(link, DownloadType.ALBUM), task_id
            )

    def _generate_track_download_obj(self, link_id: str, task_id: UUID) -> Single:
        """generates a track download object"""
        if not link_id:
            raise InvalidSpotifyLinkException()

        if (track_data := self.sp.track(link_id)) is None:
            raise InvalidSpotifyLinkException()

        track = self._safe_convert_track(
            track_data, task_id
        )  # <- denna returnerar None när vanlig Exception fångas. Kolla varför den kastas.

        if isinstance(track, Track):
            _, task = self.task_controller.create_download_task(
                track, conversion_task_id=task_id
            )
        else:
            _, task = self.task_controller.create_download_task(
                track=track, error=True, conversion_task_id=task_id
            )

        return Single(task_id, track.id, track.title, track.artist, track.album, task)

    def _generate_playlist_download_obj(self, link_id, task_id: UUID) -> Collection:
        """generates a playlist download object"""

        if link_id is None:
            raise InvalidSpotifyLinkException()
        # self.dz.api.get_artist(5080) sjuk cringe bild för 'various artists'

        # get initial data on playlist
        if (playlist := self.sp.playlist(link_id)) is None:
            raise InvalidSpotifyLinkException()

        # get all tracks (pagination)
        tracks_data = self._pull_tracks(playlist)

        spotify_tracks_data = []
        for item in tracks_data:
            if item["track"]:
                spotify_tracks_data.append(item["track"])

        collection = Collection(task_id, playlist["name"])
        collection.conversion_data = spotify_tracks_data

        return self._convert_tracks(collection, task_id)

    def _generate_album_download_obj(self, link_id: str, task_id: UUID) -> Collection:
        """Generates an album download_obj."""

        if not link_id:
            raise InvalidSpotifyLinkException()

        # get initial album data from spotify
        if (album := self.sp.album(link_id)) is None:
            raise InvalidSpotifyLinkException()

        # create download_obj
        download_obj = Collection(task_id, album["name"])

        # get all tracks in case of pagination
        tracks_data = self._pull_tracks(album)

        # convert all tracks to regular spotify format
        tracks_data = [self.sp.track(track["id"]) for track in tracks_data]

        # conversion ready
        download_obj.conversion_data = tracks_data

        return self._convert_tracks(download_obj, task_id)

    def _pull_tracks(self, data):
        tracks_temp = []
        tracks_temp.extend(data["tracks"]["items"])
        if data["tracks"]["next"]:
            next_page = self.sp.next(data["tracks"])
            tracks_temp.extend(next_page["items"])
            while next_page["next"]:
                next_page = self.sp.next(next_page)
                tracks_temp.extend(next_page["items"])

        return tracks_temp

    def _convert_tracks(self, download_obj: Collection, task_id: UUID) -> Collection:
        # converts data from spotify to deezer
        if self.task_controller.is_cancelled(task_id):
            raise ConversionCancelledException()

        tasks = []

        try:
            for track in self.thread_executor.map(
                partial(
                    self._safe_convert_track,
                    task_id=task_id,
                    size=len(download_obj.conversion_data),
                ),
                download_obj.conversion_data,
            ):
                if not self.task_controller.is_cancelled(task_id):
                    if isinstance(track, Track):
                        _, task = self.task_controller.create_download_task(
                            track=track, conversion_task_id=task_id
                        )
                    else:
                        _, task = self.task_controller.create_download_task(
                            track=track, error=True, conversion_task_id=task_id
                        )

                    tasks.append(task)

            download_obj.tasks = tasks
            download_obj.size = len(tasks)

            return download_obj
        except CancelledError as e:
            raise ConversionCancelledException()

    def _safe_convert_track(self, track_data: dict, task_id: UUID, size: int = 1):
        try:
            return Track.parse_track(self._convert_track(track_data, task_id, size))
        except TrackNotFoundOnDeezerException as e:
            return ConversionError(
                track_data["id"],
                track_data["name"],
                track_data["artists"][0]["name"],
                track_data["album"]["name"],
            )
        except CancelledError as e:
            raise ConversionCancelledException()
        except Exception as e:
            print(e)
            print("borde inte va här")

    def _convert_track(self, track_data: dict, task_id: UUID, size: int = 1) -> dict:
        """Convert a track using ISRC or fallback to track metadata search."""

        if DEBUG:
            print("@convert_track")

        # Check if the task was cancelled early
        if self.task_controller.is_cancelled(task_id):
            print("conversion cancelled")
            raise ConversionCancelledException()

        print(track_data["name"])

        try:
            # Try to find track by ISRC code first
            isrc = track_data["external_ids"]["isrc"]
            print(isrc)
            dz_track = self.dz.api.get_track_by_ISRC(isrc)

            if dz_track:
                # Update progress and return the found track
                self.task_controller.increment_task_progress(task_id, (1 / size) * 100)
                return dz_track
        except KeyError as e:
            print(f"Missing ISRC in track data: {e}")
        except DataException as e:
            print(f"Track not found with ISRC, trying name and artist: {e}")

        # Fallback: Search by track name and artist if ISRC is not available or invalid
        try:
            print(f"Trying name and artist for track: {track_data['name']}")
            artist_name = track_data["artists"][0]["name"]
            track_name = track_data["name"]
            album_name = track_data["album"]["name"]

            dz_track_id = self.dz.api.get_track_id_from_metadata(
                artist_name, track_name, album_name
            )

            if dz_track_id == "0":
                print("No track found with metadata search.")
                raise TrackNotFoundOnDeezerException()

            dz_track = self.dz.api.get_track(dz_track_id)
            self.task_controller.increment_task_progress(task_id, (1 / size) * 100)
            return dz_track

        except TrackNotFoundOnDeezerException:
            print("Track not found on Deezer.")
            self.task_controller.increment_task_progress(task_id, (1 / size) * 100)
            raise  # Reraise the exception after logging

        except Exception as e:
            print(f"Unexpected error during track conversion: {e}")
            self.task_controller.increment_task_progress(task_id, (1 / size) * 100)
            raise TrackNotFoundOnDeezerException()  # Ensure a proper exception is raised if all else fails
