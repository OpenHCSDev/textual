"""Whole-arrangement reuse must preserve the native placement oracle."""

from fractions import Fraction

import pytest

from textual.app import App
from textual.containers import VerticalGroup
from textual.css.scalar import Scalar, Unit
from textual.geometry import Size
from textual.layouts.vertical import VerticalLayout
from textual.widgets import Static


class CachedArrangement(VerticalGroup):
    CACHE_HEIGHT_INDEPENDENT_ARRANGEMENT = True
    CACHE_HEIGHT_INDEPENDENT_BOX = True


async def test_unrelated_style_and_topology_changes_preserve_subtree_reuse():
    app = App()
    async with app.run_test() as pilot:
        parent = CachedArrangement(Static("one"))
        sibling = VerticalGroup(Static("unrelated"))
        await app.mount(parent, sibling)
        await pilot.pause()
        first = parent.arrange(Size(40, 0))
        box = parent._get_box_model(Size(40, 0), app.size, Fraction(40), Fraction(0))
        sibling.styles.color = "red"
        receipt = sibling.mount(Static("another unrelated child"))
        assert parent.arrange(Size(40, 100)) is first
        assert parent._get_box_model(Size(40, 100), app.size, Fraction(40), Fraction(100)) is box
        await receipt


async def test_raw_descendant_style_write_invalidates_without_refresh():
    app = App()
    async with app.run_test() as pilot:
        child = Static("one")
        parent = CachedArrangement(child)
        await app.mount(parent)
        await pilot.pause()
        first = parent.arrange(Size(40, 0))
        child.styles.base.set_rule("height", Scalar.parse("1fr"))
        current = parent.arrange(Size(40, 100))
        assert current is not first
        assert current.placements[0][1].region.height == 100


async def test_box_reuse_observes_immediate_parent_width_exception():
    class CachedLeaf(Static):
        CACHE_HEIGHT_INDEPENDENT_BOX = True

    app = App()
    async with app.run_test() as pilot:
        leaf = CachedLeaf("intrinsic width")
        leaf.styles.width = "auto"
        leaf.styles.max_width = "50%"
        leaf.styles.height = 1
        parent = VerticalGroup(leaf)
        parent.styles.width = "auto"
        await app.mount(parent)
        await pilot.pause()
        before = leaf._get_box_model(Size(0, 10), app.size, Fraction(0), Fraction(10))
        assert before.width > 0
        parent.styles.width = 40
        after = leaf._get_box_model(Size(0, 100), app.size, Fraction(0), Fraction(100))
        assert after.width == 0
        assert after is not before


@pytest.mark.parametrize("field,value", [
    ("min_width", "20h"), ("max_width", "50h"),
    ("min_height", "10%"), ("max_height", "50%"),
])
async def test_grid_auto_track_extrema_keep_outer_height_dependency(field, value):
    app = App()
    async with app.run_test() as pilot:
        child = Static("wrapped text " * 10)
        parent = CachedArrangement(child)
        parent.styles.layout = "grid"
        parent.styles.grid_columns = "auto"
        setattr(child.styles, field, value)
        await app.mount(parent)
        await pilot.pause()
        parent._clear_arrangement_cache()
        first = parent.arrange(Size(40, 10))
        assert parent.arrange(Size(40, 100)) is not first


async def test_local_style_projection_covers_all_raw_mutation_boundaries():
    app = App()
    async with app.run_test() as pilot:
        child = Static("one")
        parent = CachedArrangement(child)
        sibling = CachedArrangement(Static("unrelated"))
        await app.mount(parent, sibling)
        await pilot.pause()
        style = child.styles.base
        for mutate in (
            lambda: style.set_rule("height", Scalar.parse("1fr")),
            lambda: style.clear_rule("height"),
            lambda: style.merge_rules({"height": Scalar.parse("auto")}),
            style.reset,
        ):
            before = parent.arrange(Size(40, 100))
            unrelated = sibling.arrange(Size(40, 100))
            mutate()
            assert parent.arrange(Size(40, 100)) is not before
            assert sibling.arrange(Size(40, 100)) is unrelated


@pytest.mark.parametrize("layout", ["vertical", "horizontal", "stream", "grid"])
async def test_reuse_skips_a_complete_intrinsic_arrangement(layout):
    app = App()
    async with app.run_test() as pilot:
        parent = CachedArrangement(Static("one"), Static("wrapped " * 15))
        parent.styles.layout = layout
        await app.mount(parent)
        await pilot.pause()
        parent._clear_arrangement_cache()
        first = parent.arrange(Size(40, 0))
        assert parent.arrange(Size(40, 200)) is first
        assert parent.arrange(Size(40, 20)) is first
        assert parent.arrange(Size(20, 20)) is not first
        assert parent.arrange(Size(40, 20), optimal=True) is not first


