from textual.app import App, ComposeResult
from textual.screen import Screen
from textual.widget import Widget
from textual.widgets import Footer, Input, Button
from textual.containers import Vertical
from textual.binding import Binding


class SearchBar(Widget):
    DEFAULT_CSS = """
        Input {
            width: 50%;
            align: center middle;
        }
    """

    def compose(self) -> ComposeResult:
        yield Input(placeholder="Search...")


class HomeScreen(Screen):
    DEFAULT_CSS = """
        Footer {
            width: 100%;
            align: center bottom;
        }
        #centered-container {
            height: 100%;
    width: 100%;
    align: center middle;
}
    """
    BINDINGS = [
        Binding("d", "app.push_screen('downloads')", "Downloads", show=True),
        Binding("h", "app.push_screen('home')", "Home", show=True),
    ]

    def compose(self) -> ComposeResult:
        yield Vertical(Button())
        yield Footer()


class MyApp(App):
    def on_mount(self) -> None:
        self.push_screen(HomeScreen())


app = MyApp()
app.run()
