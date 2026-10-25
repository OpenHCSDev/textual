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


async def test_callbacks_run_while_another_widget_relayouts_every_frame():
    """A spinner that relayouts every frame never keeps the screen idle; callbacks queued
    meanwhile still run after the next published frame instead of piling up."""
    ran = []

    class Spinner(Static):
        def on_mount(self):
            self.screen.screen_layout_refresh_signal.subscribe(self, self.spin, immediate=True)

        def spin(self, _screen):
            # Every published layout requests the next one, so a refresh is always pending.
            self.refresh(layout=True)

    class SpinnerApp(App):
        def compose(self) -> ComposeResult:
            yield Spinner("thinking", id="spinner")
            yield Static("toast", id="toast")

    app = SpinnerApp()

    async def drive(pilot):
        await pilot.pause()
        toast = app.query_one("#toast")
        done = asyncio.Event()

        def record(index):
            ran.append(index)
            if len(ran) == 50:
                done.set()

        for index in range(50):
            toast.call_after_refresh(record, index)
        await asyncio.wait_for(done.wait(), 2)
        assert ran == list(range(50))
        assert app.screen._callbacks == []
        app.exit()

    await asyncio.wait_for(
        app.run_async(headless=True, size=(40, 8), auto_pilot=drive), 10
    )
    assert app._exception is None
