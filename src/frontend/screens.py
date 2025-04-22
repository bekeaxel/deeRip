import os

from textual.screen import Screen, ModalScreen
from textual import on
from textual.widgets import (
    Footer,
    Button,
    Label,
    Select,
    DirectoryTree,
    Switch,
    Input,
    MaskedInput,
)
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import *
from textual.validation import Integer, Length
from textual.events import Blur

from src.frontend.messages import *
from src.backend.main_controller import Controller
from src.backend.configuration import Config
from src.frontend.widgets import *


class HomeScreen(Screen):
    CSS_PATH = "styles/screens.tcss"

    BINDINGS = [
        Binding("d", "app.push_screen('downloads')", "Downloads"),
        Binding("s", "app.push_screen('search')", "Search"),
        Binding("p", "app.push_screen('settings')", "Settings"),
    ]

    def compose(self) -> ComposeResult:
        yield LoginHeader()
        yield Container(SearchBar(id="search-bar-home"), classes="home-container")

        yield Footer(show_command_palette=False)
        yield Button("", id="focus_sink", classes="focus-sink")  # focus sink

    def _on_screen_resume(self):
        self.screen.query_one("#focus_sink").focus()
        return super()._on_screen_resume()


class DownloadScreen(Screen):

    CSS_PATH = ["styles/screens.tcss", "styles/widgets.tcss"]

    BINDINGS = [
        Binding("h", "app.pop_screen()", "Home"),
        Binding("s", "app.switch_screen('search')", "Search"),
        Binding("p", "app.switch_screen('settings')", "Settings"),
        Binding("backspace", "remove_all_tasks", "Clear list"),
    ]

    def __init__(self):
        self.controller: Controller = self.app.controller
        self.controller.subscribe(self)
        super().__init__()

    async def _on_screen_resume(self):
        # recomposing task viewer to sync all tasks
        await self.query_one(Vertical).query_one(TaskViewer).recompose()
        self.query_one("#focus_sink").focus()
        return super()._on_screen_resume()

    def compose(self):
        yield LoginHeader()
        yield Vertical(
            Container(
                SearchBar(id="search-bar-download"),
                id="search-container-download",
            ),
            TaskViewer(),
            classes="download-container",
        )
        yield Footer(show_command_palette=False)
        yield Button("", id="focus_sink", classes="focus-sink")  # focus sink

    def action_remove_all_tasks(self):
        self.query_one(TaskViewer).clear()

    @on(SearchQueryRequestMessage)
    def on_search_query_request(self, message: SearchQueryRequestMessage):
        self.query_one(SearchBar).set_value(message.query)
        self.query_one(TaskViewer).create_conversion_task(message.query)


class SearchScreen(Screen):

    CSS_PATH = ["styles/screens.tcss", "styles/widgets.tcss"]

    BINDINGS = [
        Binding("h", "app.pop_screen()", "Home"),
        Binding("d", "app.switch_screen('downloads')", "Downloads"),
        Binding("p", "app.switch_screen('settings')", "Settings"),
    ]

    def __init__(self):
        self.controller: Controller = self.app.controller
        self.controller.subscribe(self)
        super().__init__()

    def compose(self):
        yield LoginHeader()
        yield Vertical(
            Container(
                SearchBar(id="search-bar-search"),
                id="search-container-download",
            ),
            SearchResultView(),
            id="search-container",
        )

        yield Footer()
        yield Footer(show_command_palette=False)
        yield Button("", id="focus_sink", classes="focus-sink")  # focus sink

    @on(SearchQueryRequestMessage)
    def on_search_query_request(self, message: SearchQueryRequestMessage):
        self.query_one(SearchBar).set_value(message.query)
        results = self.controller.search(message.query)
        self.query_one(SearchResultView).add_results(results)


