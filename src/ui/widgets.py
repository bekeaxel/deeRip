from queue import Queue
from pathlib import Path
from typing import Iterable

from textual.widget import Widget
from textual.reactive import reactive
from textual.widget import Widget
from textual.widgets import *
from textual.containers import *
from textual.css.query import NoMatches
from textual import work, on

from src.ui.messages import *
from src.backend.exceptions import *
from src.backend.main_controller import Controller

EPSILON = 99.99


class SearchBar(Static):

    def __init__(self, id=None, classes=None):
        super().__init__(id=id, classes=classes)

    def compose(self):
        yield Input(
            placeholder="rip it?",
            select_on_focus=False,
            tooltip="Spotify link or whatever",
        )

    def set_value(self, value: str):
        self.query_one(Input).value = value

    @on(Input.Submitted)
    async def on_input_submitted(self, message: Input.Submitted):
        self.app.post_message(SearchQueryRequestMessage(message.value))


class TaskViewer(Static):

    def __init__(self):
        self.controller: Controller = self.app.controller
        self.controller.subscribe(self)
        self.tasks: list[str] = []
        self.conversion_in_progress = False
        super().__init__()

    def compose(self):
        components = [
            (
                ProgressWidget(
                    task_id=f"task_{task['task_id']}",
                    song_id=task["song_id"],
                    title=task["title"],
                    artist=task["artist"],
                    album=task["album"],
                    progress=task["progress"],
                )
                if "song_id" in task
                else ProgressWidget(
                    task_id=f"task_{task['task_id']}",
                    progress=task["progress"],
                    conversion=True,
                )
            )
            for task in self.controller.get_tasks()
        ]
        yield ListView(*components)

    # ---- Workers ----
    @work(thread=True)
    def create_download_tasks(self, task_id: str, tasks):
        list_view = self.query_one(ListView)

        i = 1
        download_widgets = []
        for task in tasks:
            if not task.get("error"):
                download_widgets.append(
                    ProgressWidget(
                        task_id=f"task_{task['task_id']}",
                        song_id=task["song_id"],
                        title=task["title"],
                        artist=task["artist"],
                        album=task["album"],
                        index=i,
                    )
                )
            else:
                print(f"in widget: {task}")
                download_widgets.append(
                    ErrorWidget(
                        task_id=f"task_{task['task_id']}",
                        song_id=task["song_id"],
                        title=task["title"],
                        artist=task["artist"],
                        album=task["album"],
                        index=i,
                    )
                )
            i += 1

        # remove conversion task
        self.app.call_from_thread(list_view.remove_children, f"#task_{task_id}")

        for task in tasks:
            self.tasks.append(task["task_id"])

        self.app.call_from_thread(list_view.insert, 0, download_widgets)

        # for widget in download_widgets:
        #     self.app.call_from_thread(container.mount, widget)

        self.post_message(DownloadTasksCreatedMessage(task_id))

    @work(thread=True)
    def create_conversion_task(self, query):
        task_id = self.controller.create_conversion_task(query)
        self.tasks.append(task_id)
        self.app.call_from_thread(
            self.query_one(ListView).insert,
            0,
            [ProgressWidget(f"task_{task_id}", conversion=True)],
        )

    @work(thread=True)
    def start_download(self, task_id):
        self.controller.download(task_id)

    @work(thread=True)
    def clear(self):
        self.controller.remove_all_tasks()
        # for task_id in self.tasks:
        #     self.controller.remove_task(UUID(task_id))
        self.tasks = []
        container = self.query_one(VerticalScroll)
        self.app.call_from_thread(container.remove_children, ProgressWidget)
        self.app.call_from_thread(container.remove_children, ErrorWidget)

    # ---- Messages Handlers ----
    @on(ProgressUpdateMessage)
    def on_progress_update(self, message: ProgressUpdateMessage):
        try:
            self.query_one(f"#task_{message.task_id}", ProgressWidget).update_progress(
                message.progress
            )
        except NoMatches:
            pass  # nothing to be done, the widget is probably already removed.

    @on(ConversionCompleteMessage)
    def on_conversion_complete(self, message: ConversionCompleteMessage):
        print("ConversionComplete fångad i frontend")
        self.create_download_tasks(message.task_id, message.tasks)

    @on(DownloadTasksCreatedMessage)
    def on_download_tasks_created(self, message: DownloadTasksCreatedMessage):
        print("starting download")
        print(type(message.task_id))
        self.start_download(UUID(message.task_id))

    @on(Button.Pressed)
    def on_button_pressed(self, event: Button.Pressed):
        task_id = event.button.id.removeprefix("remove_task_")
        print(f"ta bort {task_id}")
        print(self.tasks)
        self.tasks.remove(task_id)
        self.controller.remove_task(UUID(task_id))
        self.query_one(VerticalScroll).remove_children(f"#task_{task_id}")

    @on(TaskFailedMessage)
    def on_task_failed(self, message: TaskFailedMessage):
        self.query_one(f"#task_{message.task_id}", ProgressWidget).styles.background = (
            "#a65454"
        )


