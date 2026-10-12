"""A layout run in steps is the one-shot layout, published once at its end.

Each scenario builds the same app twice and makes the same change; one copy
is laid out at once (`_refresh_layout`), the other a step at a time
(`layout_in_steps` or a manual driver) with deadlines that pause it many
times. The arrangement, the widget set, the retained subtree geometry and the
Resize/Show/Hide events must be identical. Until the step that commits the
arrangement, readers see the previous scene and nothing is posted; the
events are posted at the commit; the steps after it render the visible
widgets, and nothing is published before the last step.
"""

from __future__ import annotations

import asyncio
from collections import Counter

import pytest

from textual._time import after_input
from textual import events, messages
from textual._compositor import Compositor, StepDeadline
from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.screen import Screen
from textual.widget import Widget
from textual.widgets import Label, Static


class Cached(VerticalScroll):
    """A container whose arrangement is retained, as Toad's history windows are."""

    CACHE_SUBTREE_GEOMETRY = True


class Workspace(Screen):
    """A sidebar beside a long nested history, with docks and an overlay."""

    def _use_viewport_layout(self) -> bool:
        return True

    def compose(self) -> ComposeResult:
        yield Static("top", id="top")
        with Horizontal(id="main"):
            with VerticalScroll(id="side"):
                for index in range(60):
                    yield Label(f"thread {index}")
            with Cached(id="body"):
                for row in range(40):
                    with Horizontal(classes="row", id=f"row{row}"):
                        yield Label(("word " * (row % 9 + 1)).strip(), classes="text")
                        with Vertical(classes="meta"):
                            yield Static(f"meta {row}")
                            yield Static("x" * (row % 5 + 1))
                with Cached(id="inner"):
                    for index in range(10):
                        yield Label(f"inner {index} " + "w " * index, classes="text")
        yield Static("overlay", id="overlay")
        yield Static("bottom", id="bottom")


class Tree(App[None]):
    CSS = """
    Screen { layers: base over; }
    #top { dock: top; height: 1; }
    #bottom { dock: bottom; height: 1; }
    #main { height: 1fr; }
    #side { width: 20; }
    #body { width: 1fr; }
    .row { height: auto; }
    .text { width: 1fr; }
    .meta { width: 12; height: auto; }
    #inner { height: 8; }
    #overlay { layer: over; offset: 10 5; width: 20; height: 3; }
    """

    def __init__(self) -> None:
        super().__init__()
        self.handled_during_layout: list[bool] = []

    def get_default_screen(self) -> Screen:
        return Workspace()

    def on_key(self, event: events.Key) -> None:
        if event.key == "x":
            self.handled_during_layout.append(self.screen._stepped_layout is not None)


def path(widget: Widget) -> tuple:
    """A widget's place in the tree, the same in both copies of the app."""
    steps = []
    node = widget
    while isinstance(node, Widget) and node.parent is not None:
        parent = node.parent
        index = parent._nodes.index(node) if node in parent._nodes else -1
        steps.append((type(node).__name__, node.id, index))
        node = parent
    return tuple(reversed(steps))


def canonical(scene) -> list[tuple]:
    return sorted((
        (path(widget), geometry.region, geometry.order, geometry.clip,
         geometry.virtual_size, geometry.container_size, geometry.virtual_region,
         geometry.dock_gutter, geometry.gutter)
        for widget, geometry in scene.items()
    ), key=repr)


def outcome(screen: Screen) -> dict:
    """Everything a layout leaves behind, keyed by tree position."""
    compositor = screen._compositor
    return {
        "layout_map": canonical(compositor._layout_map),
        "visible_map": None if compositor._visible_map is None
        else canonical(compositor._visible_map),
        "widgets": sorted((path(widget) for widget in compositor.widgets), key=repr),
        "retained": sorted((path(widget) for widget in compositor._subtree_geometry), key=repr),
        "sizes": sorted(((path(widget), widget.size, widget.virtual_size)
                         for widget in screen.walk_children(Widget)), key=repr),
    }