class SettingsScreen(Screen):
    CSS_PATH = ["styles/screens.tcss", "styles/widgets.tcss"]

    BINDINGS = [
        Binding("h", "app.pop_screen()", "Home"),
        Binding("d", "app.switch_screen('downloads')", "Downloads"),
        Binding("s", "app.switch_screen('search')", "Search"),
    ]

    def __init__(self):
        self.config: Config = self.app.config
        self.controller: Controller = self.app.controller
        super().__init__()

    def _on_screen_resume(self):
        self.screen.query_one("#focus_sink").focus()
        return super()._on_screen_resume()

    def bit_rate_config_2_select(self):
        match self.config.load_config()["bit_rate"]:
            case "MP3_320":
                return 1
            case "MP3_128":
                return 2
            case "FLAC":
                return 3
            case _:
                return 2

    def bit_rate_select_2_config(self, value):
        match value:
            case 1:
                return "MP3_320"
            case 2:
                return "MP3_128"
            case 3:
                return "FLAC"

    def compose(self):
        yield LoginHeader()
        yield VerticalScroll(
            Horizontal(
                Label("Download folder", classes="setting-descriptor"),
                Label(
                    self.config.load_config().get("download_folder") or "not set",
                    id="download_folder_label",
                    classes="download-folder",
                ),
                Button(
                    "Change",
                    "primary",
                    id="change_dir",
                    classes="change-dir-button",
                    tooltip="Change the base directory where things will be downloaded to.",
                ),
                classes="row",
            ),
            Horizontal(
                Label("Bit rate", classes="setting-descriptor"),
                Select(
                    options=[("MP3 320 Mbps", 1), ("MP3 128 Mbps", 2), ("FLAC", 3)],
                    prompt="Bit rate",
                    value=self.bit_rate_config_2_select(),
                    allow_blank=False,
                    id="bit_rate",
                    tooltip="bit rate for downloading from Deezer",
                ),
                classes="row",
            ),
            Horizontal(
                Label("Download overwrite", classes="setting-descriptor"),
                Switch(
                    self.config.load_config()["download_override"],
                    id="download_overwrite",
                    tooltip="If deerip will overwrite a file with the same name when downloading.",
                ),
                classes="row",
            ),
            Horizontal(
                Label("Concurrency download workers", classes="setting-descriptor"),
                Input(
                    value=str(self.config.load_config()["concurrency_workers"]),
                    type="integer",
                    validators=[Integer(minimum=1, maximum=16)],
                    id="concurrency_workers",
                    tooltip="Number of thread workers. Don't touch if you don't know what you are doing. min: 1, max: 16",
                ),
                classes="row",
            ),
            Horizontal(
                Label("Spotify client token", classes="setting-descriptor"),
                Input(
                    placeholder="Spotify client token",
                    value=self.config.get_env_variable("SPOTIFY_CLIENT_TOKEN"),
                    validators=[Length(minimum=32, maximum=32)],
                    id="spotify_client",
                    tooltip="Insert client token here and secret token in the one below. See readme on github for more info on how to setup spotify.",
                ),
                classes="row",
            ),
            Horizontal(
                Label("Spotify secret token", classes="setting-descriptor"),
                Input(
                    placeholder="Spotify secret token",
                    value=self.config.get_env_variable("SPOTIFY_SECRET_TOKEN"),
                    password=True,
                    validators=[Length(minimum=32, maximum=32)],
                    id="spotify_secret",
                ),
                Checkbox("show", id="spotify_secret_show"),
                classes="row",
            ),
            Button(
                "connect spotify",
                variant="primary",
                id="spotify_connect_button",
                classes="connect-btn",
                tooltip="Login to spotify. Will not overwrite current session.",
            ),
            Horizontal(
                Label("Deezer ARL", classes="setting-descriptor"),
                Input(
                    placeholder="Deezer arl",
                    value=self.config.get_env_variable("DEEZER_ARL"),
                    password=True,
                    validators=[Length(minimum=192, maximum=192)],
                    id="arl",
                ),
                Checkbox("show", id="arl_show"),
                classes="row",
            ),
            Button(
                "connect deezer",
                variant="primary",
                id="deezer_connect_button",
                classes="connect-btn",
                tooltip="Login to deezer. Will overwrite current session",
            ),
            classes="settings-container",
        )
        yield Footer(show_command_palette=False)
        yield Button("", id="focus_sink", classes="focus-sink")  # focus sink

    @on(Button.Pressed, "#change_dir")
    def on_change_dir_button_pressed(self, event: Button.Pressed):
        self.app.push_screen(DirectoryScreen())

    @on(ChooseDirectoryMessage)
    def on_choose_directory(self, message: ChooseDirectoryMessage):
        self.query_one("#download_folder_label", Label).update(message.path)
        updates = self.config.load_config()
        updates["download_folder"] = message.path

        self.config.update_config(updates)

    @on(Select.Changed, "#bit_rate")
    def on_select_changed(self, event: Select.Changed):
        bit_rate = self.bit_rate_select_2_config(event.value)
        if self.controller.can_stream_with_bit_rate(bit_rate):
            updates = self.config.load_config()
            updates["bit_rate"] = bit_rate
            self.config.update_config(updates)
        else:
            self.query_one("#bit_rate", Select).value = 2
            self.app.push_screen(
                PopupScreen(
                    "You cannot stream with this quality. Upgrade your deezer subscription or login"
                )
            )

    @on(Switch.Changed)
    def on_override_changed(self, event: Switch.Changed):
        updates = self.config.load_config()
        updates["download_override"] = event.value
        self.config.update_config(updates)

    @on(Input.Changed, "#concurrency_workers")
    def on_concurrency_workers_changed(self, event: Input.Changed):
        if len(event.validation_result.failures) == 0:
            updates = self.config.load_config()
            updates["concurrency_workers"] = event.value
            self.config.update_config(updates)

    @on(Checkbox.Changed, "#spotify_secret_show")
    def on_spotify_client_show(self, event: Checkbox.Changed):
        self.query_one("#spotify_secret", Input).password = not event.value

    @on(Checkbox.Changed, "#arl_show")
    def on_arl_show(self, event: Checkbox.Changed):
        self.query_one("#arl", Input).password = not event.value

    @on(Button.Pressed, "#spotify_connect_button")
    def on_spotify_connect(self, event: Button.Pressed):
        self.app.push_screen(LoadingScreen())
        self.spotify_login()

    @on(Button.Pressed, "#deezer_connect_button")
    def on_deezer_connect(self, event: Button.Pressed):
        self.app.push_screen(LoadingScreen())
        self.deezer_login()

    @work(thread=True)
    def spotify_login(self):
        client = self.query_one("#spotify_client", Input)
        secret = self.query_one("#spotify_secret", Input)

        if (
            client.validate(client.value).is_valid
            and secret.validate(secret.value).is_valid
        ):
            self.config.update_env_variable("SPOTIFY_CLIENT_TOKEN", client.value)
            self.config.update_env_variable("SPOTIFY_SECRET_TOKEN", secret.value)
            self.controller.login()
        self.app.call_from_thread(self.app.pop_screen)

    @work(thread=True)
    def deezer_login(self):
        arl = self.query_one("#arl", Input)

        if arl.validate(arl.value).is_valid:
            self.config.update_env_variable("DEEZER_ARL", arl.value)
            self.controller.login()

        self.app.call_from_thread(self.app.pop_screen)


