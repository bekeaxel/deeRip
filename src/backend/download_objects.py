from src.backend.tasks import *


class IDownloadObject:
    def __init__(self, conversion_id):
        self.conversion_id = conversion_id


class Single(IDownloadObject):
    def __init__(self, conversion_id, song_id, title, artist, album, task: Task):
        self.song_id = song_id  # spotify id or soundcloud id
        self.title = title
        self.artist = artist
        self.album = album
        self.task: DownloadTask = task
        self.size = 1
        super().__init__(conversion_id)

    def __str__(self):
        return f"Single({self.song_id}, {self.title}, {self.artist}, {self.album})"


class Collection(IDownloadObject):
    def __init__(self, conversion_id, title):
        self.tasks: list[DownloadTask] = []
        self.conversion_data = []
        self.title = title
        self.size = 0
        super().__init__(conversion_id)

    def __str__(self):
        return f"Collection({self.title}, {[str(task) for task in self.tasks]})"
