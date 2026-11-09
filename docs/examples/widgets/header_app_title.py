from textual.app import App, ComposeResult
from textual.widgets import Header
from textual import events
from textual import on


class HeaderApp(App):
    def compose(self) -> ComposeResult:
        yield Header()

    @on(events.Mount)
    def on_mount(self) -> None:
        self.title = "Header Application"
        self.sub_title = "With title and sub-title"


if __name__ == "__main__":
    app = HeaderApp()
    app.run()
