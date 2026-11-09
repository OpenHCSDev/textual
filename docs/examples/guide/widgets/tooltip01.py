from textual.app import App, ComposeResult
from textual.widgets import Button
from textual import events
from textual import on

TEXT = """I must not fear.
Fear is the mind-killer.
Fear is the little-death that brings total obliteration.
I will face my fear."""


class TooltipApp(App):
    CSS = """
    Screen {
        align: center middle;
    }
    """

    def compose(self) -> ComposeResult:
        yield Button("Click me", variant="success")

    @on(events.Mount)
    def on_mount(self) -> None:
        self.query_one(Button).tooltip = TEXT


if __name__ == "__main__":
    app = TooltipApp()
    app.run()
