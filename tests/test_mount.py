"""Regression test for https://github.com/Textualize/textual/issues/2914

Make sure that calls to render only happen after a widget being mounted.
"""

import asyncio
from unittest.mock import Mock

import pytest

from textual.app import App
from textual.widget import AwaitMount, Widget


class W(Widget):
    def render(self):
        return self.renderable

    async def on_mount(self):
        await asyncio.sleep(0.1)
        self.renderable = "1234"


async def test_render_only_after_mount():
    """Regression test for https://github.com/Textualize/textual/issues/2914"""
    app = App()
    async with app.run_test() as pilot:
        app.mount(W())
        app.mount(W())
        await pilot.pause()


async def test_mount_completion_is_shared_by_explicit_and_scheduled_awaiters():
    parent = Mock(spec=Widget)
    children = [Widget(), Widget()]
    mounted = AwaitMount(parent, children)
    explicit = asyncio.create_task(mounted())
    scheduled = asyncio.create_task(mounted())
    await asyncio.sleep(0)
    children[0]._mounted_event.set()
    await asyncio.sleep(0)
    assert not explicit.done() and not scheduled.done()
    children[1]._mounted_event.set()
    await asyncio.gather(explicit, scheduled)
    await mounted
    parent.refresh.assert_called_once_with(layout=True)
    parent.app._update_mouse_over.assert_called_once_with(parent.screen)


async def test_cancelling_one_mount_awaiter_does_not_cancel_completion():
    parent = Mock(spec=Widget)
    child = Widget()
    mounted = AwaitMount(parent, [child])
    first = asyncio.create_task(mounted())
    second = asyncio.create_task(mounted())
    await asyncio.sleep(0)
    await asyncio.sleep(0)
    first.cancel()
    with pytest.raises(asyncio.CancelledError):
        await first
    await asyncio.sleep(0)
    waiters = [task for task in asyncio.all_tasks() if task.get_name() == "await mount"]
    assert len(waiters) <= 1, "A cancelled mount waiter left duplicate child waits"
    assert not second.done()
    child._mounted_event.set()
    await asyncio.wait_for(second, 1)
    parent.refresh.assert_called_once_with(layout=True)
