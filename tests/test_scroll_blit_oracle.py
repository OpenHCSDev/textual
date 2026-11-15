"""Correctness oracle for the scroll blit, validated against the real target terminal.

The compositor's incremental byte stream (now containing terminal scroll-region blits,
including rectangular DECSLRM scrolls for a pane beside a sidebar) is fed through the
patched st's own terminal logic (`st_render`, built headless from st.c) and must paint
the exact cell grid a full redraw of the same final state produces. Equal grids prove
the blit carries and fixes up cells — including the left/right-margin scroll — without
tearing, on the terminal it will actually run on.
"""

import os
import subprocess

import pytest

ST_RENDER = "/home/ts/programs/st/st_render"
pytestmark = pytest.mark.skipif(
    not os.path.exists(ST_RENDER), reason="patched st_render oracle not built"
)

from textual._compositor import run_steps
from textual.containers import VerticalScroll
from tests.test_paint_output import PageView, PaintApp


def _st_grid(width: int, height: int, chunks: list[str]) -> list[str]:
    data = "".join(chunks).encode("utf-8", "replace")
    out = subprocess.run(
        [ST_RENDER, str(width), str(height)], input=data, capture_output=True
    ).stdout.decode("utf-8", "replace")
    return out.split("\n")[:height]


async def _updates_and_full() -> tuple[list[str], str, int, int]:
    app = PaintApp()
    async with app.run_test(size=(100, 36)) as pilot:
        await pilot.pause()
        # The terminal (patched st) honours DECSLRM, so sub-width panes may blit.
        app.screen._compositor._supports_rectangular_scroll = True
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
async def test_scroll_blit_matches_full_redraw_on_patched_st():
    updates, full_segments, width, height = await _updates_and_full()
    # A rectangular (DECSLRM) scroll must actually have been emitted, or this proves nothing.
    assert any("\x1b[?69h" in u for u in updates), \
        "expected at least one DECSLRM (rectangular scroll) sequence in the stream"
    incremental = _st_grid(width, height, updates)
    full = _st_grid(width, height, [full_segments])
    assert incremental == full
