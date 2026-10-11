"""The terminal receives the same bytes for a realistic scrolling screen.

A history-like screen (a docked header and footer, a scrolling column of
line-drawn pages with padding, borders, tint, a one-column gutter beside
them, wide characters and an overlay on its own layer) is scrolled by
pages, by lines and back, and parts of it are refreshed. Every update the
driver would write is recorded. The digest was recorded from the paint
path before its strips kept their rendered form (Textual 266d53c94); paint
optimisations must not change one byte of it.
"""

from __future__ import annotations

import hashlib

from rich.segment import Segment
from rich.style import Style

from textual.app import App, ComposeResult
from textual.containers import Horizontal, VerticalScroll
from textual.strip import Strip
from textual.widget import Widget
from textual.widgets import Static

# sha256 of the joined updates and their count, recorded on Textual 266d53c94.
# Re-recorded when a scoped scroll reflow stopped putting the history in front
# of its own scrollbar: the only change is that the scrollbar's cells (column
# 99) show the bar again instead of the container's background.
EXPECTED_DIGEST = "43fb71c47b758efd8d4e9300096d7a9638d5f78e2f29072d136e06f76d815826"
EXPECTED_UPDATES = 22

WORDS = ("history", "│", "─┼─", "漢字", "scroll", "ü", "paint", "🙂", "line", "cells", "┌─┐", "compositor")


def page_lines(page: int, count: int) -> list[Strip]:
    """Deterministic styled lines, some shorter than the page and some wider."""
    lines = []
    for row in range(count):
        segments = []
        for word in range((row * 7 + page) % 9 + 1):
            index = (page * 31 + row * 7 + word) % len(WORDS)
            style = Style(
                color=f"#{(index * 40) % 256:02x}{(row * 17) % 256:02x}{(page * 50) % 256:02x}",
                bgcolor=None if word % 3 else f"#{(row * 9) % 256:02x}2030",
                bold=bool(word % 2),
                italic=word % 5 == 1,
                underline=word % 7 == 3,
            )
            segments.append(Segment(WORDS[index], style))
            segments.append(Segment(" ", Style()))
        if row % 11 == 4:
            segments.append(Segment("x" * 120, Style(color="red")))
        lines.append(Strip(segments))
    return lines


class PageView(Widget):
    """Draws prepared lines the way a transcript page does."""

    DEFAULT_CSS = "PageView { height: auto; }"

    def __init__(self, page: int, count: int, **kwargs) -> None:
        super().__init__(**kwargs)
        self.lines = page_lines(page, count)

    def get_content_height(self, container, viewport, width: int) -> int:
        return len(self.lines)

    def render_line(self, y: int) -> Strip:
        width = self.size.width
        if y >= len(self.lines):
            return Strip.blank(width)
        return self.lines[y].extend_cell_length(width).crop(0, width)


class Gutter(Widget):
    DEFAULT_CSS = "Gutter { width: 1; height: 100%; }"

    def render_lines(self, crop):
        style = Style(color="#5050ff")
        strips = [Strip([Segment("▌", style)], 1)] * crop.height
        if crop.y == 0 and strips:
            strips[0] = Strip([Segment(" ", style)], 1)
        return strips


class PaintApp(App):
    CSS = """
    Screen { layers: base overlay; }
    #header { dock: top; height: 1; background: $primary; }
    #footer { dock: bottom; height: 2; background: $panel; }
    #history { height: 1fr; }
    #pages { height: auto; }
    PageView.padded { padding: 0 2; background: #102030; }
    PageView.bordered { border: round #808080; }
    PageView.tinted { tint: #ff000030; }
    #overlay { layer: overlay; offset: 50 6; width: 24; height: 5; border: solid yellow; background: #303030; }
    """

    def __init__(self) -> None:
        super().__init__()
        self.updates: list[str] = []

    def compose(self) -> ComposeResult:
        yield Static("[b]header[/b] 漢字 title", id="header")
        with Horizontal():
            yield Gutter()
            with VerticalScroll(id="history"):
                for page in range(14):
                    classes = ("padded", "bordered", "", "tinted", "padded", "", "padded tinted")[page % 7]
                    yield PageView(page, 20 + page % 5 * 6, classes=classes)
        yield Static("footer ─ status [i]line[/i]\nsecond 🙂 row", id="footer")
        yield Static("overlay\n[b]on top[/b] 漢", id="overlay")

    def _display(self, screen, renderable) -> None:
        from textual._compositor import CompositorUpdate

        if isinstance(renderable, CompositorUpdate) and not self._batch_count:
            self.updates.append(renderable.render_segments(self.console))
        super()._display(screen, renderable)


async def record_updates() -> list[str]:
    app = PaintApp()
    async with app.run_test(size=(100, 36)) as pilot:
        await pilot.pause()
        history = app.query_one("#history")
        history.scroll_end(animate=False, immediate=True)
        await pilot.pause()
        for _ in range(6):
            history.scroll_page_up(animate=False)
            await pilot.pause()
        for delta in (1, 1, 3, -2, 7):
            history.scroll_to(y=history.scroll_y + delta, animate=False)
            await pilot.pause()
        pages = list(app.query(PageView))
        pages[3].refresh()
        await pilot.pause()
        app.query_one("#overlay").update("changed\n[b]overlay[/b] 🙂")
        await pilot.pause()
        for _ in range(3):
            history.scroll_page_down(animate=False)
            await pilot.pause()
        history.scroll_home(animate=False, immediate=True)
        await pilot.pause()
        pages[0].refresh()
        await pilot.pause()
        app.screen.refresh()
        await pilot.pause()
    return app.updates


async def test_terminal_output_is_unchanged():
    updates = await record_updates()
    digest = hashlib.sha256("\0".join(updates).encode("utf-8")).hexdigest()
    assert (digest, len(updates)) == (EXPECTED_DIGEST, EXPECTED_UPDATES)


async def test_terminal_output_is_deterministic():
    first, second = await record_updates(), await record_updates()
    assert first == second


async def test_plain_widget_paints_its_own_lines():
    """A widget without border, padding or effects is drawn with its content
    strips themselves, so what a strip computed for the terminal is kept."""

    class Lines(Widget):
        def __init__(self) -> None:
            super().__init__()
            self.lines = [Strip([Segment(f"{row:<20}", Style(color="red"))], 20) for row in range(5)]

        def render_line(self, y: int) -> Strip:
            return self.lines[y]

    class LinesApp(App):
        CSS = "Lines { width: 20; height: 5; }"

        def compose(self) -> ComposeResult:
            yield Lines()

    app = LinesApp()
    async with app.run_test(size=(30, 8)) as pilot:
        await pilot.pause()
        widget = app.query_one(Lines)
        drawn = widget.render_lines(widget.size.region)
        # Its styled lines are dropped (as on a refresh); drawing them again
        # reuses the strips (and their line filters' results) already drawn.
        widget._styles_cache.clear()
        again = widget.render_lines(widget.size.region)
        assert all(first is second for first, second in zip(drawn, again))
        if not widget.get_line_filters():
            assert all(strip is line for strip, line in zip(drawn, widget.lines))
