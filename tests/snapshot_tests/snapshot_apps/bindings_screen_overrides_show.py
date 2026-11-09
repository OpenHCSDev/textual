from textual.app import App, ComposeResult
from textual.screen import Screen
from textual.binding import Binding
from textual.widgets import Footer
from textual import events
from textual import on


class ShowBindingScreen(Screen):
    BINDINGS = [
        Binding("p", "app.pop_screen", "Binding shown"),
    ]

    def compose(self) -> ComposeResult:
        yield Footer()


class HideBindingApp(App):
    """Regression test for https://github.com/Textualize/textual/issues/4382"""

    BINDINGS = [
        Binding("p", "app.pop_screen", "Binding hidden", show=False),
    ]

    @on(events.Mount)
    def on_mount(self) -> None:
        self.push_screen(ShowBindingScreen())


if __name__ == "__main__":
    app = HideBindingApp()
    app.run()