async def change(screen: Screen) -> None:
    """Widen the sidebar (every history row rewraps), hide one row, show another.

    Layout requests are recorded at once, with no frame between the change
    and the layout under test. Every request's boundary is below the screen,
    so the screen re-arranges those subtrees (`reflow_subtrees`).
    """
    side = screen.query_one("#side")
    side.styles.width = 34
    hidden = screen.query_one("#row3")
    hidden.display = False
    await screen._on_layout(messages.Layout(side))
    await screen._on_layout(messages.Layout(hidden))
    assert screen._layout_boundaries(), "a scoped layout is pending"


class Posted:
    """Resize, Show and Hide posts, with how many pauses preceded each."""

    def __init__(self, monkeypatch) -> None:
        self.pauses = 0
        self.events: list[tuple[int, tuple, str, tuple]] = []
        passed = StepDeadline.passed

        def counted(deadline: StepDeadline) -> bool:
            result = passed(deadline)
            self.pauses += result
            return result

        post_message = Widget.post_message

        def recorded(widget: Widget, message) -> bool:
            if isinstance(message, (events.Resize, events.Show, events.Hide)):
                detail = ((message.size, message.virtual_size, message.container_size)
                          if isinstance(message, events.Resize) else ())
                self.events.append((self.pauses, path(widget), type(message).__name__, detail))
            return post_message(widget, message)

        monkeypatch.setattr(StepDeadline, "passed", counted)
        monkeypatch.setattr(Widget, "post_message", recorded)

    def posted(self) -> Counter:
        return Counter(event[1:] for event in self.events)


def refuse_full_reflow(monkeypatch) -> None:
    """The scenario must take the scoped path that runs in steps."""

    def refused(*args, **kwargs):
        raise AssertionError("expected a scoped reflow")

    monkeypatch.setattr(Compositor, "reflow_steps", refused)


async def laid_out(monkeypatch, step_ns: int | None) -> tuple[dict, Posted]:
    """The app after `change`, laid out at once (None) or in steps of `step_ns`.

    Only the layout under test must be scoped: a later layout the app runs
    for its own pending requests is not part of the comparison.
    """
    async with Tree().run_test(size=(100, 30)) as pilot:
        screen = pilot.app.screen
        await pilot.pause()
        await change(screen)
        with monkeypatch.context() as patch:
            refuse_full_reflow(patch)
            posted = Posted(patch)
            with screen.hold_frames():
                if step_ns is None:
                    screen._refresh_layout()
                else:
                    await screen.layout_in_steps(step_ns=step_ns)
        return outcome(screen), posted


@pytest.mark.parametrize("step_ns", [0, 20_000])
async def test_layout_in_steps_equals_refresh_layout(monkeypatch, step_ns) -> None:
    one_shot, one_shot_posted = await laid_out(monkeypatch, None)
    stepped, stepped_posted = await laid_out(monkeypatch, step_ns)
    assert stepped_posted.pauses > (40 if step_ns == 0 else 3)
    assert stepped == one_shot
    # Every event the one-shot layout posts, posted once, all in the step that commits.
    assert stepped_posted.posted() == one_shot_posted.posted()
    assert max(stepped_posted.posted().values()) == 1
    assert {"Resize", "Hide"} <= {kind for _, kind, _ in stepped_posted.posted()}
    assert len({pauses for pauses, *_ in stepped_posted.events}) == 1


async def test_arrangement_steps_equal_one_shot() -> None:
    """Pausing before every widget: the same map and widgets as one call."""
    results = []
    for stepped in (False, True):
        async with Tree().run_test(size=(100, 30)) as pilot:
            screen = pilot.app.screen
            compositor = screen._compositor
            compositor._subtree_geometry.clear()
            if not stepped:
                results.append(compositor._arrange_root(screen, screen.size))
                continue
            steps = compositor._arrange_steps(screen, screen.size, deadline=StepDeadline())
            pauses = 0
            try:
                while True:
                    next(steps)
                    pauses += 1
                    assert compositor._arranging, "a paused arrangement is still in progress"
            except StopIteration as finished:
                results.append(finished.value)
            assert not compositor._arranging
            assert pauses > 40
    (one_shot, one_shot_widgets), (stepped_map, stepped_widgets) = results
    assert canonical(stepped_map) == canonical(one_shot)
    assert sorted(map(path, stepped_widgets), key=repr) == sorted(map(path, one_shot_widgets), key=repr)


