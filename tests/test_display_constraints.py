from unittest.mock import patch

from textual.app import App
from textual.containers import HorizontalGroup, VerticalGroup, VerticalScroll
from textual.widgets import Static


async def test_display_constraints_compose_and_preserve_current_authored_styles():
    app = App()
    async with app.run_test() as pilot:
        child = Static("body")
        await app.mount(child)
        await pilot.pause()
        child.set_display_constraint("filter", False)
        child.set_display_constraint("permission", False)
        assert not child.display
        child.set_display_constraint("filter", True)
        assert not child.display
        child.styles.display = "none"
        child.set_display_constraint("permission", True)
        assert not child.display
        child.styles.display = "block"
        assert child.display


async def test_constraint_updates_native_layout_without_restyling_subtrees():
    app = App()
    async with app.run_test() as pilot:
        nested = Static("nested")
        block = VerticalGroup(nested)
        following = Static("following")
        await app.mount(block, following)
        await pilot.pause()
        before = following.region.y
        with patch.object(app.stylesheet, "apply", wraps=app.stylesheet.apply) as apply:
            block.set_display_constraint("filter", False)
            await pilot.pause()
            assert following.region.y < before
            assert block not in app.screen._compositor.visible_widgets
            assert block not in app.screen.displayed_children
            block.set_display_constraint("filter", True)
            await pilot.pause()
            assert following.region.y == before
            assert block in app.screen._compositor.visible_widgets
            assert apply.call_count == 0


async def test_constraint_reflows_following_sibling_in_group():
    app = App()
    async with app.run_test() as pilot:
        first, middle, third = (Static(text) for text in ("first", "middle", "third"))
        for child in (first, middle, third):
            child.styles.height = 1
        await app.mount(VerticalGroup(first, middle, third))
        await pilot.pause()
        middle.set_display_constraint("t", False)
        await pilot.pause()
        assert third.region.y == first.region.y + 1


async def test_nested_auto_height_members_release_hidden_row_space():
    app = App()
    rows = [Static(name) for name in ("first", "second", "third")]
    for row in rows:
        row.styles.height = 2
    header = HorizontalGroup(Static("group"))
    header.styles.height = 1
    members = VerticalGroup(*rows)
    group = VerticalGroup(header, members)
    following = Static("following")
    following.styles.height = 1
    viewport = VerticalScroll(group, following)
    viewport.CACHE_SUBTREE_GEOMETRY = True
    async with app.run_test() as pilot:
        await app.mount(viewport)
        await pilot.pause()
        assert members.region.height == 6
        assert group.region.height == 7
        for row in rows[:2]:
            row.set_display_constraint("sidebar-search", False)
        await pilot.pause()
        assert members.region.height == 2
        assert group.region.height == 3
        assert rows[2].region.y == header.region.bottom
        assert following.region.y == group.region.bottom
        for row in rows[:2]:
            row.set_display_constraint("sidebar-search", True)
        await pilot.pause()
        assert members.region.height == 6
        assert group.region.height == 7
        rows[0].remove()
        rows[1].remove()
        await pilot.pause()
        assert len(members.children) == 1
        assert members.region.height == 2
        assert group.region.height == 3
        assert rows[2].region.y == header.region.bottom


async def test_initial_constraint_and_relative_child_measurement():
    app = App()
    async with app.run_test() as pilot:
        child = Static("relative")
        child.styles.height = "1fr"
        parent = VerticalGroup(child)
        child.set_display_constraint("filter", False)
        await app.mount(parent)
        await pilot.pause()
        assert not parent._has_relative_children_height
        child.set_display_constraint("filter", True)
        assert parent._has_relative_children_height
