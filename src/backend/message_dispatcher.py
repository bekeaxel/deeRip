from src.frontend.messages import *


class MessageDispatcher:

    def __init__(self):
        self._subscribers = []

    def subsribe(self, subscriber):
        self._subscribers.append(subscriber)

    def publish_conversion_task_created_message(self, task_id: UUID):
        self.publish(ConversionTaskCreatedMessage(str(task_id)))

    def publish_update_progress_message(self, task_id: UUID, progress):
        self.publish(ProgressUpdateMessage(str(task_id), progress))

    def publish_conversion_complete_message(self, task_id: UUID, tasks):
        self.publish(ConversionCompleteMessage(str(task_id), tasks))

    def publish_login_status_message(self, spotify: bool, deezer: bool):
        self.publish(LoginStatusMessage(spotify, deezer))

    def publish_task_failed_message(self, task_id: UUID):
        self.publish(TaskFailedMessage(str(task_id)))

    def publish(self, message):
        for subscriber in self._subscribers:
            subscriber.post_message(message)