def drive(screen: Screen):
    """Start a stepped layout that pauses before every widget."""
    steps = screen._stepped_layout = screen._layout_steps(deadline=StepDeadline())
    next(steps)
    return steps


def finish(screen: Screen, steps) -> int:
    count = 0
    try:
        while True:
            next(steps)
            count += 1
    except StopIteration:
        screen._stepped_layout = None
    return count


async def test_readers_between_steps_see_the_previous_scene(monkeypatch) -> None:
    one_shot, _ = await laid_out(monkeypatch, None)
    async with Tree().run_test(size=(100, 30)) as pilot:
        screen = pilot.app.screen
        compositor = screen._compositor
        await pilot.pause()
        maps = (compositor._layout_map, compositor._visible_map, compositor._published_map)
        copies = tuple(dict(scene) for scene in maps)
        visible = dict(compositor.visible_widgets)
        published = dict(compositor.published_widgets)
        points = [(x, y) for x in range(0, 100, 7) for y in range(0, 30, 3)]
        hits = [screen.get_widget_at(x, y) for x, y in points]
        offsets = [screen.get_widget_and_offset_at(x, y) for x, y in points]
        offscreen = next(widget for widget in screen.walk_children(Widget)
                         if widget not in compositor._layout_map)
        regions = {widget: widget.region for widget in compositor._layout_map}
        await change(screen)
        with monkeypatch.context() as patch:
            refuse_full_reflow(patch)
            with screen.hold_frames():
                steps = drive(screen)
                pauses = 0
                rendering = 0
                try:
                    while True:
                        if compositor._visible_map is not maps[1]:
                            # Committed: the remaining steps only render.
                            committed = compositor._visible_map
                            rendering += 1
                            assert compositor._published_map is maps[2]
                            next(steps)
                            assert compositor._visible_map is committed
                            continue
                        # Readers that could arrange lazily must not.
                        try:
                            screen.find_widget(offscreen)
                        except Exception:
                            pass
                        compositor.full_map
                        screen.focus_next()
                        assert (compositor._layout_map, compositor._visible_map,
                                compositor._published_map) == maps
                        assert all(scene is kept for scene, kept in zip(
                            (compositor._layout_map, compositor._visible_map,
                             compositor._published_map), maps))
                        assert tuple(dict(scene) for scene in maps) == copies
                        assert compositor.visible_widgets == visible
                        assert compositor.published_widgets == published
                        if pauses % 25 == 0:
                            assert [screen.get_widget_at(x, y) for x, y in points] == hits
                            assert [screen.get_widget_and_offset_at(x, y)
                                    for x, y in points] == offsets
                            assert {widget: widget.region for widget in regions} == regions
                        pauses += 1
                        next(steps)
                except StopIteration:
                    screen._stepped_layout = None
                assert pauses > 40
                assert rendering > 3, "the visible widgets render in steps after the commit"
                assert not compositor._arranging
                assert outcome(screen)["layout_map"] == one_shot["layout_map"]
                assert compositor._visible_map is not maps[1]


async def test_input_between_steps_is_handled(monkeypatch) -> None:
    one_shot, _ = await laid_out(monkeypatch, None)
    async with Tree().run_test(size=(100, 30)) as pilot:
        app = pilot.app
        screen = app.screen
        await pilot.pause()
        await change(screen)
        with screen.hold_frames():
            layout = asyncio.create_task(screen.layout_in_steps(step_ns=0))
            await asyncio.sleep(0)
            assert screen._stepped_layout is not None
            app.post_message(events.Key("x", "x"))
            await layout
        assert app.handled_during_layout == [True]
        assert outcome(screen)["layout_map"] == one_shot["layout_map"]