@pytest.mark.parametrize("layout", ["vertical", "horizontal", "stream", "grid"])
async def test_reuse_matches_native_placements_and_invalidates_before_idle(layout):
    app = App()
    async with app.run_test() as pilot:
        inner = VerticalGroup(Static("nested " * 10))
        parent = CachedArrangement(inner, Static("second"))
        parent.styles.layout = layout
        parent.styles.padding = (1, 2)
        inner.styles.margin = (1, 2, 3, 4)
        inner.styles.offset = (1, 2)
        await app.mount(parent)
        await pilot.pause()

        def check():
            sizes = [Size(width, height) for width in (20, 40) for height in (0, 10, 100)]
            parent.CACHE_HEIGHT_INDEPENDENT_ARRANGEMENT = False
            parent._clear_arrangement_cache()
            expected = [parent.arrange(size).placements[:] for size in sizes]
            parent.CACHE_HEIGHT_INDEPENDENT_ARRANGEMENT = True
            parent._clear_arrangement_cache()
            assert [parent.arrange(size).placements for size in sizes] == expected

        check()
        before = parent.arrange(Size(40, 100))
        inner.children[0].styles.height = 7
        assert parent.arrange(Size(40, 100)) is not before
        check()
        before = parent.arrange(Size(40, 100))
        receipt = inner.mount(Static("admitted before idle"))
        assert parent.arrange(Size(40, 100)) is not before
        await receipt
        check()
        parent.children[1].display = False
        check()
        await pilot.resize_terminal(100, 30)
        check()


@pytest.mark.parametrize("field,value", [
    ("height", "50%"), ("height", "1fr"), ("width", "30h"),
    ("min_height", "10%"), ("max_height", "50%"),
    ("dock", "bottom"), ("split", "bottom"), ("overlay", "screen"),
])
async def test_context_sensitive_flow_keeps_native_height_inputs(field, value):
    app = App()
    async with app.run_test() as pilot:
        child = Static("text")
        parent = CachedArrangement(child)
        await app.mount(parent)
        setattr(child.styles, field, value)
        await pilot.pause()
        parent._clear_arrangement_cache()
        first = parent.arrange(Size(40, 10))
        assert parent.arrange(Size(40, 100)) is not first


@pytest.mark.parametrize("layout", ["stream", "grid"])
async def test_direct_content_measurement_cannot_use_a_fixed_box_proof(layout):
    class ContextContent(Static):
        def get_content_height(self, container, viewport, width):
            return container.height + 1

    app = App()
    async with app.run_test() as pilot:
        child = ContextContent("text")
        child.styles.height = 2  # Box is constant; direct content measurement is not.
        parent = CachedArrangement(child)
        parent.styles.layout = layout
        await app.mount(parent)
        await pilot.pause()
        parent._clear_arrangement_cache()
        first = parent.arrange(Size(40, 10))
        assert parent.arrange(Size(40, 100)) is not first


@pytest.mark.parametrize("field,value", [
    ("height", "1fr"), ("grid_rows", "1fr"), ("grid_rows", "50%"),
    ("grid_columns", "30h"), ("align_vertical", "middle"),
])
async def test_grid_context_rules_retain_native_arrangements(field, value):
    app = App()
    async with app.run_test() as pilot:
        parent = CachedArrangement(Static("text"))
        parent.styles.layout = "grid"
        setattr(parent.styles, field, value)
        await app.mount(parent)
        await pilot.pause()
        parent._clear_arrangement_cache()
        first = parent.arrange(Size(40, 10))
        assert parent.arrange(Size(40, 100)) is not first


async def test_unknown_layout_hooks_and_scalars_remain_context_sensitive():
    class UnknownLayout(VerticalLayout):
        def arrange(self, parent, children, size, greedy=True):
            return super().arrange(parent, children, size, greedy)

    class UnknownHook(CachedArrangement):
        def pre_layout(self, layout):
            super().pre_layout(layout)

    class UnknownScalar(Scalar):
        def resolve(self, size, viewport, fraction_unit=Fraction(1)):
            return Fraction(size.height)

    app = App()
    async with app.run_test() as pilot:
        layout = CachedArrangement(Static("text"))
        layout.styles.set_rule("layout", UnknownLayout())
        hook = UnknownHook(Static("text"))
        scalar = CachedArrangement(Static("text"))
        scalar.styles.layout = "grid"
        scalar.styles.set_rule("grid_rows", (UnknownScalar(1, Unit.CELLS, Unit.HEIGHT),))
        await app.mount(layout, hook, scalar)
        await pilot.pause()
        for parent in (layout, hook, scalar):
            parent._clear_arrangement_cache()
            first = parent.arrange(Size(40, 10))
            assert parent.arrange(Size(40, 100)) is not first
