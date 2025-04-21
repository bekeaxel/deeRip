from enum import Enum
from uuid import uuid4, UUID
import threading

from src.backend.models import *
from src.backend.exceptions import *

EPSILON = 99.99


class State(Enum):
    PENDING = 1
    RUNNING = 2
    COMPLETE = 3
    CANCELLED = 4
    FAILED = 5
    CREATED = 6


class Task:
    def __init__(self, index, progress=0, state: State = State.CREATED):
        self.index = index
        self.progress = progress
        self.state = state
        self.id: UUID = uuid4()
        self.lock = threading.Lock()
        self.is_cancelled = False

    def increment_progress(self, progress):
        """Increment progress of task by progress"""
        with self.lock:
            self.progress += progress
            if self.progress > EPSILON:
                self.state = State.COMPLETE
            return self.progress

    def set_progress(self, progress):
        """Set progress of task to progress"""
        with self.lock:
            self.progress = progress
            if self.progress >= 99:
                self.state = State.COMPLETE

    def get_progress(self):
        with self.lock:
            return self.progress

    def finish_task(self):
        with self.lock:
            self.state = State.COMPLETE

    def start_task(self):
        with self.lock:
            self.state = State.RUNNING

    def queue_task(self):
        with self.lock:
            self.state = State.PENDING

    def fail_task(self):
        with self.lock:
            self.state = State.FAILED

    def cancel(self):
        with self.lock:
            self.state = State.CANCELLED


class DownloadTask(Task):
    def __init__(
        self,
        index,
        track: Track | SoundCloudTrack = None,
        error_obj: ConversionError = None,
        error=False,
        progress=0,
        state: State = State.CREATED,
        conversion_task_id: UUID = None,
    ):
        self.track: Track | SoundCloudTrack = track
        self.error_obj = error_obj
        self.error = error
        self.conversion_task_id = conversion_task_id
        super().__init__(index, progress, state)

    def __str__(self):
        return (
            f"d_task - task_id={self.id}, progress={self.progress}, state={self.state}, track={self.track}"
            if self.state != State.FAILED
            else f"d_task - task_id={self.id}, progress={self.progress}, state={self.state}, track={self.error_obj}"
        )


class ConversionTask(Task):
    def __init__(self, url, index, progress=0, state: State = State.CREATED):
        self.url = url
        self.name = ""
        super().__init__(index, progress, state)

    def __str__(self):
        return (
            f"c_task - task_id={self.id}, progress={self.progress}, state={self.state}"
        )