async def test_request_between_steps_waits_for_next_layout() -> None:
    async with Tree().run_test(size=(100, 30)) as pilot:
        screen = pilot.app.screen
        await pilot.pause()
        await change(screen)
        top = screen.query_one("#top")
        with screen.hold_frames():
            steps = drive(screen)
            top.styles.height = 2
            await screen._on_layout(messages.Layout(top))
            screen._on_timer_update()  # deferred: the stepped layout is running
            finish(screen, steps)
        assert screen._layout_widgets, "the request made between steps is still pending"
        assert top.region.height == 1
        await pilot.pause()
        assert top.region.height == 2


async def removed_between_steps(monkeypatch, fraction: float | None, selector: str) -> dict:
    """Remove a widget after `fraction` of the layout's steps (None: before it)."""
    async with Tree().run_test(size=(100, 30)) as pilot:
        screen = pilot.app.screen
        await pilot.pause()
        removed = screen.query_one(selector)
        if fraction is None:
            await removed.remove()
            await change(screen)
            with screen.hold_frames():
                screen._refresh_layout()
        else:
            await change(screen)
            with screen.hold_frames():
                total = finish(screen, drive(screen))
            # The same change again, removing the widget part way through.
            screen.query_one("#side").styles.width = 20
            screen.query_one("#row3").display = True
            await pilot.pause()
            await change(screen)
            with screen.hold_frames():
                steps = drive(screen)
                for _ in range(int(total * fraction)):
                    next(steps)
                await removed.remove()
                finish(screen, steps)
            assert removed not in screen._compositor._layout_map
            assert removed not in screen._compositor.widgets
            assert not any(removed in geometry.ancestors
                           for geometry in screen._compositor._layout_map.values()
                           if hasattr(geometry, "ancestors"))
        await pilot.pause()
        return outcome(screen)


@pytest.mark.parametrize("selector", ["#row1", "#row38", "#inner"])
@pytest.mark.parametrize("fraction", [0.02, 0.5, 0.95])
async def test_widget_removed_between_steps(monkeypatch, selector, fraction) -> None:
    """Removed before or after its placement, in or out of a retained subtree:
    the scene leaves it out, and the next layout is the one-shot result."""
    expected = await removed_between_steps(monkeypatch, None, selector)
    assert await removed_between_steps(monkeypatch, fraction, selector) == expected


async def test_direct_layout_replaces_a_paused_one() -> None:
    async with Tree().run_test(size=(100, 30)) as pilot:
        screen = pilot.app.screen
        compositor = screen._compositor
        await pilot.pause()
        await change(screen)
        with screen.hold_frames():
            steps = drive(screen)
            assert compositor._arranging
            screen._refresh_layout()
            assert screen._stepped_layout is None
            assert not compositor._arranging
            assert compositor._discarded_between_steps is None
            with pytest.raises(StopIteration):
                next(steps)


async def test_a_second_stepped_layout_replaces_a_paused_one() -> None:
    async with Tree().run_test(size=(100, 30)) as pilot:
        screen = pilot.app.screen
        compositor = screen._compositor
        await pilot.pause()
        await change(screen)
        with screen.hold_frames():
            first = asyncio.create_task(screen.layout_in_steps(step_ns=0))
            await asyncio.sleep(0)
            paused = screen._stepped_layout
            assert paused is not None
            await screen.layout_in_steps(step_ns=0)
            await first
            with pytest.raises(StopIteration):
                next(paused)
        assert screen._stepped_layout is None
        assert not compositor._arranging
        assert compositor._discarded_between_steps is None


async def test_timer_layout_runs_in_steps(monkeypatch) -> None:
    """A requested layout longer than a step (the screen's update timer) runs
    over loop turns: input is handled between steps, no frame is written
    until the last step, and the result is the one-shot layout's."""
    one_shot, one_shot_posted = await laid_out(monkeypatch, None)
    async with Tree().run_test(size=(100, 30)) as pilot:
        app = pilot.app
        screen = app.screen
        await pilot.pause()
        await change(screen)
        with monkeypatch.context() as patch:
            posted = Posted(patch)
            patch.setattr(Workspace, "LAYOUT_STEP_NS", 0)
            frames = []
            display = type(app)._display

            def counted(self, screen, renderable):
                frames.append(posted.pauses)
                return display(self, screen, renderable)

            patch.setattr(type(app), "_display", counted)
            with monkeypatch.context() as scoped:
                refuse_full_reflow(scoped)
                screen._on_timer_update()
                remaining = screen._stepped_layout_task
                assert screen._stepped_layout is not None and remaining is not None
                assert not screen._layout_required, "the running layout took the request"
                app.post_message(events.Key("x", "x"))
                await remaining
            paused = posted.pauses
            await pilot.pause()
        assert screen._stepped_layout is None and screen._stepped_layout_task is None
        assert paused > 40
        assert app.handled_during_layout == [True]
        assert frames and min(frames) >= paused, "no frame before the last step"
        assert outcome(screen)["layout_map"] == one_shot["layout_map"]
        assert posted.posted() == one_shot_posted.posted()


