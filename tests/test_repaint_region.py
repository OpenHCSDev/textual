"""A mounted widget repaints one region without re-rendering its content.

`repaint_region` keeps the rendered content (no `render()` call) and paints only the
lines inside the region. The counts are taken on a mounted widget in a running app.
"""

from textual.app import App, ComposeResult
from textual.geometry import Region
from textual.widget import Widget


class CountingRows(Widget):
    def __init__(self) -> None:
        super().__init__()
        self.content_renders = 0
        self.painted: list[int] = []

    def render(self) -> str:
        self.content_renders += 1
        return "\n".join(f"row {index}" for index in range(3))

    def render_line(self, y: int, paint):
        self.painted.append(y)
        return super().render_line(y, paint)


class RowsApp(App):
    def compose(self) -> ComposeResult:
        yield CountingRows()


async def test_repaint_region_paints_only_its_lines_without_rerendering_content():
    app = RowsApp()
    async with app.run_test() as pilot:
        rows = app.query_one(CountingRows)
        await pilot.pause()
        renders_before = rows.content_renders
        rows.painted.clear()

        rows.repaint_region(Region(0, 0, rows.size.width, 1))
        await pilot.pause()

        assert rows.content_renders == renders_before, "the content is kept, not rendered again"
        assert set(rows.painted) == {0}, "only the requested line is painted"


async def test_repaint_lines_still_paints_every_line():
    app = RowsApp()
    async with app.run_test() as pilot:
        rows = app.query_one(CountingRows)
        await pilot.pause()
        rows.painted.clear()

        rows.repaint_lines()
        await pilot.pause()

        assert set(rows.painted) >= {0, 1, 2}, "the base path still paints every line"
