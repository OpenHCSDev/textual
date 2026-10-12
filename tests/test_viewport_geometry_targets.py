import pytest
from unittest.mock import patch

from textual import errors
from textual.app import App
from textual.containers import VerticalGroup, VerticalScroll
from textual.screen import Screen
from textual.widgets import Static


def test_borrowed_geometry_routes_preserve_membership_ancestry_and_assignment_order():
    from types import MappingProxyType

    from textual._compositor import (
        IntrinsicSubtreeGeometry, PlacedSubtreeGeometry, RootSceneClip,
        SubtreeGeometryKey, SubtreeGeometryPlacement, SubtreeMapGeometry, run_steps,
    )
    from textual.geometry import Offset, Region, Spacing
    from textual.map_geometry import MapGeometry

    root, first, second, shared, logical, invisible, unrelated = (
        Static(name) for name in ("root", "first", "second", "shared", "logical", "invisible", "unrelated")
    )
    bounds = Region(0, 0, 20, 10)
    clip = RootSceneClip(bounds)
    key = SubtreeGeometryKey(0, 0, bounds, bounds, (), 0, bounds, True,
                            Spacing(), bounds.size, False, Offset(), ())

    def placed(owner, y, ancestors):
        region = Region(0, y, 5, 1)
        return MapGeometry(region, (), bounds, region.size, region.size, region,
                           Spacing(), ancestors, owner.gutter)

    def source(owner, y):
        return IntrinsicSubtreeGeometry(
            key, MappingProxyType({
                owner: (0, SubtreeMapGeometry(placed(owner, y, (root,)), (), None)),
                shared: (1, SubtreeMapGeometry(placed(shared, y + 1, (owner, root)), (), owner)),
            }), frozenset((owner, shared, logical)), frozenset((invisible,)),
        )

    first_source, second_source = source(first, 0), source(second, 5)
    resource = PlacedSubtreeGeometry(
        key, MappingProxyType({
            first: (0, SubtreeGeometryPlacement(first_source, key, clip, root)),
            second: (1, SubtreeGeometryPlacement(second_source, key, clip, root)),
            root: (2, placed(root, 9, ())),
        }), frozenset((root,)), frozenset(),
    )
    assert resource.contains(shared)
    assert logical in set(resource.members()) and not resource.contains(logical)
    assert invisible in set(resource.members(invisible=True)) and not resource.contains(invisible)
    assert not resource.contains(unrelated)
    assert resource._geometry_routes[shared] == (first, second)
    assert resource.captured_parent(shared) is first
    assert resource.captured_parent(first) is root
    published, clips = {}, {}
    run_steps(resource.project_into(published, key, clip, clips, root, visible_only=True,
                                    retained={shared, unrelated}, bounds=Region(30, 30, 1, 1),
                                    ancestry_root=root, ancestors=(), deadline=None))
    assert published[shared] == placed(shared, 6, (second, root))
    assert unrelated not in published


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


async def test_held_screen_relative_source_keeps_placement_and_retires_children():
    from textual._compositor import PlacedSubtreeGeometry

    class HeldBody(VerticalGroup):
        CACHE_SUBTREE_GEOMETRY = True

        def arrange(self, size, optimal=False):
            assert not self.lock.is_locked, "Read changing overlay layout"
            return super().arrange(size, optimal=optimal)

    overlay = Static("SCREEN_OVERLAY", id="overlay")
    retired = Static("RETIRE_THIS", id="retired")
    body = HeldBody(overlay, retired, *(Static(f"row {i}") for i in range(30)))

    class HeldScreen(TargetedScreen):
        CSS = "#overlay { overlay: screen; width: 12; height: 1; offset: 2 3; }"

        def compose(self):
            with VerticalScroll(id="history"):
                yield body

        def _layout_mutation_roots(self):
            return (body,) if body.lock.is_locked else ()

    app = App()
    async with app.run_test(size=(40, 10)) as pilot:
        screen = HeldScreen()
        screen.targets = (body,)
        await app.push_screen(screen)
        await pilot.pause()
        compositor = screen._compositor
        resource = compositor._subtree_geometry[body]
        assert isinstance(resource, PlacedSubtreeGeometry)
        original = dict(compositor._published_map)
        async with body.lock:
            await body.mount(Static("INCOMPLETE"))
            screen.query_one("#history").scroll_to(y=10, animate=False, immediate=True)
            await pilot.pause()
            for node, geometry in original.items():
                if resource.contains(node):
                    assert compositor._published_map[node] == geometry
            await retired.remove()
            await pilot.pause()
            assert body not in compositor._subtree_geometry
            assert retired not in compositor._published_map
            assert retired not in compositor.widgets
            assert compositor._published_map[overlay] == original[overlay]
        body.refresh(layout=True)
        await pilot.pause()
        assert not app._exception


@pytest.mark.parametrize("scoped", [False, True])
async def test_cached_overlay_and_fixed_children_match_the_original_scene(scoped):
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
            if scoped:
                # As when the scroll reaches the screen before the frame: the
                # scoped reflow of the scrolled container. It keeps the
                # container behind its scrollbars, as the full arrangement does.
                screen._scrolled_widgets.add(history)
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
            size, strips, _ = compositor.render_subtree_strips(body, placement)
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
