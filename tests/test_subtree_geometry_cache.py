from unittest.mock import patch

import pytest

from textual._compositor import Compositor
from textual.app import App
from textual.containers import VerticalGroup
from textual.widgets import Static


class CachedGroup(VerticalGroup):
    CACHE_SUBTREE_GEOMETRY = True


@pytest.mark.parametrize("capacity", [0, 1, 2, 5])
async def test_geometry_budget_bounds_retention_without_changing_the_scene(capacity):
    app = App()
    async with app.run_test() as pilot:
        groups = [CachedGroup(Static(f"item {index}")) for index in range(4)]
        await app.mount(*groups)
        await pilot.pause()
        compositor = Compositor(max_subtree_geometry_entries=capacity)
        for _ in range(3):
            actual = compositor._arrange_root(app.screen, app.size)
            assert len(compositor._subtree_geometry) <= capacity
        reference = Compositor(max_subtree_geometry_entries=0)._arrange_root(app.screen, app.size)
        assert actual == reference
        compositor.max_subtree_geometry_entries = 0
        assert not compositor._subtree_geometry


async def test_unchanged_subtree_reuses_geometry_and_nested_changes_invalidate_it():
    app = App()
    async with app.run_test() as pilot:
        text = Static("one")
        group = CachedGroup(VerticalGroup(text))
        await app.mount(group)
        await pilot.pause()
        compositor = Compositor(max_subtree_geometry_entries=2)
        compositor._arrange_root(app.screen, app.size)
        with patch.object(group, "arrange", wraps=group.arrange) as arrange:
            compositor._arrange_root(app.screen, app.size)
            assert not arrange.called
        text.update("one\ntwo\nthree")
        await pilot.pause()
        with patch.object(group, "arrange", wraps=group.arrange) as arrange:
            actual = compositor._arrange_root(app.screen, app.size)
            assert arrange.called
        reference = Compositor(max_subtree_geometry_entries=0)._arrange_root(app.screen, app.size)
        assert actual == reference
        compositor.discard_widgets({text})
        assert not compositor._subtree_geometry


