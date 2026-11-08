"""Scrolling borrows complete native child geometry without recapturing it."""

from collections import Counter

from textual._compositor import Compositor, ScrolledGeometry, run_steps
from textual.app import App
from textual.containers import VerticalGroup, VerticalScroll
from textual.widgets import Static


class ArrangedGroup(VerticalGroup):
    calls: Counter = Counter()

    def arrange(self, size, optimal=False):
        self.calls[self] += 1
        return super().arrange(size, optimal=optimal)


class RetainedHistory(VerticalScroll):
    CACHE_SUBTREE_GEOMETRY = True


class ScrollingApp(App):
    CSS = "RetainedHistory { height: 12; } ArrangedGroup, Static { height: auto; }"

    def compose(self):
        with RetainedHistory():
            for row in range(20):
                with ArrangedGroup():
                    with ArrangedGroup():
                        yield Static(f"row {row}", id=f"row-{row}")
                        yield Static("second line")


async def test_scroll_reuses_complete_child_arrangements_and_remeasures_changed_content():
    app = ScrollingApp()
    async with app.run_test(size=(45, 16)) as pilot:
        await pilot.pause()
        screen = app.screen
        history = app.query_one(RetainedHistory)
        native = screen._compositor
        native.reflow(screen, screen.size)
        captured = native._subtree_geometry[history]
        native.reflow_visible(screen, screen.size)
        assert native._subtree_geometry[history] is captured
        reference = Compositor(max_subtree_geometry_entries=0)
        ArrangedGroup.calls.clear()
        for y in (3, 11, 20, 0):
            history.scroll_to(y=y, animate=False, immediate=True)
            assert run_steps(native.reflow_subtrees_steps(
                screen, screen.size, (history,), demand=ScrolledGeometry)) is not None
            reference.reflow_visible(screen, screen.size)
            assert native._layout_map == reference._layout_map
            assert tuple(native.render_strips()) == tuple(reference.render_strips())
        # The reference arrangements above are counted too; measure one native
        # scroll alone after the exact scene/cell comparison.
        ArrangedGroup.calls.clear()
        history.scroll_to(y=5, animate=False, immediate=True)
        run_steps(native.reflow_subtrees_steps(
            screen, screen.size, (history,), demand=ScrolledGeometry))
        assert not ArrangedGroup.calls
        assert native._subtree_geometry[history] is captured

        app.query_one("#row-4", Static).update("changed\ncontent\nheight")
        ArrangedGroup.calls.clear()
        run_steps(native.reflow_subtrees_steps(
            screen, screen.size, (history,), demand=ScrolledGeometry))
        assert ArrangedGroup.calls, "changed content must not borrow stale geometry"
        reference.reflow_visible(screen, screen.size)
        assert native._layout_map == reference._layout_map
        assert tuple(native.render_strips()) == tuple(reference.render_strips())
