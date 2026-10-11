"""A layout run in steps places every widget exactly as the one-shot layout does."""

from __future__ import annotations

from textual import messages
from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual._compositor import StepDeadline
from textual.screen import Screen
from textual.widget import Widget
from textual.widgets import Label, Static


class ViewportScreen(Screen):
    def _use_viewport_layout(self) -> bool:
        return True

    def compose(self) -> ComposeResult:
        yield Static("side", id="side")
        with VerticalScroll(id="body"):
            for row in range(30):
                with Horizontal(classes="row"):
                    yield Label(f"row {row} " + "word " * (row % 7))
                    yield Label("right")
            with Vertical(id="grow"):
                yield Static("x", id="growing")


class Tree(App[None]):
    CSS = """
    #side { dock: left; width: 12; }
    #body { height: 1fr; }
    .row { height: auto; }
    .row Label { width: 1fr; }
    #grow { height: auto; }
    """

    def get_default_screen(self) -> Screen:
        return ViewportScreen()


async def request_growth(screen: Screen) -> None:
    """Grow #growing and record its layout request at once (no frame between)."""
    growing = screen.query_one("#growing", Static)
    growing.update("line\n" * 5)
    await screen._on_layout(messages.Layout(growing))
    assert screen._layout_boundaries(), "a scoped layout is pending"


def canonical(scene) -> list[tuple]:
    """A scene's geometry keyed by each widget's place in the tree."""

    def path(widget: Widget) -> tuple:
        steps = []
        node = widget
        while isinstance(node, Widget) and node.parent is not None:
            parent = node.parent
            index = parent.children.index(node) if node in parent.children else -1
            steps.append((type(node).__name__, getattr(node, "vertical", None), index))
            node = parent
        return tuple(reversed(steps))

    return sorted(
        (path(widget), geometry.region, geometry.order, geometry.clip,
         geometry.virtual_size, geometry.container_size, geometry.virtual_region,
         geometry.dock_gutter, geometry.gutter)
        for widget, geometry in scene.items()
    )


async def test_arrangement_steps_equal_one_shot() -> None:
    async with Tree().run_test(size=(60, 20)) as pilot:
        screen = pilot.app.screen
        compositor = screen._compositor
        one_shot, one_shot_widgets = compositor._arrange_root(screen, screen.size)

        deadline = StepDeadline()  # always passed: pause before every widget
        steps = compositor._arrange_steps(screen, screen.size, deadline=deadline)
        pauses = 0
        try:
            while True:
                next(steps)
                pauses += 1
                assert not compositor._arranging, "readers between steps see the committed scene"
        except StopIteration as finished:
            stepped, stepped_widgets = finished.value
        assert pauses > 20
        assert canonical(stepped) == canonical(one_shot)
        assert stepped_widgets == one_shot_widgets


async def layout_after_change(stepped: bool) -> tuple[list[tuple], int]:
    """Grow a widget, then lay out the screen in steps or at once."""
    async with Tree().run_test(size=(60, 20)) as pilot:
        screen = pilot.app.screen
        await pilot.pause()
        published = screen._compositor._visible_map
        await request_growth(screen)
        with screen.hold_frames():
            if stepped:
                pauses = 0
                original = StepDeadline.passed

                def counted(deadline: StepDeadline) -> bool:
                    nonlocal pauses
                    passed = original(deadline)
                    pauses += passed
                    return passed

                StepDeadline.passed = counted
                try:
                    await screen.layout_in_steps(step_ns=0)
                finally:
                    StepDeadline.passed = original
            else:
                pauses = 0
                screen._refresh_layout()
        assert screen._compositor._visible_map is not published
        return canonical(screen._compositor._layout_map), pauses


async def test_layout_in_steps_equals_refresh_layout() -> None:
    one_shot, _ = await layout_after_change(stepped=False)
    stepped, pauses = await layout_after_change(stepped=True)
    assert pauses > 1
    assert stepped == one_shot


async def test_scene_unpublished_until_last_step() -> None:
    async with Tree().run_test(size=(60, 20)) as pilot:
        screen = pilot.app.screen
        compositor = screen._compositor
        await pilot.pause()
        published = compositor._visible_map
        await request_growth(screen)
        seen = []
        with screen.hold_frames():
            deadline = StepDeadline()
            steps = screen._layout_steps(deadline=deadline)
            screen._stepped_layout = steps
            try:
                while True:
                    next(steps)
                    seen.append(compositor._visible_map is published)
            except StopIteration:
                pass
            finally:
                screen._stepped_layout = None
        assert seen and all(seen)
        assert compositor._visible_map is not published


async def test_request_between_steps_waits_for_next_layout() -> None:
    async with Tree().run_test(size=(60, 20)) as pilot:
        screen = pilot.app.screen
        await pilot.pause()
        await request_growth(screen)
        side = screen.query_one("#side", Static)
        with screen.hold_frames():
            deadline = StepDeadline()
            steps = screen._stepped_layout = screen._layout_steps(deadline=deadline)
            next(steps)  # paused mid-arrangement
            side.styles.width = 20
            await screen._on_layout(messages.Layout(side))
            screen._on_timer_update()  # deferred: the stepped layout is running
            assert screen._compositor._visible_map is not None
            try:
                while True:
                    next(steps)
            except StopIteration:
                pass
            screen._stepped_layout = None
        assert side in {requester for requesters in screen._layout_widgets.values()
                        for requester in requesters} or side in screen._layout_widgets
        await pilot.pause()
        assert screen.query_one("#side").region.width == 20


async def test_widget_removed_between_steps_is_not_placed() -> None:
    async with Tree().run_test(size=(60, 20)) as pilot:
        screen = pilot.app.screen
        await pilot.pause()

        def stepped_layout():
            deadline = StepDeadline()  # pause before every widget
            steps = screen._stepped_layout = screen._layout_steps(deadline=deadline)
            return steps

        def finish(steps) -> int:
            count = 0
            try:
                while True:
                    next(steps)
                    count += 1
            except StopIteration:
                screen._stepped_layout = None
            return count

        # Count the steps of this layout, then remove a widget near its end,
        # after it was placed (children are placed last row first).
        await request_growth(screen)
        with screen.hold_frames():
            total = finish(stepped_layout())
        removed = screen.query(".row")[12].query_one(Label)
        assert removed in screen._compositor._layout_map
        await request_growth(screen)
        with screen.hold_frames():
            steps = stepped_layout()
            for _ in range(total - 2):
                next(steps)
            await removed.parent.remove()
            finish(steps)
        assert removed not in screen._compositor._layout_map
        assert removed not in screen._compositor.widgets
