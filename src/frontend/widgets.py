from queue import Queue
from pathlib import Path
from typing import Iterable

from textual.reactive import reactive
from textual import events
from textual.widgets import *
from textual.containers import *
from textual.css.query import NoMatches
from textual import work, on

from src.frontend.messages import *
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
        if value := message.value.strip():
            self.app.post_message(SearchQueryRequestMessage(value))


class TaskViewer(Static):

    def __init__(self):
        self.controller: Controller = self.app.controller
        self.controller.subscribe(self)
        super().__init__()

    def compose(self):
        tasks: list[dict] = self.controller.get_tasks()
        components = []
        for task in tasks:
            if task.get("error", False):
                widget = ErrorWidget(
                    task_id=f"task_{task.get("task_id", "?")}",
                    song_id=task.get("song_id", "?"),
                    title=task.get("title", "?"),
                    artist=task.get("artist", "?"),
                    album=task.get("album", "?"),
                )
                components.append(widget)
            elif task.get("song_id", ""):
                widget = ProgressWidget(
                    task_id=f"task_{task.get('task_id', "?")}",
                    song_id=task.get("song_id", "?"),
                    title=task.get("title", "?"),
                    artist=task.get("artist", "?"),
                    album=task.get("album", "?"),
                    progress=task.get("progress", 0),
                )
                components.append(widget)
            else:
                widget = ProgressWidget(
                    task_id=f"task_{task.get('task_id', "?")}",
                    progress=task.get("progress", 0),
                    conversion=True,
                )
                components.append(widget)

        yield ListView(*components)

    # ---- Workers ----

    @work(thread=True)
    def create_download_tasks(self, task_id: str, songs: list[dict]):
        list_view = self.query_one(ListView)

        download_widgets = []
        for song in songs:
            if not song.get("error"):
                download_widgets.append(
                    ProgressWidget(
                        task_id=f"task_{song.get('task_id', "?")}",
                        song_id=song.get("song_id", "?"),
                        title=song.get("title", "?"),
                        artist=song.get("artist", "?"),
                        album=song.get("album", "?"),
                        progress=song.get("progress", 0),
                    )
                )
            else:
                download_widgets.append(
                    ErrorWidget(
                        task_id=f"task_{song.get("task_id", "?")}",
                        song_id=song.get("song_id", "?"),
                        title=song.get("title", "?"),
                        artist=song.get("artist", "?"),
                        album=song.get("album", "?"),
                    )
                )

        # remove conversion task
        self.app.call_from_thread(list_view.remove_children, f"#task_{task_id}")

        # render new widgets
        self.app.call_from_thread(list_view.insert, 0, download_widgets)

    @work(thread=True)
    def create_conversion_task(self, query):
        self.controller.create_job(query)

    @work(thread=True)
    def clear(self):
        self.controller.remove_all_tasks()
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
            pass  # nothing to be done, the widget is either not created yet or removed.

    @on(ConversionTaskCreatedMessage)
    def on_conversion_task_created(self, message: ConversionTaskCreatedMessage):
        self.query_one(ListView).insert(
            0, [ProgressWidget(f"task_{message.task_id}", conversion=True)]
        )

    @on(ConversionCompleteMessage)
    def on_conversion_complete(self, message: ConversionCompleteMessage):
        self.create_download_tasks(message.task_id, message.tasks)

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
    ):
        super().__init__(id=task_id)
        self.song_id: str = song_id
        self.title: str = title
        self.artist: str = artist
        self.album: str = album
        self.progress: int = progress
        self.conversion: bool = conversion

    def compose(self):
        components = [
            (
                Label(
                    self.format_label(self.title, self.artist, self.album),
                    classes="row-label",
                )
                if self.title
                else Label(f"Fixing shit in the backend...", classes="row-label")
            )
        ]

        bar = ProgressBar(total=100, show_eta=False, classes="progress-bar")
        bar.update(progress=self.progress)
        components.append(bar)

        yield Horizontal(*components)

    def format_label(self, title, artist, album):
        res = title
        if artist:
            res += f" - {artist}"
        if album:
            res += f" - {album}"

        return res

    def update_progress(self, progress):
        self.progress = progress
        self.query_one(ProgressBar).update(progress=progress)

    @on(events.Click)
    def on_widget_click(self, event: events.Click):
        from src.frontend.screens import TaskInfoScreen

        self.app.push_screen(TaskInfoScreen(self))


class ErrorWidget(ListItem):

    def __init__(self, task_id, song_id, title, artist, album):
        super().__init__(id=task_id)
        self.song_id: str = song_id
        self.title: str = title
        self.artist: str = artist
        self.album: str = album

    def compose(self):
        yield Horizontal(
            Label(
                f"{self.title} - {self.artist} - {self.album}",
                classes="row-label",
            )
        )


class FilteredDirectoryTree(DirectoryTree):

    def filter_paths(self, paths: Iterable[Path]) -> Iterable[Path]:
        return [path for path in paths if not path.name.startswith(".")]


class LoginHeader(Header):

    def __init__(self):
        super().__init__(show_clock=True)
        self.tall = True


class SearchResult(Static):

    def __init__(self, id, title, artist, album, duration, widths):
        super().__init__(id=id)
        self.title = title
        self.artist = artist
        self.album = album
        self.duration = duration
        self.widths = widths

    def trim(cls, s: str, w: int):
        return s.ljust(w) if len(s) <= w - 10 else f"{s[:w-10].strip()}...".ljust(w)

    def compose(self):
        yield Horizontal(
            Label(
                self.trim(self.title, self.widths[0])
                + self.trim(self.artist, self.widths[1])
                + self.trim(self.album, self.widths[2])
                + self.duration.rjust(self.widths[3]),
                classes="result-label",
            ),
            Button("⬇", id=f"d_{self.id}", classes="download-btn", tooltip="gieeet"),
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
        if results:
            self.app.call_from_thread(self.query_one(VerticalScroll).remove_children)
            self.results = results
            widths = self.get_widths(results)
            self.app.call_from_thread(
                self.mount,
                Label(
                    "         Title".ljust(widths[0])
                    + "         Artist".ljust(widths[1])
                    + "         Album".ljust(widths[2])
                    + "         Duration".rjust(widths[3]),
                    classes="column-label",
                ),
            )
            # yield column headers
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
        def width(key, max_chars):
            longest_chars = max([len(x[key]) for x in results]) + 20

            return min(longest_chars, max_chars)

        total_width = self.app.size.width - 40

        widths = [
            width("title", total_width // 3),
            width("artist", total_width // 3),
            width("album", total_width // 4),
        ]

        diff = total_width - sum(widths) - 5  # leaving room for duration column
        widths = [w + diff // 3 for w in widths]  # fill out empty space
        widths.append(
            max(max(total_width - sum(widths), 0), 5)
        )  # adding duration column

        return widths

    def to_display_time(cls, seconds):
        m = int(seconds / 60)
        s = seconds - m * 60

        if s < 10:
            return f"{m}:0{s}"
        else:
            return f"{m}:{s}"

    @work(thread=True)
    def create_job(self, song_id):
        self.controller.create_job(str(song_id))

    @on(Button.Pressed)
    def on_download_button_pressed(self, event: Button.Pressed):
        song_id = int(event.button.id.removeprefix("d_result_"))
        self.create_job(song_id)
