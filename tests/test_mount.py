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


async def test_eager_composition_observes_completed_registration_and_styles():
    """Compose must not run inside a caller's unfinished mount / cover setup."""
    from textual.color import Color

    observed = []

    class Probe(Widget):
        def _post_register(self, app):
            super()._post_register(app)
            self.registration_complete = True

        def compose(self):
            assert self.registration_complete
            assert self._task is asyncio.current_task()
            assert self.styles.color == Color.parse("red")
            if self.id != "cover":
                assert all(
                    self.app.query_one(f"#{name}").styles.color == Color.parse("red")
                    for name in ("first", "second")
                )
            observed.append(self.id)
            return []

    class StartupApp(App):
        CSS = "Probe { color: red; }"

    loop = asyncio.get_running_loop()
    previous_factory = loop.get_task_factory()
    app = StartupApp()
    try:
        async with app.run_test() as pilot:
            loop.set_task_factory(asyncio.eager_task_factory)
            first, second = Probe(id="first"), Probe(id="second")
            await app.screen.mount(first, second)
            first._cover(Probe(id="cover"))
            await pilot.pause()
            assert observed == ["first", "second", "cover"]
            first._uncover()
            await first.remove()
            await second.remove()
    finally:
        loop.set_task_factory(previous_factory)


async def test_initial_notifications_observe_complete_tree_styles_and_css_sources():
    """Initial resource acquisition follows the complete registration's styles."""
    from textual.color import Color

    observed = []

    class Probe(Widget):
        def notify_style_update(self):
            super().notify_style_update()
            if self.id and not self.is_mounted:
                assert self.rich_style.color == Color.parse("red").rich_color
                assert self.app.query_one("#left").rich_style.italic
                observed.append(self.id)

    class LaterDeclaration(Probe):
        SCOPED_CSS = False
        DEFAULT_CSS = "#left { text-style: italic; }"

    class RegistrationApp(App):
        CSS = "#parent-a, #parent-b { color: red; }"

    app = RegistrationApp()
    async with app.run_test():
        left, right, last = Probe(id="left"), Probe(id="right"), Probe(id="last")
        first = Probe(id="parent-a")
        second = LaterDeclaration(id="parent-b")
        first._add_children(left, right)
        second._add_children(last)
        await app.mount(first, second)
        assert observed == ["left", "right", "last", "parent-a", "parent-b"]
        assert list(app.screen.children) == [first, second]
        assert list(first.children) == [left, right]
