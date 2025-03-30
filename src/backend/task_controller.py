import threading
from uuid import UUID

from src.backend.tasks import *
from src.backend.message_dispatcher import MessageDispatcher
from src.frontend.messages import *


class TaskController:
    """Central unit for controlling all tasks. Sends updates to all watchers"""

    def __init__(self, dispatcher: MessageDispatcher):
        self._tasks: dict[str, Task] = {}
        self._lock = threading.Lock()
        self._dispatcher: MessageDispatcher = dispatcher

    def create_download_task(
        self, track=None, error_obj=None, error=False
    ) -> tuple[UUID, Task]:
        with self._lock:
            task = DownloadTask(track=track, error_obj=error_obj, error=error)
            self._tasks[task.id] = task
            return task.id, task

    def create_conversion_task(self, link) -> UUID:
        with self._lock:
            task = ConversionTask(link)
            self._tasks[task.id] = task
            self._dispatcher.publish_conversion_task_created_message(task.id)
            return task.id

    def task_is_done(self, task_id) -> bool:
        return (task := self._tasks.get(task_id)) and task.state == State.COMPLETE

    def task_is_cancelled(self, task_id) -> bool:
        return (task := self._tasks.get(task_id)) and task.state == State.CANCELLED

    def cancel_task(self, task_id) -> None:
        if task := self._tasks.get(task_id):
            task.cancel()

    def cancel_all(self) -> None:
        for task_id in self._tasks.keys():
            self.cancel_task(task_id)

    def increment_task_progress(self, task_id: UUID, progress: float) -> None:
        if task := self._tasks.get(task_id):
            task_progress = task.increment_progress(progress)
            self._dispatcher.publish_update_progress_message(
                task_id=task_id, progress=task_progress
            )

    def update_task_progress(self, task_id: UUID, progress: float) -> None:
        if task := self._tasks.get(task_id):
            task.set_progress(progress)
            self._dispatcher.publish_update_progress_message(
                task_id=task_id, progress=progress
            )

    def finish_task(self, task_id) -> None:
        if task := self._tasks.get(task_id):
            if isinstance(task, ConversionTask):
                self._tasks.pop(task_id)
            else:
                task.finish_task()

    def start_task(self, task_id) -> None:
        if task := self._tasks.get(task_id):

            task.start_task()

    def fail_task(self, task_id) -> None:
        if task := self._tasks.get(task_id):
            task.fail_task()
            self._dispatcher.publish_task_failed_message(task_id)

    def get_task(self, task_id) -> Task | None:
        return self._tasks.get(task_id)

    def get_all_tasks(self) -> list[dict]:
        tasks = []
        for task in self._tasks.values():
            if not task.state == State.CANCELLED:
                if isinstance(task, ConversionTask):
                    tasks.append(
                        {"task_id": str(task.id), "progress": task.get_progress()}
                    )
                elif isinstance(task, DownloadTask):
                    tasks.append(
                        {
                            "task_id": str(task.id),
                            "song_id": task.track.id,
                            "title": task.track.title,
                            "artist": task.track.artist.name,
                            "album": task.track.album.title,
                            "error": task.error,
                            "progress": task.progress,
                        }
                        if not task.error
                        else {
                            "task_id": str(task.id),
                            "song_id": task.error_obj.id,
                            "title": task.error_obj.title,
                            "artist": task.error_obj.artist,
                            "album": task.error_obj.album,
                            "error": task.error,
                        }
                    )

        tasks.reverse()
        return tasks