class DirectoryScreen(ModalScreen):

    def __init__(self):
        self.path = ""
        super().__init__()

    def compose(self):
        yield Vertical(
            FilteredDirectoryTree("~/"),
            Horizontal(
                Button("Cancel", "warning", action="app.pop_screen"),
                Button("Save", "success", id="save_dir", disabled=True),
            ),
        )
        yield Button("", id="focus_sink", classes="focus-sink")  # focus sink

    @on(DirectoryTree.DirectorySelected)
    def on_directory_selected(self, event: DirectoryTree.DirectorySelected):
        self.query_one("#save_dir", Button).disabled = False
        self.path = event.path.as_posix()

    @on(Button.Pressed, "#save_dir")
    def on_save_dir_button_pressed(self):
        self.app.post_message(ChooseDirectoryMessage(self.path))
        self.app.pop_screen()


class TaskInfoScreen(ModalScreen):
    def __init__(self, widget):
        self.widget = widget
        super().__init__(id=f"info_{widget.id}")

    def compose(self):
        yield Vertical(
            Label(f"task_id  - {self.widget.id}"),
            Label(f"song_id  - {self.widget.song_id}"),
            Label(f"title    - {self.widget.title}"),
            Label(f"artist   - {self.widget.artist}"),
            Label(f"album    - {self.widget.album}"),
            Label(f"progress - {self.widget.progress}"),
            Button("Close", "warning"),
        )
        yield Button("", id="focus_sink", classes="focus-sink")  # focus sink

    @on(Button.Pressed)
    def on_okay_button_pressed(self):
        self.app.pop_screen()


class PopupScreen(ModalScreen):

    def __init__(self, message: str, id=None):
        self.message = message
        super().__init__(id=id)

    def compose(self):
        yield Vertical(
            Label(self.message), Button("Close", "warning"), classes="popup-container"
        )
        yield Button("", id="focus_sink", classes="focus-sink")  # focus sink

    @on(Button.Pressed)
    def on_okay_button_pressed(self):
        self.app.pop_screen()


class LoadingScreen(ModalScreen):

    def compose(self):
        yield LoginHeader()
        yield LoadingIndicator()
