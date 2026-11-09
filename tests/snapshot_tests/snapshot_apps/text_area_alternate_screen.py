from textual.app import App
from textual.screen import Screen
from textual.widgets import TextArea
from textual import events
from textual import on

TEXT = """\
foo
bar
baz
"""


class AltScreen(Screen[None]):
    def compose(self):
        yield TextArea(TEXT)


class TABug(App[None]):
    @on(events.Mount)
    def on_mount(self):
        self.push_screen(AltScreen())


if __name__ == "__main__":
    app = TABug()
    app.run()
