"""Real framework lifecycle checks, not installed terminal acceptance."""

import asyncio

from textual.app import App, ComposeResult
from textual.containers import Vertical
from textual.screen import Screen
from textual.widgets import Label


class ObservedScreen(Screen):
    def __init__(self) -> None:
        super().__init__()
        self.preparation_batches: list[int] = []

    def _prepare_compositor_refresh(self) -> bool:
        self.preparation_batches.append(self.app._batch_count)
        return super()._prepare_compositor_refresh()


class BatchPaintApp(App):
    def __init__(self) -> None:
        super().__init__()
        self.frames: list[tuple[int, str]] = []

    def get_default_screen(self) -> Screen:
        return ObservedScreen()

    def compose(self) -> ComposeResult:
        with Vertical(id="holder"):
            yield Label("original")

    def _display(self, screen, renderable) -> None:
        if renderable is not None:
            self.frames.append((self._batch_count, type(renderable).__name__))
        super()._display(screen, renderable)


async def test_async_widget_batch_retains_damage_and_refresh_callbacks() -> None:
    app = BatchPaintApp()
    painted = asyncio.Event()
    async with app.run_test(size=(50, 12)) as pilot:
        await pilot.pause()
        holder = app.query_one("#holder", Vertical)
        screen = app.screen
        app.frames.clear()
        screen.preparation_batches.clear()
        async with holder.batch():
            await holder.mount(Label("new retained source", id="new"))
            screen._refresh_layout()
            app.call_after_refresh(painted.set)
            await pilot.pause()
            damage = set(screen._compositor._dirty_regions)
            assert damage, "Mount must produce actual compositor damage"
            assert not app.frames
            assert not screen.preparation_batches
            assert not painted.is_set()
            # A queued/direct compositor refresh must obey the same admission.
            screen._compositor_refresh()
            assert screen._compositor._dirty_regions == damage
        await asyncio.wait_for(painted.wait(), 1)
        assert app.frames
        assert all(batch == 0 for batch, _ in app.frames)
        assert screen.preparation_batches
        assert all(batch == 0 for batch in screen.preparation_batches)
        assert not screen._compositor._dirty_regions
        assert app.query_one("#new", Label).is_attached


async def test_refresh_callback_queue_survives_a_batch_between_callbacks() -> None:
    app = BatchPaintApp()
    entered = asyncio.Event()
    release = asyncio.Event()
    completed = asyncio.Event()
    order: list[str] = []

    async def first() -> None:
        order.append("first")
        entered.set()
        await release.wait()

    def second() -> None:
        order.append("second")
        completed.set()

    async with app.run_test() as pilot:
        app.call_after_refresh(first)
        app.call_after_refresh(second)
        await asyncio.wait_for(entered.wait(), 1)
        with app.batch_update():
            release.set()
            # The screen message pump is waiting inside first; let it proceed.
            await asyncio.sleep(0.05)
            assert order == ["first"]
            assert not completed.is_set()
        await asyncio.wait_for(completed.wait(), 1)
        assert order == ["first", "second"]
