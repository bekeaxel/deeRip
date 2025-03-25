from deezer import Deezer

from src.backend.models import *
from src.backend.download_objects import Single
from src.backend.task_controller import TaskController
from src.backend.message_dispatcher import MessageDispatcher


class DeezerUtils:

    def __init__(self, dz: Deezer, task_controller: TaskController, dispatcher):
        self.dz: Deezer = dz
        self.task_controller: TaskController = task_controller
        self.dispatcher: MessageDispatcher = dispatcher

    def search(self, query: str) -> list[dict]:
        return [
            {
                "id": r["id"],
                "title": r["title"],
                "artist": r["artist"]["name"],
                "album": r["album"]["title"],
                "duration": r["duration"],
            }
            for r in self.dz.api.search(query)["data"]
        ]

    def create_download_obj(self, id):
        dz_track = self.dz.api.get_track(id)
        track = Track.parse_track(dz_track)
        _, task = self.task_controller.create_download_task(track=track)

        return Single(None, track.id, track.title, track.artist, track.album, task)
