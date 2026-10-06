import asyncio

import pytest

from textual._context import active_message_pump
from textual.app import App, ComposeResult
from textual.screen import Screen
from textual.widgets import Static


@pytest.mark.parametrize("sender_kind", ["app", "widget"])
async def test_async_sender_callback_does_not_borrow_screen_task(sender_kind):
    """A suspended sender cannot own another sender's paint or callbacks."""
    complete = asyncio.Event()
    sidebar_written = asyncio.Event()
    child_tasks = []

    class CallbackApp(App):
        def compose(self) -> ComposeResult:
            yield Static("saved history", id="history")
            yield Static("pending sidebar", id="sidebar")

    app = CallbackApp()

    async def drive(pilot):
        await pilot.pause()
        history = app.query_one("#history")
        sidebar = app.query_one("#sidebar", Static)
        sender = app if sender_kind == "app" else history
        child_tasks.extend((history.task, sidebar.task, app.screen.task))

        def sidebar_published():
            assert asyncio.current_task() is sidebar.task
            assert active_message_pump.get() is sidebar
            assert not app.screen._compositor.pending_for(sidebar)
            text = "\n".join(strip.text for strip in app.screen._compositor.render_strips())
            assert "unrelated sidebar paint" in text
            sidebar_written.set()

        async def after_paint():
            assert asyncio.current_task() is sender.task
            assert active_message_pump.get() is sender
            # This original self-wait rule must apply to the actual pump task.
            assert await sender.wait_for_refresh() is False
            sidebar.update("unrelated sidebar paint")
            sidebar.call_after_refresh(sidebar_published)
            await sidebar_written.wait()
            complete.set()

        sender.call_after_refresh(after_paint)
        await asyncio.wait_for(complete.wait(), 5)
        app.exit()

    await asyncio.wait_for(
        app.run_async(headless=True, size=(40, 8), auto_pilot=drive), 10
    )
    assert app._exception is None
    assert app._task is None
    assert all(task.done() for task in child_tasks)


async def test_sender_delivery_preserves_held_subtree_and_whole_frame_admission():
    sidebar_written = asyncio.Event()
    held_written = asyncio.Event()
    screen_written = asyncio.Event()
    app_written = asyncio.Event()

    class SourceScreen(Screen):
        held = False

        def compose(self) -> ComposeResult:
            yield Static("old source", id="source")
            yield Static("old sidebar", id="sidebar")

        def _prepare_compositor_refresh(self):
            return (self.query_one("#source"),) if self.held else ()

    class SourceApp(App):
        def get_default_screen(self):
            return SourceScreen()

    app = SourceApp()

    async def drive(pilot):
        await pilot.pause()
        screen = app.screen
        source = screen.query_one("#source", Static)
        sidebar = screen.query_one("#sidebar", Static)
        screen.held = True
        source.update("new source")
        sidebar.update("new sidebar")

        def published(sender, written):
            assert asyncio.current_task() is sender.task
            assert active_message_pump.get() is sender
            assert not sender._after_refresh_pending(screen, screen._prepare_compositor_refresh())
            written.set()

        source.call_after_refresh(published, source, held_written)
        sidebar.call_after_refresh(published, sidebar, sidebar_written)
        screen.call_after_refresh(published, screen, screen_written)
        app.call_after_refresh(published, app, app_written)
        await asyncio.wait_for(sidebar_written.wait(), 5)
        assert not held_written.is_set()
        assert not screen_written.is_set()
        assert not app_written.is_set()
        assert screen._compositor.pending_for(source)
        assert {sender for _, sender in screen._callbacks} >= {source, screen, app}

        screen.held = False
        source.refresh()
        await asyncio.wait_for(
            asyncio.gather(held_written.wait(), screen_written.wait(), app_written.wait()),
            5,
        )
        assert not screen._compositor.pending_for(source)
        app.exit()

    await asyncio.wait_for(
        app.run_async(headless=True, size=(40, 8), auto_pilot=drive), 10
    )
    assert app._exception is None
    assert app._task is None
