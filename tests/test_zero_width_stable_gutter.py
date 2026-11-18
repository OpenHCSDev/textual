"""A stable gutter declared 0 cells wide leaves the content its whole width."""
import pytest

from textual.app import App
from textual.containers import Grid, VerticalScroll
from textual.widgets import Static


class Rows(Grid):
    DEFAULT_CSS = "Rows { grid-size: 2; grid-columns: 1 1fr; height: auto; width: 1fr; }"


class Reader(App):
    def __init__(self, scrollbar: int) -> None:
        super().__init__()
        self.scrollbar = scrollbar

    def compose(self):
        with VerticalScroll() as scroller:
            scroller.styles.scrollbar_gutter = "stable"
            scroller.styles.overflow_x = "hidden"
            scroller.styles.scrollbar_size_vertical = self.scrollbar
            with Rows():
                yield Static("|")
                yield Static("text " * 40)


@pytest.mark.parametrize("scrollbar", [0, 1, 2])
async def test_stable_gutter_takes_only_its_declared_width(scrollbar: int) -> None:
    app = Reader(scrollbar)
    async with app.run_test(size=(80, 20)) as pilot:
        await pilot.pause()
        assert app.query_one(Rows).region.width == 80 - scrollbar
