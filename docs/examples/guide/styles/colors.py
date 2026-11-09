from textual.app import App, ComposeResult
from textual.widgets import Static
from textual import events
from textual import on


class WidgetApp(App):
    def compose(self) -> ComposeResult:
        self.widget = Static("Textual")
        yield self.widget

    @on(events.Mount)
    def on_mount(self) -> None:
        self.widget.styles.background = "darkblue"
        self.widget.styles.border = ("heavy", "white")


if __name__ == "__main__":
    app = WidgetApp()
    app.run()
