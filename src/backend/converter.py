import os
import re
from enum import Enum
from functools import partial
from concurrent.futures import ThreadPoolExecutor, CancelledError
from uuid import UUID

import spotipy
from spotipy.oauth2 import SpotifyOAuth
from spotipy.exceptions import SpotifyException
from spotipy.cache_handler import CacheFileHandler

from deezer import Deezer
from deezer.errors import DataException

from src.backend.exceptions import *
from src.backend.track_cache import Cache
from src.backend.models import *
from src.backend.configuration import Config
from src.backend.tasks import *
from src.backend.task_controller import TaskController
from src.backend.download_objects import *
from src.backend.exceptions import *
from src.backend.types import *

# https://open.spotify.com/playlist/5aKAA4aRjYqqhUfc2kypKH?si=e3d7ad4d57d84655&pt=7f8ec04af71e9b691f8fd87f29e20d3f
# https://open.spotify.com/playlist/32MEUCjETK4UurVG7m9fQf?si=03bdaf5fd6e3463e

DEBUG = True

redirect_url = "http://localhost:8888/callback/"
auth_url = "https://accounts.spotify.com/api/token"

# https://open.spotify.com/track/2UVSP6BlF8AgQOpzfDUVL2?si=53291ac0778a4ab8


class Converter:

    def __init__(self, dz: Deezer, config: Config, task_controller: TaskController):
        self.config: Config = config
        self.dz: Deezer = dz
        self.logged_in: bool = False
        self.cache: Cache = Cache()
        self.task_controller: TaskController = task_controller
        self.thread_executor = ThreadPoolExecutor(
            int(self.config.load_config()["concurrency_workers"])
        )

    def restart_executor(self):
        print("converter cancelled")
        self.thread_executor.shutdown(wait=False, cancel_futures=True)
        self.thread_executor = ThreadPoolExecutor(
            int(self.config.load_config()["concurrency_workers"])
        )

    def login(self):
        """Logins a user to spotify"""
        client_id = os.getenv("SPOTIFY_CLIENT_TOKEN")
        client_secret = os.getenv("SPOTIFY_SECRET_TOKEN")
        cache_folder = os.path.join(
            os.path.abspath(os.path.dirname(__file__)), "../..", "cache"
        )
        os.makedirs(cache_folder, exist_ok=True)
        cache_path = os.path.join(cache_folder, ".spotipy_cache")
        cache_handler = CacheFileHandler(cache_path=cache_path)
        try:
            self.sp = spotipy.Spotify(
                auth_manager=SpotifyOAuth(
                    client_id=client_id,
                    client_secret=client_secret,
                    redirect_uri=redirect_url,
                    scope="playlist-read-private",
                    cache_handler=cache_handler,
                )
            )

            user = self.sp.current_user()
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
        if DEBUG:
            print("@extract_link_id")
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

    def generate_download_obj(self, link: str, task_id: UUID):
        """generates a download object from a link (track, playlist, album)"""
        if DEBUG:
            print("@generate_download_obj")

        if "track" in link:
            return self.generate_track_download_obj(
                self.extract_link_id(link, DownloadType.TRACK), task_id
            )
        elif "playlist" in link:
            return self.generate_playlist_download_obj(
                self.extract_link_id(link, DownloadType.PLAYLIST), task_id
            )
        elif "album" in link:
            return self.generate_album_download_obj(
                self.extract_link_id(link, DownloadType.ALBUM), task_id
            )

    def generate_track_download_obj(self, link_id: str, task_id: UUID) -> Single:
        """generates a track download object"""
        if not link_id:
            raise InvalidSpotifyLinkException()

        if (track_data := self.sp.track(link_id)) is None:
            raise InvalidSpotifyLinkException()

        track = self.safe_convert_track(
            track_data, task_id
        )  # <- denna returnerar None när vanlig Exception fångas. Kolla varför den kastas.

        print(type(track))
        if isinstance(track, Track):
            _, task = self.task_controller.create_download_task(track)
        else:
            _, task = self.task_controller.create_download_task(
                error_obj=track, error=True
            )

        print(
            f"id: {track.id}, title: {track.title}, artist: {track.artist}, album: {track.album}"
        )

        return Single(task_id, track.id, track.title, track.artist, track.album, task)

    def generate_playlist_download_obj(self, link_id, task_id: UUID) -> Collection:
        """generates a playlist download object"""
        if DEBUG:
            print("@generate_playlist_download_obj")
        if link_id is None:
            raise InvalidSpotifyLinkException()
        # self.dz.api.get_artist(5080) sjuk cringe bild för 'various artists'

        # get initial data on playlist
        if (playlist := self.sp.playlist(link_id)) is None:
            raise InvalidSpotifyLinkException()

        # get all tracks (pagination)
        tracks_data = self.pull_tracks(playlist)

        spotify_tracks_data = []
        for item in tracks_data:
            if item["track"]:
                spotify_tracks_data.append(item["track"])

        collection = Collection(task_id, playlist["name"])
        collection.conversion_data = spotify_tracks_data

        return self.convert_tracks(collection, task_id)

    def generate_album_download_obj(self, link_id: str, task_id: UUID) -> Collection:
        """Generates an album download_obj."""

        if not link_id:
            raise InvalidSpotifyLinkException()

        # get initial album data from spotify
        if (album := self.sp.album(link_id)) is None:
            raise InvalidSpotifyLinkException()

        # create download_obj
        download_obj = Collection(task_id, album["name"])

        # get all tracks in case of pagination
        tracks_data = self.pull_tracks(album)

        # convert all tracks to regular spotify format
        tracks_data = [self.sp.track(track["id"]) for track in tracks_data]

        # conversion ready
        download_obj.conversion_data = tracks_data

        return self.convert_tracks(download_obj, task_id)

    def pull_tracks(self, data):
        tracks_temp = []
        tracks_temp.extend(data["tracks"]["items"])
        if data["tracks"]["next"]:
            next_page = self.sp.next(data["tracks"])
            tracks_temp.extend(next_page["items"])
            while next_page["next"]:
                next_page = self.sp.next(next_page)
                tracks_temp.extend(next_page["items"])

        return tracks_temp

    def convert_tracks(self, download_obj: Collection, task_id: UUID) -> Collection:
        # converts data from spotify to deezer
        if DEBUG:
            print("@convert")

        if self.task_controller.task_is_cancelled(task_id):
            raise ConversionCancelledException()

        tasks = []

        concurrency_workers = self.config.load_config()["concurrency_workers"]

        print(type(concurrency_workers))
        print(concurrency_workers)

        try:
            for track in self.thread_executor.map(
                partial(
                    self.safe_convert_track,
                    task_id=task_id,
                    size=len(download_obj.conversion_data),
                ),
                download_obj.conversion_data,
            ):
                if not self.task_controller.task_is_cancelled(task_id):
                    print(track.title)
                    if isinstance(track, Track):
                        _, task = self.task_controller.create_download_task(track=track)
                    else:
                        _, task = self.task_controller.create_download_task(
                            error_obj=track, error=True
                        )

                    tasks.append(task)

            download_obj.tasks = tasks
            download_obj.size = len(tasks)

            return download_obj
        except CancelledError as e:
            print(e)
            raise ConversionCancelledException()

    def safe_convert_track(self, track_data: dict, task_id: UUID, size: int = 1):

        try:
            return Track.parse_track(self.convert_track(track_data, task_id, size))
        except TrackNotFoundOnDeezerException as e:
            print(e)
            print(f"Track not found {track_data}")
            return ConversionError(
                track_data["id"],
                track_data["name"],
                track_data["artists"][0]["name"],
                track_data["album"]["name"],
            )
        except CancelledError as e:
            print(e)
            print("Conversion cancelled")
            raise ConversionCancelledException()

    def convert_track(self, track_data: dict, task_id: UUID, size: int = 1) -> dict:
        """Convert a track using ISRC or fallback to track metadata search."""

        if DEBUG:
            print("@convert_track")

        # Check if the task was cancelled early
        if self.task_controller.task_is_cancelled(task_id):
            print("conversion cancelled")
            raise ConversionCancelledException()

        print(track_data["name"])

        # Get the Spotify ID for caching purposes (currently not used)
        spotify_id = track_data["id"]

        try:
            # Try to find track by ISRC code first
            isrc = track_data["external_ids"]["isrc"]
            print(isrc)
            dz_track = self.dz.api.get_track_by_ISRC(isrc)

            if dz_track:
                # Update progress and return the found track
                self.task_controller.update_task_progress(task_id, (1 / size) * 100)
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
            self.task_controller.update_task_progress(task_id, (1 / size) * 100)
            return dz_track

        except TrackNotFoundOnDeezerException:
            print("Track not found on Deezer.")
            self.task_controller.update_task_progress(task_id, (1 / size) * 100)
            raise  # Reraise the exception after logging

        except Exception as e:
            print(f"Unexpected error during track conversion: {e}")
            self.task_controller.update_task_progress(task_id, (1 / size) * 100)
            raise TrackNotFoundOnDeezerException()  # Ensure a proper exception is raised if all else fails
