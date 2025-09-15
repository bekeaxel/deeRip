from textual.message import Message

# Backend -> frontend messages


class ConversionTaskCreatedMessage(Message):
    def __init__(self, task_id: str):
        self.task_id: str = task_id
        super().__init__()


class ProgressUpdateMessage(Message):
    def __init__(self, task_id: str, progress: float):
        self.task_id: str = task_id
        self.progress = progress
        super().__init__()


class ConversionCompleteMessage(Message):
    def __init__(self, task_id: str, tasks: list):
        self.task_id: str = task_id
        self.tasks = tasks
        super().__init__()


class LoginStatusMessage(Message):
    def __init__(self, spotify, deezer):
        self.spotify = spotify
        self.deezer = deezer
        super().__init__()


class TaskFailedMessage(Message):
    def __init__(self, task_id: str):
        self.task_id: str = task_id
        super().__init__()


# frontend -> frontend messages


class SearchQueryRequestMessage(Message):
    def __init__(self, query: str):
        self.query = query
        super().__init__()


class ChooseDirectoryMessage(Message):
    def __init__(self, path: str):
        self.path: str = path
        self.bubble = False
        super().__init__()