async def change_screen(screen: Screen) -> None:
    """Change the docked top bar's height: the request reaches the screen,
    which re-arranges everything (`reflow`), and the history rewraps."""
    top = screen.query_one("#top")
    top.styles.height = 2
    screen.query_one("#side").styles.width = 34
    await screen._on_layout(messages.Layout(top))
    await screen._on_layout(messages.Layout(screen.query_one("#side")))
    assert screen._layout_boundaries() is None, "the request reaches the screen"


async def fully_laid_out(monkeypatch, step_ns: int | None) -> tuple[dict, Posted, list]:
    """The app after `change_screen`, laid out at once (None) or in steps of `step_ns`."""
    async with Tree().run_test(size=(100, 30)) as pilot:
        screen = pilot.app.screen
        await pilot.pause()
        await change_screen(screen)
        with monkeypatch.context() as patch:
            full = []
            reflow_steps = Compositor.reflow_steps

            def recorded(self, *args, **kwargs):
                full.append(kwargs.get("deadline") is not None)
                return (yield from reflow_steps(self, *args, **kwargs))

            patch.setattr(Compositor, "reflow_steps", recorded)
            posted = Posted(patch)
            with screen.hold_frames():
                if step_ns is None:
                    screen._refresh_layout()
                else:
                    await screen.layout_in_steps(step_ns=step_ns)
        return outcome(screen), posted, full


@pytest.mark.parametrize("step_ns", [0, 20_000])
async def test_full_layout_in_steps_equals_refresh_layout(monkeypatch, step_ns) -> None:
    one_shot, one_shot_posted, one_shot_full = await fully_laid_out(monkeypatch, None)
    stepped, stepped_posted, stepped_full = await fully_laid_out(monkeypatch, step_ns)
    # The layout under test (later layouts follow requests its events made).
    assert one_shot_full[0] is False and stepped_full[0] is True
    assert stepped_posted.pauses > (40 if step_ns == 0 else 3)
    assert stepped == one_shot
    assert stepped_posted.posted() == one_shot_posted.posted()
    assert len({pauses for pauses, *_ in stepped_posted.events}) == 1


async def test_readers_between_full_layout_steps_see_the_previous_scene() -> None:
    async with Tree().run_test(size=(100, 30)) as pilot:
        screen = pilot.app.screen
        compositor = screen._compositor
        await pilot.pause()
        maps = (compositor._layout_map, compositor._visible_map, compositor._published_map)
        copies = tuple(dict(scene) for scene in maps)
        root, size = compositor.root, compositor.size
        top = screen.query_one("#top")
        await change_screen(screen)
        with screen.hold_frames():
            steps = drive(screen)
            pauses = 0
            try:
                while True:
                    if compositor._layout_map is not maps[0]:
                        # Committed: the remaining steps only render.
                        next(steps)
                        continue
                    compositor.full_map
                    assert (compositor.root, compositor.size) == (root, size)
                    assert tuple(dict(scene) for scene in (
                        compositor._layout_map, compositor._visible_map,
                        compositor._published_map)) == copies
                    assert top.region.height == 1
                    pauses += 1
                    next(steps)
            except StopIteration:
                screen._stepped_layout = None
        assert pauses > 40
        assert not compositor._arranging
        assert top.region.height == 2



