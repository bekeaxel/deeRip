from enum import Enum
from uuid import uuid4
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


class Task:
    def __init__(self, progress=0, state: State = State.PENDING):
        self.progress = progress
        self.state = state
        self.id = uuid4()
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
        track: Track = None,
        error_obj: ConversionError = None,
        error=False,
        progress=0,
        state: State = State.PENDING,
    ):
        self.track: Track = track
        self.error_obj = error_obj
        self.error = error
        super().__init__(progress, state)


class ConversionTask(Task):
    def __init__(self, link, progress=0, state: State = State.PENDING):
        self.link = link
        self.name = ""
        super().__init__(progress, state)
