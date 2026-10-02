from unittest.mock import patch

from textual import errors
from textual.app import App
from textual.containers import VerticalGroup, VerticalScroll
from textual.screen import Screen
from textual.widgets import Static


class TargetedScreen(Screen):
    CSS = "VerticalScroll { width: 1fr; } VerticalGroup, Static { height: auto; }"
    targets = ()

    def _use_viewport_layout(self):
        return True

    def _layout_geometry_targets(self):
        return self.targets

    def compose(self):
        with VerticalScroll(id="history"):
            for index in range(100):
                with VerticalGroup(id=f"group-{index}"):
                    yield Static(f"Row {index}: " + "wrapped text " * 10, id=f"row-{index}")
                    yield Static("second line " * 5)


async def test_offscreen_targets_match_full_geometry_without_full_tree_traversal():
    app = App()
    async with app.run_test(size=(80, 25)) as pilot:
        screen = TargetedScreen()
        await app.push_screen(screen)
        await pilot.pause()
        history = screen.query_one("#history", VerticalScroll)
        target = screen.query_one("#row-85", Static)
        screen.targets = (target,)
        for width, scroll in ((80, 0), (55, 30), (100, 250), (65, 0)):
            await pilot.resize_terminal(width, 25)
            history.scroll_to(y=scroll, immediate=True, animate=False)
            screen.refresh(layout=True)
            await pilot.pause()
            # Both layout and scrolling retain the original declared boxes.
            screen._refresh_layout(app.size)
            compositor = screen._compositor
            # Scrolling consumes the same original target declaration. Its
            # fast path must not discard the offscreen box just established.
            with patch.object(compositor, "reflow_visible", wraps=compositor.reflow_visible) as scroll_reflow:
                screen._refresh_layout(app.size, scroll=True)
                assert scroll_reflow.call_count == 1
            assert target in compositor._visible_map
            assert screen.query_one("#row-50") not in compositor._visible_map
            assert len(compositor._visible_map) < 80
            with patch.object(compositor, "_arrange_root", side_effect=AssertionError("Anchor query rebuilt all geometry")):
                actual_target = compositor.find_widget(target)
                rendered = tuple(tuple(strip) for strip in compositor.render_strips())
            compositor.reflow(screen, app.size)
            expected_target = compositor.find_widget(target)
            assert actual_target.region == expected_target.region
            assert actual_target.virtual_region == expected_target.virtual_region
            assert rendered == tuple(tuple(strip) for strip in compositor.render_strips())


async def test_foreign_and_removed_targets_do_not_enter_the_scene():
    app = App()
    async with app.run_test() as pilot:
        screen = TargetedScreen()
        await app.push_screen(screen)
        await pilot.pause()
        target = screen.query_one("#row-85")
        await target.remove()
        foreign = Static("foreign")
        screen.targets = (target, foreign)
        screen._refresh_layout(app.size)
        screen._refresh_layout(app.size, scroll=True)
        assert target not in screen._compositor._visible_map
        assert foreign not in screen._compositor._visible_map
        for body in (target, foreign):
            try:
                screen._compositor.render_subtree_strips(body)
            except errors.NoWidget:
                pass
            else:
                raise AssertionError("An unmounted body acquired native capture geometry")


async def test_capture_requires_publication_while_position_queries_keep_lazy_layout():
    app = App()
    async with app.run_test(size=(80, 25)) as pilot:
        screen = TargetedScreen()
        await app.push_screen(screen)
        await pilot.pause()
        body = screen.query_one("#group-85", VerticalGroup)
        screen._refresh_layout(app.size)
        compositor = screen._compositor
        assert body.is_mounted and body not in compositor._visible_map
        published = compositor._full_map, compositor._visible_map
        with patch.object(compositor, "_arrange_root", side_effect=AssertionError("Capture manufactured a full scene")):
            try:
                compositor.render_subtree_strips(body)
            except errors.NoWidget:
                pass
            else:
                raise AssertionError("An unpublished body acquired native capture geometry")
        assert compositor._full_map is published[0]
        assert compositor._visible_map is published[1]
        # Position queries still acquire the ordinary complete layout.
        assert compositor.find_widget(body).region.height > 0
        assert body in compositor._full_map


async def test_body_capture_descendants_use_original_arrangement_and_screen_coordinates():
    app = App()
    async with app.run_test(size=(80, 25)) as pilot:
        screen = TargetedScreen()
        await app.push_screen(screen)
        await pilot.pause()
        body = screen.query_one("#group-85", VerticalGroup)
        row = screen.query_one("#row-85", Static)
        screen.targets = (body,)
        screen._refresh_layout(app.size)
        compositor = screen._compositor
        bounds = compositor.find_widget(body).region
        assert row not in compositor._visible_map
        published = compositor._full_map, compositor._visible_map
        arrange = compositor._arrange_root
        rendered_regions = []
        render_lines = row.render_lines

        def arrange_body(root, *args, **kwargs):
            assert root is body, "Body rendering rebuilt the whole screen"
            return arrange(root, *args, **kwargs)

        def render_row(crop):
            rendered_regions.append(row.region)
            return render_lines(crop)

        with patch.object(compositor, "_arrange_root", side_effect=arrange_body), patch.object(row, "render_lines", side_effect=render_row):
            size, strips = compositor.render_subtree_strips(body)
        assert size == bounds.size
        assert len(strips) == size.height
        assert all(strip.cell_length == size.width for strip in strips)
        assert "Row 85" in "\n".join(strip.text for strip in strips)
        assert "second line" in "\n".join(strip.text for strip in strips)
        assert rendered_regions and all(region.offset == bounds.offset for region in rendered_regions)
        assert compositor._full_map is published[0]
        assert compositor._visible_map is published[1]
        assert compositor._render_geometry is None

        # A failing renderer must release the same scoped resource and leave
        # ordinary screen queries with their original publication.
        with patch.object(row, "render_lines", side_effect=ValueError("render failed")):
            try:
                compositor.render_subtree_strips(body)
            except ValueError as error:
                assert str(error) == "render failed"
            else:
                raise AssertionError("Renderer failure was hidden")
        assert compositor._render_geometry is None
        assert compositor._full_map is published[0]
        assert compositor._visible_map is published[1]