async def test_retained_subtree_projection_pauses_between_entries() -> None:
    """Re-arranging from retained subtree geometry projects it in steps too,
    and the result is the one-shot arrangement's."""
    async with Tree().run_test(size=(100, 30)) as pilot:
        screen = pilot.app.screen
        compositor = screen._compositor
        await pilot.pause()
        compositor._arrange_root(screen, screen.size)  # Retains #body and #inner.
        assert compositor._subtree_geometry
        one_shot = compositor._arrange_root(screen, screen.size)
        outside = sum(1 for widget in screen.walk_children(Widget)
                      if not any(isinstance(node, Cached) for node in widget.ancestors_with_self))
        steps = compositor._arrange_steps(screen, screen.size, deadline=StepDeadline())
        pauses = 0
        try:
            while True:
                next(steps)
                pauses += 1
        except StopIteration as finished:
            stepped = finished.value
        assert pauses > outside + 10, "the retained subtree's entries are projected in steps"
        assert canonical(stepped[0]) == canonical(one_shot[0])
        assert sorted(map(path, stepped[1]), key=repr) == sorted(map(path, one_shot[1]), key=repr)


async def test_a_repaint_between_steps_publishes_with_the_layout() -> None:
    async with Tree().run_test(size=(100, 30)) as pilot:
        screen = pilot.app.screen
        await pilot.pause()
        await change(screen)
        top = screen.query_one("#top", Static)
        compositor = screen._compositor
        published = []
        refresh = screen._compositor_refresh

        def publish():
            published.append(set(compositor._dirty_regions))
            refresh()

        screen._compositor_refresh = publish
        try:
            steps = drive(screen)
            # The widget's refresh, delivered to the screen between steps.
            top.refresh()
            top._check_refresh()
            await screen._on_update(messages.Update(top))
            assert top in screen._dirty_widgets
            finish(screen, steps)
        finally:
            del screen._compositor_refresh
        # The publication covers the widget repainted between the steps;
        # publishing cleared its request, so it is not left for later.
        [damage] = published
        assert any(region.contains_region(top.region) for region in damage)
        assert top not in screen._dirty_widgets


async def test_timer_update_after_a_layout_step_waits_for_the_loop_to_read_input() -> None:
    """Two units of layout work do not run back to back.

    The update timer is often due right behind a layout's last step. The
    loop runs what was scheduled during a turn before the input it reads in
    the next, so a layout started then would run ahead of input that arrived
    during the step: the two would be one wait.
    """
    async with Tree().run_test(size=(100, 30)) as pilot:
        await pilot.pause()
        screen = pilot.app.screen
        screen._refresh_layout()
        order = []
        start = screen._start_stepped_layout

        def record(*args, **kwargs):
            order.append("layout")
            return start(*args, **kwargs)

        screen._start_stepped_layout = record
        try:
            # A layout step (here of a layout with nothing left to do).
            assert screen._layout_step(iter(()), StepDeadline(), screen.LAYOUT_STEP_NS)
            # Input and timers the loop finds in its next turn run as this does.
            asyncio.get_running_loop().call_later(0, order.append, "input")
            screen._layout_required = True
            screen._on_timer_update()
            assert not order and screen._layout_required
            # Scheduled during this turn, so it runs before that input.
            await asyncio.sleep(0)
            screen._on_timer_update()
            assert not order
            await asyncio.sleep(0.01)
            assert order == ["input", "layout"]
            # With the input read, the timer starts a layout at once.
            del order[:]
            screen._stop_stepped_layout()
            screen._layout_required = True
            screen._on_timer_update()
            assert order == ["layout"]
        finally:
            del screen._start_stepped_layout


async def test_after_input_resumes_behind_what_arrived_during_the_step() -> None:
    """A step that waits with `after_input` lets the due timers run first.

    `asyncio.sleep(0)` resumes ahead of them, which is why the steps of a
    layout do not use it.
    """
    loop = asyncio.get_running_loop()
    order: list[str] = []

    async def stepped(wait) -> None:
        # Arrives while the step runs.
        loop.call_later(0, order.append, "input")
        await wait()
        order.append("next step")

    await stepped(lambda: asyncio.sleep(0))
    await after_input()
    assert order == ["next step", "input"]
    del order[:]
    await stepped(after_input)
    assert order == ["input", "next step"]
