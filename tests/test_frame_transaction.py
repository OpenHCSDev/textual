from unittest.mock import patch

from textual.app import App
from textual.widgets import Static


async def test_layout_and_full_repaint_commit_one_compositor_frame():
    app = App()
    async with app.run_test() as pilot:
        await app.mount(Static("first", id="content"))
        await pilot.pause()
        screen = app.screen
        app.query_one("#content", Static).update("replacement\nsecond row")
        screen.refresh(layout=True)
        with patch.object(screen, "_compositor_refresh", wraps=screen._compositor_refresh) as paint:
            screen._on_timer_update()
            assert paint.call_count == 1, "Layout and repaint produced duplicate frames"
        await pilot.pause()
        text = "\n".join(strip.text for strip in screen._compositor.render_strips())
        assert "replacement" in text and "second row" in text
