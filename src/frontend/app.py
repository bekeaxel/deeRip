from textual import events
from textual.app import App
from textual import on
from textual.binding import Binding
from textual.widgets import Label

from src.frontend.messages import *
from src.backend.main_controller import Controller
from src.frontend.screens import *
from src.backend.configuration import Config


class DeeRipApp(App):
    ENABLE_COMMAND_PALETTE = False
    CSS_PATH = "styles/global.tcss"

    SCREENS = {
        "home": HomeScreen,
        "downloads": DownloadScreen,
        "search": SearchScreen,
        "settings": SettingsScreen,
    }

    spotify = reactive(False)
    deezer = reactive(False)

    def __init__(self):
        super().__init__()
        self.controller: Controller = Controller()
        self.config: Config = Config()
        self.controller.subscribe(self)
        self.controller.login()

    def on_mount(self):
        self.push_screen("home")
        self.title = "spotify: not connected, deezer: not connected"

    @on(SearchQueryRequestMessage)
    def on_search_query_request(self, message: SearchQueryRequestMessage):
        message.bubble = False
        self.query = message.query
        if self.controller.valid_url(message.query):
            self.push_screen("downloads")
            self.get_screen("downloads").post_message(message)
        else:
            self.push_screen("search")
            self.get_screen("search").post_message(message)

    @on(ChooseDirectoryMessage)
    def on_choose_directory(self, message: ChooseDirectoryMessage):
        self.get_screen("settings").post_message(message)

    @on(events.Click)
    def on_click(self, event: events.Click):
        self.spotify = True
        if not isinstance(event.widget, Input):
            self.screen.query_one("#focus_sink").focus()

    @on(LoginStatusMessage)
    def on_login_status(self, message: LoginStatusMessage):
        if message.spotify and message.deezer:
            self.title = "spotify: connected, deezer: connected"
        elif message.spotify and not message.deezer:
            self.title = "spotify: connected, deezer: not connected"
        elif not message.spotify and message.deezer:
            self.title = "spotify: not connected, deezer: connected"
        else:
            self.title = "spotify: not connected, deezer: not connected"
