import asyncio

import pytest

from textual._context import active_message_pump
from textual.app import App, ComposeResult
from textual.message import Message
from textual.widgets import Static


async def test_busy_sender_hands_execution_to_peer_after_completed_delivery():
    class Notice(Message):
        def __init__(self, sequence):
            super().__init__()
            self.sequence = sequence

    delivered = []
    peer_received = asyncio.Event()
    finished = asyncio.Event()
    peer_position = []

    class Sender(Static):
        def on_notice(self, message):
            message.stop()
            delivered.append(message.sequence)
            if message.sequence == 0:
                self.app.query_one("#peer").call_later(peer_delivery)
            if message.sequence == 63:
                finished.set()

    def peer_delivery():
        peer_position.append(len(delivered))
        peer_received.set()

    class BurstApp(App):
        def compose(self):
            yield Sender("sender", id="sender")
            yield Static("peer", id="peer")

    app = BurstApp()

    async def drive(pilot):
        await pilot.pause()
        sender = app.query_one("#sender")
        for sequence in range(64):
            sender.post_message(Notice(sequence))
        await asyncio.wait_for(peer_received.wait(), 5)
        await asyncio.wait_for(finished.wait(), 5)
        assert delivered == list(range(64))
        assert 0 < peer_position[0] < 64
        app.exit()

    await asyncio.wait_for(
        app.run_async(headless=True, size=(40, 8), auto_pilot=drive), 10
    )
    assert app._exception is None
    assert app._task is None


@pytest.mark.parametrize("work", ["layout", "scroll"])
async def test_frame_preserves_requests_from_its_layout_publication(work):
    class FrameApp(App):
        def compose(self):
            child = Static("native source", id="source")
            child.styles.width = 10
            child.styles.height = 40
            yield child

    app = FrameApp()

    async def drive(pilot):
        await pilot.pause()
        screen = app.screen
        source = app.query_one("#source")
        received = asyncio.Event()

        def request_next_frame(_screen):
            screen.screen_layout_refresh_signal.unsubscribe(source)
            if work == "layout":
                source.styles.width = 20
                screen.refresh(layout=True)
            else:
                screen.scroll_to(y=2, animate=False, immediate=True, force=True)

        screen.screen_layout_refresh_signal.subscribe(
            source, request_next_frame, immediate=True
        )
        screen.refresh(layout=True)
        screen._on_timer_update()
        # The completed geometry is still the first frame. Its subscriber
        # requested independent work through the original native owner.
        if work == "layout":
            assert source.region.width == 10
            assert screen._layout_required
        else:
            assert screen.scroll_y == 2
            assert screen._scroll_required
        assert screen._refresh_pending
        screen.call_after_refresh(received.set)
        await asyncio.wait_for(received.wait(), 5)
        if work == "layout":
            assert source.region.width == 20
        else:
            assert source.region.y == -2
        assert not screen._refresh_pending
        app.exit()

    await asyncio.wait_for(
        app.run_async(headless=True, size=(40, 8), auto_pilot=drive), 10
    )
    assert app._exception is None
    assert app._task is None


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
