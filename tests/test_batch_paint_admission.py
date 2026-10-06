"""Real framework lifecycle checks, not installed terminal acceptance."""

import asyncio

from textual.app import App, ComposeResult
from textual.containers import Vertical
from textual.screen import ModalScreen, Screen
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


async def test_translucent_foreground_respects_background_resource_admission() -> None:
    class SourceScreen(ObservedScreen):
        def _prepare_compositor_refresh(self) -> tuple[Widget, ...]:
            holder = self.query_one("#holder")
            return (holder,) if holder.lock.is_locked else super()._prepare_compositor_refresh()

    class SourceApp(BatchPaintApp):
        def get_default_screen(self) -> Screen:
            return SourceScreen()

    app = SourceApp()
    async with app.run_test(size=(50, 12)) as pilot:
        holder = app.query_one("#holder", Vertical)
        source = app.screen
        await app.push_screen(ModalScreen())
        await pilot.pause()
        assert source in app._background_screens
        foreground = app.screen
        async with holder.lock:
            foreground._compositor._dirty_regions.add(foreground.size.region)
            damage = set(foreground._compositor._dirty_regions)
            app.frames.clear()
            foreground._compositor_refresh()
            assert not app.frames
            assert foreground._compositor._dirty_regions == damage
        foreground._compositor_refresh()
        assert app.frames
        assert not foreground._compositor._dirty_regions


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


async def test_partial_publication_keeps_geometry_and_owner_callbacks():
    from textual._compositor import ChopsUpdate
    from textual.geometry import Region

    app = IndependentApp()
    held_done, parent_done, scene_done, sidebar_done = (asyncio.Event() for _ in range(4))
    async with app.run_test(size=(40, 8)) as pilot:
        await pilot.pause()
        screen = app.screen
        holder = app.query_one(HeldVertical)
        original = app.query_one("#original")
        sidebar = app.query_one("#sidebar", Label)
        compositor = screen._compositor
        before = compositor.find_widget(holder)
        original_geometry = compositor.find_widget(original)
        original_hit = compositor.get_widget_at(15, 1)[0]
        app.frames.clear()
        screen.publications.clear()
        async with holder.lock:
            await holder.mount(Label("NEW_HELD", id="new"))
            sidebar.update("SIDEBAR_NEW")
            original.call_after_refresh(held_done.set)
            holder.call_after_refresh(parent_done.set)
            app.call_after_refresh(scene_done.set)
            sidebar.call_after_refresh(sidebar_done.set)
            await asyncio.wait_for(sidebar_done.wait(), 2)
            assert not held_done.is_set() and not parent_done.is_set() and not scene_done.is_set()
            assert compositor.find_widget(holder) == before
            assert compositor.find_widget(original) == original_geometry
            assert compositor.get_widget_at(1, 1)[0] is original
            assert screen.publications and all(roots == (holder,) for roots in screen.publications)
            assert compositor._dirty_regions
            compositor._dirty_regions.add(compositor.size.region)
            update = compositor.render_update(excluded_regions=compositor.deferred_regions((holder,)))
            assert isinstance(update, ChopsUpdate)
            cells = list(ChopsUpdate._span_cuts(update.spans, update.cuts, 0))
            assert all(not Region(x1, y, x2 - x1, 1).overlaps(before.visible_region)
                       for y, x1, x2 in cells)
            assert "SIDEBAR_NEW" in update.render_segments(app.console)
            assert "ORIGINAL_HELD" not in update.render_segments(app.console)
            # Repeated idle delivery is quiescent: holding a callback never
            # schedules itself, and held-only damage doesn't resume the timer.
            await pilot.pause(0.05)
            assert screen._update_timer._active.is_set() is False
            # A sibling can acquire new layout overlapping held pixels. The
            # terminal still shows the borrowed subtree there; hit lookup must
            # not expose the sibling's unpainted part early.
            sidebar.styles.width = 30
            await pilot.pause()
            assert compositor.get_widget_at(15, 1)[0] is original_hit
        holder.refresh(layout=True)
        await asyncio.wait_for(scene_done.wait(), 2)
        assert held_done.is_set() and parent_done.is_set()
        assert screen.publications[-1] == ()
        assert not compositor._dirty_regions
        assert compositor.find_widget(holder).region.height == 6


async def test_inline_partial_cells_preserve_held_content_and_clear_after_release():
    from textual._compositor import InlineUpdate

    app = IndependentApp()
    async with app.run_test(size=(40, 8)) as pilot:
        await pilot.pause()
        compositor = app.screen._compositor
        holder = app.query_one(HeldVertical)
        async with holder.lock:
            update = compositor.render_inline(app.size, clear=True,
                excluded_regions=compositor.deferred_regions((holder,)))
            assert isinstance(update, InlineUpdate)
            rendered = update.render_segments(app.console)
            assert "SIDEBAR_OLD" in rendered and "ORIGINAL_HELD" not in rendered
            assert "\x1b[J" not in rendered
            assert compositor._dirty_regions
        rendered = compositor.render_inline(app.size, clear=True).render_segments(app.console)
        assert "ORIGINAL_HELD" in rendered and "\x1b[J" in rendered
        assert not compositor._dirty_regions


async def test_partial_translucent_publication_never_reads_held_backdrop():
    from textual._compositor import ChopsUpdate
    from textual.geometry import Region

    app = IndependentApp()
    async with app.run_test(size=(40, 8)) as pilot:
        await pilot.pause()
        source = app.screen
        holder = app.query_one(HeldVertical)
        held = holder.region
        await app.push_screen(ModalScreen())
        await pilot.pause()
        foreground = app.screen
        async with holder.lock:
            compositor = foreground._compositor
            compositor._dirty_regions.add(compositor.size.region)
            regions = source._compositor.deferred_regions((holder,))
            # Exercise the original Screen publication including its nested
            # BackgroundScreen renderer, not only the isolated damage function.
            app.frames.clear()
            foreground._compositor_refresh()
            assert app.frames
            assert compositor._dirty_regions
            with source._compositor._using_exclusions(regions):
                update = compositor.render_update(full=True, screen_stack=[source], excluded_regions=regions)
            assert isinstance(update, ChopsUpdate)
            assert all(not Region(x1, y, x2 - x1, 1).overlaps(held)
                       for y, x1, x2 in ChopsUpdate._span_cuts(update.spans, update.cuts, 0))
            assert "SIDEBAR_OLD" in update.render_segments(app.console)
        foreground.refresh()
        await pilot.pause()
        assert not foreground._compositor._dirty_regions