class ProgressWidget(ListItem):
    """A row widget for tracking a song download progress."""

    progress = reactive(0)

    def __init__(
        self,
        task_id,
        song_id=None,
        title=None,
        artist=None,
        album=None,
        progress=0,
        conversion=False,
        index=0,
    ):
        super().__init__(id=task_id)
        self.song_id = song_id
        self.title = title
        self.artist = artist
        self.album = album
        self.progress = progress
        self.conversion = conversion
        self.index = index

    def compose(self):
        components = [
            (
                Label(f"{self.index}. {self.title}", classes="row-label")
                if self.title
                else Label(f"Converting songs...", classes="row-label")
            )
        ]

        components.append(
            ProgressBar(total=100, show_eta=False, classes="progress-bar")
        )

        yield Horizontal(*components)

    def update_progress(self, progress):
        self.query_one(ProgressBar).update(
            progress=100 if progress > EPSILON else progress
        )


class ErrorWidget(ListItem):

    def __init__(self, task_id, song_id, title, artist, album, index=0):
        super().__init__(id=task_id)
        self.song_id = song_id
        self.title = title
        self.artist = artist
        self.album = album
        self.index = index

    def compose(self):
        yield Horizontal(
            Label(
                f"{self.index}. {self.title} by {self.artist} from {self.album}",
                classes="row-label",
            ),
            Button(
                "remove",
                variant="default",
                id=f"remove_{self.id}",
                classes="remove-btn",
            ),
        )


class FilteredDirectoryTree(DirectoryTree):

    def filter_paths(self, paths: Iterable[Path]) -> Iterable[Path]:
        return [path for path in paths if not path.name.startswith(".")]


class LoginHeader(Header):

    def __init__(self):
        super().__init__()
        self.tall = True


class SearchResult(Static):

    def __init__(self, id, title, artist, album, duration, widths):
        super().__init__(id=id)
        self.title = title
        self.artist = artist
        self.album = album
        self.duration = duration
        self.widths = widths

    def compose(self):
        yield Horizontal(
            Label(
                self.title.ljust(self.widths[0])
                + self.artist.ljust(self.widths[1])
                + self.album.ljust(self.widths[2])
                + self.duration.rjust(self.widths[3]),
                classes="result-label",
            ),
            Button("download", id=f"d_{self.id}", classes="download-btn"),
            classes="result-row",
        )


class SearchResultView(Static):

    def __init__(self):
        self.controller: Controller = self.app.controller
        self.controller.subscribe(self)
        self.results = []
        super().__init__()

    def compose(self):
        yield VerticalScroll()

    @work(thread=True)
    def add_results(self, results):
        self.results = results
        widths = self.get_widths(results)
        for result in results:
            self.app.call_from_thread(
                self.query_one(VerticalScroll).mount,
                SearchResult(
                    f"result_{result["id"]}",
                    result["title"],
                    result["artist"],
                    result["album"],
                    self.to_display_time(result["duration"]),
                    widths=widths,
                ),
            )

    def get_widths(self, results):
        def width(key):
            return max([len(x[key]) for x in results]) + 10

        return [width("title"), width("artist"), width("album"), 5]

    def to_display_time(cls, seconds):
        m = int(seconds / 60)
        s = seconds - m * 60

        if s < 10:
            return f"{m}:0{s}"
        else:
            return f"{m}:{s}"

    @on(Button.Pressed)
    def on_download_button_pressed(self, event: Button.Pressed):
        song_id = int(event.button.id.removeprefix("d_result_"))
        self.controller.create_download_task(song_id)
