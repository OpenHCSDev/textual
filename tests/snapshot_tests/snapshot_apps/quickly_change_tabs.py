"""Regression test for https://github.com/Textualize/textual/issues/2229."""
from textual.app import App, ComposeResult
from textual.widgets import TabbedContent, TabPane, Tabs, Label
from textual.binding import MethodBinding


class QuicklyChangeTabsApp(App[None]):
    def compose(self) -> ComposeResult:
        with TabbedContent():
            with TabPane("one"):
                yield Label("one")
            with TabPane("two"):
                yield Label("two")
            with TabPane("three", id="three"):
                yield Label("three")

    @MethodBinding.declare("p")
    def key_p(self) -> None:
        self.query_one(Tabs).action_cursor_right()
        self.query_one(Tabs).action_cursor_right()


app = QuicklyChangeTabsApp()

if __name__ == "__main__":
    app.run()
