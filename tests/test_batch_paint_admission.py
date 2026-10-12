"""Real framework lifecycle checks, not installed terminal acceptance."""

import asyncio


from textual.app import App, ComposeResult
from textual.containers import Vertical
from textual.screen import Screen
from textual.widget import Widget
from textual.widgets import Label


class ObservedScreen(Screen):
    def __init__(self) -> None:
        super().__init__()
        self.preparation_batches: list[int] = []

    def _prepare_compositor_refresh(self) -> tuple[Widget, ...]:
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


async def test_admitted_refresh_callbacks_keep_sender_order_during_later_batch() -> None:
    app = BatchPaintApp()
    entered = asyncio.Event()
    release = asyncio.Event()
    completed = asyncio.Event()
    order: list[str] = []

    async def first() -> None:
        assert asyncio.current_task() is app.task
        order.append("first")
        entered.set()
        await release.wait()

    def second() -> None:
        assert asyncio.current_task() is app.task
        order.append("second")
        completed.set()

    async with app.run_test() as pilot:
        app.call_after_refresh(first)
        app.call_after_refresh(second)
        await asyncio.wait_for(entered.wait(), 1)
        with app.batch_update():
            assert order == ["first"]
            assert not completed.is_set()
            release.set()
            # Publication already admitted both callbacks. The sender owns
            # their execution and order; a later batch holds new frames,
            # not this sender's previously admitted callback messages.
            await asyncio.wait_for(completed.wait(), 1)
        assert order == ["first", "second"]


class HeldVertical(Vertical):
    """A real changing subtree refuses layout and paint until its owner releases."""

    def arrange(self, size, optimal=False):
        assert not self.lock.is_locked, "Layout descended into a mutation"
        return super().arrange(size, optimal=optimal)

    def render_lines(self, crop):
        assert not self.lock.is_locked, "Paint consumed a held source"
        return super().render_lines(crop)


class IndependentScreen(ObservedScreen):
    def __init__(self):
        super().__init__()
        self.publications = []

    def _layout_mutation_roots(self):
        return tuple(root for root in self.query(HeldVertical) if root.lock.is_locked)

    def _prepare_compositor_refresh(self):
        return self._layout_mutation_roots()

    def _on_frame_published(self, deferred_roots):
        self.publications.append(deferred_roots)


class IndependentApp(BatchPaintApp):
    CSS = """
    HeldVertical { width: 20; height: auto; }
    HeldVertical Label { height: 3; }
    #sidebar { dock: right; width: 20; height: 8; }
    """

    def get_default_screen(self):
        return IndependentScreen()

    def compose(self):
        with HeldVertical(id="holder"):
            yield Label("ORIGINAL_HELD", id="original")
        yield Label("SIDEBAR_OLD", id="sidebar")
