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


async def test_cached_overlay_and_fixed_children_match_the_original_scene():
    from textual._compositor import Compositor, PlacedSubtreeGeometry

    class CachedBody(VerticalGroup):
        CACHE_SUBTREE_GEOMETRY = True

    body = CachedBody(
        Static("Fixed heading", id="fixed-heading"),
        Static("Screen overlay", id="screen-overlay"),
        *(Static(f"Source row {index}", id=f"source-row-{index}") for index in range(80)),
        id="cached-body",
    )

    class OverlayScreen(TargetedScreen):
        CSS = """
        #fixed-heading { dock: top; height: 1; }
        #screen-overlay { overlay: screen; width: 15; height: 1; offset: 5 3; }
        """

        def compose(self):
            with VerticalScroll(id="history"):
                yield body

    app = App()
    async with app.run_test(size=(40, 10)) as pilot:
        screen = OverlayScreen()
        screen.targets = (body,)
        await app.push_screen(screen)
        await pilot.pause()
        history = screen.query_one("#history", VerticalScroll)
        compositor = screen._compositor
        for position in (0, 30, 0):
            history.scroll_to(y=position, immediate=True, animate=False)
            screen._refresh_layout(app.size, scroll=True)
            # The overlay's clip reaches the outer screen, so this resource
            # keeps placed geometry rather than manufacturing an intrinsic clip.
            assert isinstance(compositor._subtree_geometry[body], PlacedSubtreeGeometry)
            expected, _ = Compositor(max_subtree_geometry_entries=0)._arrange_root(
                screen, app.size, visible_only=False,
            )
            paint = compositor._paint_regions(compositor._ordered_geometry(expected), app.size.region)
            admitted = {node: expected[node] for node in paint}
            admitted[body] = expected[body]  # The original explicit geometry target.
            for node, entry in admitted.items():
                assert node in compositor._visible_map, (position, node.id, entry)
                assert compositor._visible_map[node] == entry
            actual_layers = compositor._ordered_geometry(compositor._visible_map)
            expected_layers = compositor._ordered_geometry(expected)
            assert [(node, entry) for node, entry in actual_layers if node in admitted] == [
                (node, entry) for node, entry in expected_layers if node in admitted
            ]


async def test_complete_cached_body_keeps_capture_and_explicit_reader_geometry():
    class CachedBody(VerticalGroup):
        CACHE_SUBTREE_GEOMETRY = True

    rows = [Static(f"Original row {index}", id=f"cached-row-{index}")
            for index in range(240)]
    body = CachedBody(*rows, id="cached-body")

    class CachedScreen(TargetedScreen):
        def compose(self):
            with VerticalScroll(id="history"):
                yield body

    app = App()
    async with app.run_test(size=(40, 10)) as pilot:
        screen = CachedScreen()
        screen.targets = (body, rows[235])
        await app.push_screen(screen)
        await pilot.pause()
        history = screen.query_one("#history", VerticalScroll)
        compositor = screen._compositor
        resource = compositor._subtree_geometry[body]
        assert all(row in resource.geometry for row in rows)

        for position in (0, 200, 0):
            history.scroll_to(y=position, immediate=True, animate=False)
            screen._refresh_layout(app.size, scroll=True)
            viewport = compositor._visible_map
            assert body in viewport and rows[235] in viewport
            omitted = rows[200] if position == 0 else rows[0]
            assert omitted not in viewport
            assert all(row in resource.geometry for row in rows)
            assert all(row in compositor.widgets for row in rows)
            _, placement = next(compositor.published_geometry((body,)))
            source_bounds = app.size.region - (placement.region.offset - resource.key.region.offset)
            candidates = resource._spatial_map.get_values_in_region(source_bounds)
            # The immutable source stays complete; spatial admission and the
            # explicit offscreen reader path remain different original facts.
            assert omitted not in {node for _, node in candidates}
            assert rows[235] not in {node for _, node in candidates}
            assert len(candidates) < len(resource.geometry)
            # Capture remains complete without replacing the published viewport.
            size, strips = compositor.render_subtree_strips(body, placement)
            assert size.height == 240
            assert all(f"Original row {index}" in strip.text
                       for index, strip in enumerate(strips))
            assert compositor._visible_map is viewport

        # A position query retains its path without requiring every offscreen row.
        assert compositor.find_widget(rows[20]).region.height == 1
        assert rows[20] in compositor._visible_map
        assert rows[235] in compositor._visible_map
        assert compositor._full_map_invalidated
        assert all(row in compositor.full_map for row in rows)
        rows[5].display = False
        await pilot.pause()
        screen._refresh_layout(app.size, scroll=True)
        assert rows[5] not in compositor._subtree_geometry[body].geometry
        assert rows[235] in compositor._visible_map


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
        assert not tuple(screen._compositor.published_geometry((target, foreign)))


async def test_capture_requires_publication_while_position_queries_acquire_reader_paths():
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
            assert not tuple(compositor.published_geometry((body,)))
        assert compositor._full_map is published[0]
        assert compositor._visible_map is published[1]
        # Position queries acquire this original path in the current scene.
        assert compositor.find_widget(body).region.height > 0
        assert body in compositor._visible_map
        assert screen.query_one("#group-50") not in compositor._visible_map
        assert compositor._full_map is published[0]
        assert compositor._full_map_invalidated


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
        published_body, placement = next(compositor.published_geometry((body,)))
        assert published_body is body
        bounds = placement.region
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
            size, strips = compositor.render_subtree_strips(body, placement)
        assert size == bounds.size
        assert len(strips) == size.height
        assert all(strip.cell_length == size.width for strip in strips)
        assert "Row 85" in "\n".join(strip.text for strip in strips)
        assert "second line" in "\n".join(strip.text for strip in strips)
        assert rendered_regions and all(region.offset == bounds.offset for region in rendered_regions)
        assert compositor._full_map is published[0]
        assert compositor._visible_map is published[1]
        assert compositor._render_geometry is None

        # A descendant omitted by its real display rule must remain absent
        # inside capture, rather than acquiring geometry from the outer scene.
        hidden = body.children[1]
        hidden.display = False
        await pilot.pause()
        screen._refresh_layout(app.size)
        _, placement = next(compositor.published_geometry((body,)))
        published = compositor._full_map, compositor._visible_map
        scoped_misses = []

        def render_with_hidden_query(crop):
            try:
                compositor.find_widget(hidden)
            except errors.NoWidget:
                scoped_misses.append(hidden)
            else:
                raise AssertionError("Hidden capture descendant escaped its original arrangement")
            return render_lines(crop)

        with patch.object(compositor, "_arrange_root", side_effect=arrange_body), patch.object(row, "render_lines", side_effect=render_with_hidden_query):
            compositor.render_subtree_strips(body, placement)
        assert scoped_misses
        assert compositor._render_geometry is None
        assert compositor._full_map is published[0]
        assert compositor._visible_map is published[1]

        # A failing renderer must release the same scoped resource and leave
        # ordinary screen queries with their original publication.
        with patch.object(row, "render_lines", side_effect=ValueError("render failed")):
            try:
                compositor.render_subtree_strips(body, placement)
            except ValueError as error:
                assert str(error) == "render failed"
            else:
                raise AssertionError("Renderer failure was hidden")
        assert compositor._render_geometry is None
        assert compositor._full_map is published[0]
        assert compositor._visible_map is published[1]
