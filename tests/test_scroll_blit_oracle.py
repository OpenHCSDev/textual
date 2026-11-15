"""Correctness oracle for the scroll blit: the incremental byte stream (which now
includes terminal scroll-region blits) must paint the exact screen a full redraw of
the same final state would. Feeding both through a real VT emulator (pyte) and
comparing the grids proves the blit carries and fixes up cells without tearing.

Uses the exact scrolling scenario of test_paint_output, so the re-recorded golden
digest there is backed by this no-tearing proof on the same stream.
"""

import pytest

pyte = pytest.importorskip("pyte")

from textual._compositor import CompositorUpdate, run_steps
from textual.containers import VerticalScroll
from tests.test_paint_output import PageView, PaintApp, record_updates


def _grid(width: int, height: int, chunks: list[str]) -> list[str]:
    screen = pyte.Screen(width, height)
    stream = pyte.Stream(screen)
    for chunk in chunks:
        stream.feed(chunk)
    return list(screen.display)


async def _updates_and_full() -> tuple[list[str], str, int, int]:
    """The recorded incremental stream and a full redraw of the same final state."""
    app = PaintApp()
    async with app.run_test(size=(100, 36)) as pilot:
        await pilot.pause()
        history = app.query_one("#history", VerticalScroll)
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
        width, height = app.size
        full = run_steps(app.screen._compositor.render_update(full=True))
        full_segments = full.render_segments(app.console)
    return app.updates, full_segments, width, height


@pytest.mark.asyncio
async def test_scroll_blit_stream_paints_the_same_screen_as_a_full_redraw():
    updates, full_segments, width, height = await _updates_and_full()
    assert any("\x1b[" in u and ("S" in u or "T" in u) and "r" in u for u in updates), \
        "expected at least one terminal scroll-region sequence in the stream"
    incremental = _grid(width, height, updates)
    full = _grid(width, height, [full_segments])
    assert incremental == full
