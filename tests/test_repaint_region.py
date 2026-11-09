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
        self.strip_preparations = 0
        self.painted: list[int] = []
        self.painted_text: dict[int, str] = {}
        self.body = "row"

    def render(self) -> str:
        self.content_renders += 1
        return "\n".join(f"{self.body} {index}" for index in range(3))

    def _render_content(self, paint) -> None:
        self.strip_preparations += 1
        super()._render_content(paint)

    def render_line(self, y: int, paint):
        self.painted.append(y)
        line = super().render_line(y, paint)
        self.painted_text[y] = line.text
        return line


class RowsApp(App):
    def compose(self) -> ComposeResult:
        yield CountingRows()


async def test_repaint_region_paints_only_its_lines_without_rerendering_content():
    app = RowsApp()
    async with app.run_test() as pilot:
        rows = app.query_one(CountingRows)
        await pilot.pause()
        renders_before = rows.content_renders
        prepared_before = rows.strip_preparations
        rows.painted.clear()

        rows.repaint_region(Region(0, 0, rows.size.width, 1))
        await pilot.pause()

        assert rows.content_renders == renders_before, "the content is kept, not rendered again"
        assert rows.strip_preparations == prepared_before
        assert set(rows.painted) == {0}, "only the requested line is painted"

        rows.body = "changed"
        rows.refresh(Region(0, 0, rows.size.width, 1))
        await pilot.pause()
        assert rows.strip_preparations > prepared_before
        assert rows.painted_text[0].startswith("changed 0")


async def test_repaint_lines_still_paints_every_line():
    app = RowsApp()
    async with app.run_test() as pilot:
        rows = app.query_one(CountingRows)
        await pilot.pause()
        rows.painted.clear()

        rows.repaint_lines()
        await pilot.pause()

        assert set(rows.painted) >= {0, 1, 2}, "the base path still paints every line"
