from textual import events
from textual.app import App, ComposeResult
from textual.widgets import RichLog
from textual import on
from textual.binding import MethodBinding


class InputApp(App):
    """App to display key events."""

    def compose(self) -> ComposeResult:
        yield RichLog()

    @on(events.Key)
    def on_key(self, event: events.Key) -> None:
        self.query_one(RichLog).write(event)

    @MethodBinding.declare("space")
    def key_space(self) -> None:
        self.bell()


if __name__ == "__main__":
    app = InputApp()
    app.run()
