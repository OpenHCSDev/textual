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


@pytest.mark.parametrize("capacity", [-1, True, 1.5, None])
def test_geometry_budget_rejects_invalid_capacities(capacity):
    with pytest.raises(ValueError, match="non-negative integer"):
        Compositor(max_subtree_geometry_entries=capacity)