async def test_changed_parent_borrows_original_children_without_flat_capture():
    from dataclasses import replace
    from textual._compositor import PlacedSubtreeGeometry, SubtreeGeometryPlacement
    from textual.containers import VerticalScroll
    from textual.screen import Screen

    rows = [CachedGroup(Static(f"row {index}"), Static("wrapped " * 7))
            for index in range(20)]
    history = CachedGroup(*rows)

    class SourceScreen(Screen):
        def compose(self):
            yield VerticalScroll(history)

        def _layout_mutation_roots(self):
            return (history,) if history.lock.is_locked else ()

        def _prepare_compositor_refresh(self):
            return self._layout_mutation_roots()

    class SourceApp(App):
        CSS = "VerticalScroll { height: 10; } Static { height: auto; }"

        def get_default_screen(self):
            return SourceScreen()

    app = SourceApp()
    async with app.run_test(size=(30, 12)) as pilot:
        await pilot.pause()
        compositor = app.screen._compositor
        original = compositor._subtree_geometry[history]
        stable = rows[5]
        stable_source = original.geometry[stable][1]
        assert isinstance(stable_source, SubtreeGeometryPlacement)
        child = stable.children[1]
        assert child not in original.geometry
        assert original.contains(child)
        assert original.captured_parent(child) is stable
        # Capture the same acquired source with one original child loan. The
        # immutable lifetime must be refused at the parent's reuse owner.
        incoming_clip = stable_source.clip.source
        local = {node: (entry if isinstance(entry, SubtreeGeometryPlacement) else entry.geometry)
                 for node, (_, entry) in original.geometry.items()}
        local[stable] = replace(stable_source, source_held=True)
        loan = type(original).capture(
            original.key, local, original.widgets, original.invisible_widgets,
            {history: incoming_clip}, incoming_clip, set(),
        )
        assert loan.geometry[stable][1].source is stable_source.source
        assert loan.geometry[stable][1].source_held
        assert not loan.reusable
        assert not loan.matches(loan.key)
        assert loan.matches(loan.key, source_held=True)
        assert original.reusable
        # A missing complete child source can lend only its known placed
        # snapshot. A containing capture must not promote that scope.
        partial = PlacedSubtreeGeometry.capture(
            stable_source.key._replace(visible_only=True),
            {stable: stable_source.source.geometry[stable][1].geometry},
            frozenset({stable}), frozenset(), {}, stable_source.clip, set(),
        )
        local[stable] = replace(stable_source, source=partial, source_held=True)
        partial_loan = type(original).capture(
            original.key, local, original.widgets, original.invisible_widgets,
            {history: incoming_clip}, incoming_clip, set(),
        )
        assert partial_loan.contains(stable)
        assert not partial_loan.contains(child)
        assert not partial_loan.complete
        assert not partial_loan.matches(partial_loan.key, require_complete=True, source_held=True)

        rows[0].children[0].update("changed\nheight\nthree")
        inserted = CachedGroup(Static("new row"), Static("new second child"))
        await history.mount(inserted, before=rows[1])
        await pilot.pause()
        current = compositor._subtree_geometry[history]
        assert current is not original
        assert current.geometry[stable][1].source is stable_source.source
        assert len(current.geometry) == len(history.children) + 1
        assert child not in current.geometry
        assert current.contains(child)
        scroll = app.query_one(VerticalScroll)
        targets = (child, rows[12].children[0], rows[-1].children[-1])
        expected = {}
        for position in (0, 18, 3, 55):
            scroll.scroll_to(y=position, animate=False, immediate=True)
            await pilot.pause()
            compositor.reflow_visible(app.screen, app.size, retain_geometry=targets)
            reference = Compositor(max_subtree_geometry_entries=0)
            reference.reflow_visible(app.screen, app.size, retain_geometry=targets)
            demanded = {node for target in targets for node in target.walk_ancestors(with_self=True)}
            # Cached complete sources may retain extra empty clipped boxes.
            # Visible paint and every explicitly required reader must agree.
            def required_scene(source):
                return {node: geometry for node, geometry in source._published_map.items()
                        if geometry.visible_region or node in demanded}
            assert required_scene(compositor) == required_scene(reference)
            expected[position] = required_scene(reference)
            # Complete source membership includes offscreen descendants;
            # uncached visible traversal intentionally does not visit them.
            assert compositor.widgets == reference._arrange_root(
                app.screen, app.size, visible_only=False
            )[1]
            assert compositor.find_widget(child) == reference.find_widget(child)
        held_source = compositor._subtree_geometry[history]
        async with history.lock:
            incomplete = CachedGroup(Static("NOT_COMMITTED"))
            await history.mount(incomplete)
            await pilot.pause()
            for position in (3, 18, 55, 0):
                scroll.scroll_to(y=position, animate=False, immediate=True)
                await pilot.pause()
                compositor.reflow_visible(app.screen, app.size, retain_geometry=targets)
                assert compositor._subtree_geometry[history] is held_source
                assert not held_source.contains(incomplete)
                assert incomplete not in compositor._published_map
                assert required_scene(compositor) == expected[position]
        await incomplete.remove()
        await pilot.pause()
        compositor.reflow(app.screen, app.size)
        reference.reflow(app.screen, app.size)
        assert compositor._published_map == reference._published_map
        await stable.remove()
        await pilot.pause()
        assert stable not in compositor._subtree_geometry
        assert not any(source.contains(child) for source in compositor._subtree_geometry.values())
        assert child not in compositor._published_map


@pytest.mark.parametrize("capacity", [-1, True, 1.5, None])
def test_geometry_budget_rejects_invalid_capacities(capacity):
    with pytest.raises(ValueError, match="non-negative integer"):
        Compositor(max_subtree_geometry_entries=capacity)
