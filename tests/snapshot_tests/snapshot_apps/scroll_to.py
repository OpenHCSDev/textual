from textual.app import App, ComposeResult
from textual.widgets import Checkbox, Footer
from textual import events
from textual import on


class ScrollOffByOne(App):
    """Scroll to item 50."""

    AUTO_FOCUS = None

    def compose(self) -> ComposeResult:
        for number in range(1, 100):
            yield Checkbox(str(number), id=f"number-{number}")
        yield Footer()

    @on(events.Ready)
    def on_ready(self) -> None:
        self.query_one("#number-50").scroll_visible()


app = ScrollOffByOne()
if __name__ == "__main__":
    app.run()
