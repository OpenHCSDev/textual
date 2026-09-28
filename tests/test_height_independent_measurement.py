"""Reuse only declared height-independent boxes; all other contexts keep native results."""

from fractions import Fraction
from unittest.mock import patch

import pytest

from textual.app import App
from textual.containers import HorizontalGroup, VerticalGroup
from textual.css.scalar import Scalar, Unit
from textual.geometry import Size
from textual.layouts.vertical import VerticalLayout
from textual.layouts.stream import StreamLayout
from textual.widget import Widget
from textual.widgets import Static


class CachedColumn(VerticalGroup):
    CACHE_HEIGHT_INDEPENDENT_BOX = True


def box(widget, height, *, width=40, greedy=True):
    return widget._get_box_model(Size(width, height), widget.app.size,
                                 Fraction(width), Fraction(height), greedy=greedy)


async def test_native_nested_flow_reuses_only_unused_height_inputs():
    app = App()
    async with app.run_test() as pilot:
        column = CachedColumn(HorizontalGroup(Static("first"), Static("second")))
        await app.mount(column)
        await pilot.pause()
        assert not column._box_depends_on_available_height()
        column._box_model_cache.clear()
        with patch.object(column, "get_content_height", wraps=column.get_content_height) as measured:
            first = box(column, 0)
            assert box(column, 300) is first
            assert box(column, 30) is first
            assert measured.call_count == 1
            assert box(column, 300, width=20).width == 20
            assert measured.call_count == 2


@pytest.mark.parametrize("field,value", [
    ("height", "50%"), ("height", "1fr"),
    ("width", "50h"), ("min_width", "20h"), ("max_width", "30h"),
    ("min_height", "40%"), ("min_height", "1fr"), ("max_height", "50%"),
    ("max_height", "50vh"),
])
async def test_height_dependent_css_and_extrema_match_native_contexts(field, value):
    app = App()
    async with app.run_test() as pilot:
        column = CachedColumn(Static("wrapped text " * 25))
        await app.mount(column)
        setattr(column.styles, field, value)
        await pilot.pause()
        assert column._box_depends_on_available_height()
        column.CACHE_HEIGHT_INDEPENDENT_BOX = False
        column._box_model_cache.clear()
        expected = {height: box(column, height) for height in (0, 10, 30, 70)}
        column.CACHE_HEIGHT_INDEPENDENT_BOX = True
        column._box_model_cache.clear()
        for height, measured in expected.items():
            assert box(column, height) == measured


async def test_descendant_style_change_invalidates_proof_before_idle():
    app = App()
    async with app.run_test() as pilot:
        leaf = Static("one")
        column = CachedColumn(VerticalGroup(leaf))
        await app.mount(column)
        await pilot.pause()
        assert not column._box_depends_on_available_height()
        first = box(column, 0)
        assert box(column, 30) is first
        leaf.styles.height = "1fr"
        assert column._box_depends_on_available_height()
        assert box(column, 100).height != first.height
        leaf.styles.height = 2
        assert not column._box_depends_on_available_height()
        await pilot.pause()
        assert box(column, 30).height == 2


async def test_structural_admission_retires_normalized_boxes():
    app = App()
    async with app.run_test() as pilot:
        inner = VerticalGroup(Static("first"))
        column = CachedColumn(inner)
        await app.mount(column)
        await pilot.pause()
        before = box(column, 30)
        added = Static("second")
        added.styles.height = 4
        receipt = inner.mount(added)
        assert box(column, 200).height == before.height + 4
        await receipt


async def test_custom_measurement_and_layout_overrides_are_context_dependent():
    class CustomHeight(CachedColumn):
        def get_content_height(self, container, viewport, width):
            return container.height + 3

    class CustomLayout(VerticalLayout):
        def arrange(self, parent, children, size, greedy=True):
            return super().arrange(parent, children, size, greedy)

    class CustomHook(CachedColumn):
        def pre_layout(self, layout):
            super().pre_layout(layout)

    class CustomPlacement(CachedColumn):
        def process_layout(self, placements):
            return placements

    app = App()
    async with app.run_test() as pilot:
        custom = CustomHeight()
        layout = CachedColumn(Static("auto height"))
        layout.styles.set_rule("layout", CustomLayout())
        hook = CustomHook(Static("auto height"))
        placement = CustomPlacement(Static("auto height"))
        await app.mount(custom, layout, hook, placement)
        await pilot.pause()
        assert box(custom, 10).height == 13
        assert box(custom, 30).height == 33
        observed = {type(widget).__name__: widget._box_depends_on_available_height()
                    for widget in (custom, layout, hook, placement)}
        assert all(observed.values()), observed


@pytest.mark.parametrize("field,value", [("dock", "bottom"), ("split", "bottom"), ("overlay", "screen")])
async def test_flow_rejects_context_sensitive_child_placement(field, value):
    app = App()
    async with app.run_test() as pilot:
        child = VerticalGroup(Static("text"))
        column = CachedColumn(child)
        await app.mount(column)
        await pilot.pause()
        assert not column._box_depends_on_available_height()
        setattr(child.styles, field, value)
        assert column._box_depends_on_available_height()


async def test_width_and_viewport_scalars_preserve_native_results():
    app = App()
    async with app.run_test() as pilot:
        column = CachedColumn(Static("text"))
        await app.mount(column)
        await pilot.pause()
        for unit in (Unit.CELLS, Unit.WIDTH, Unit.VIEW_HEIGHT, Unit.VIEW_WIDTH):
            column.styles.height = Scalar(10, unit, Unit.HEIGHT)
            assert not column._box_depends_on_available_height()
            column.CACHE_HEIGHT_INDEPENDENT_BOX = False
            column._box_model_cache.clear()
            expected = box(column, 70)
            column.CACHE_HEIGHT_INDEPENDENT_BOX = True
            assert box(column, 0) == expected
            assert box(column, 70) == expected
        assert Widget.CACHE_HEIGHT_INDEPENDENT_BOX is False


async def test_unknown_width_and_stream_overrides_do_not_inherit_a_proof():
    class HeightSizedWidth(Static):
        CACHE_HEIGHT_INDEPENDENT_BOX = True

        def get_content_width(self, container, viewport):
            return container.height

    class UnknownStream(StreamLayout):
        def arrange(self, parent, children, size, greedy=True):
            return super().arrange(parent, children, size, greedy)

    app = App()
    async with app.run_test() as pilot:
        width = HeightSizedWidth("text")
        width.styles.width = "auto"
        width.styles.height = 1
        stream = CachedColumn(Static("text"))
        stream.styles.set_rule("layout", UnknownStream())
        await app.mount(width, stream)
        await pilot.pause()
        assert width._box_depends_on_available_height()
        assert stream._box_depends_on_available_height()
        assert box(width, 10).width == 10
        assert box(width, 30).width == 30


@pytest.mark.parametrize("layout_name", ["vertical", "horizontal", "stream"])
async def test_width_padding_margin_offset_and_viewport_parity(layout_name):
    app = App()
    async with app.run_test() as pilot:
        children = [Static("line one\nline two"), Static("wrapped " * 15)]
        column = CachedColumn(*children)
        column.styles.layout = layout_name
        column.styles.padding = (1, 2)
        children[0].styles.margin = (1, 2, 3, 4)
        children[1].styles.offset = (1, 2)
        await app.mount(column)
        await pilot.pause()
        inputs = [(width, height, greedy) for width in (20, 40)
                  for height in (0, 10, 100) for greedy in (False, True)]
        column.CACHE_HEIGHT_INDEPENDENT_BOX = False
        column._box_model_cache.clear()
        expected = [box(column, height, width=width, greedy=greedy) for width, height, greedy in inputs]
        column.CACHE_HEIGHT_INDEPENDENT_BOX = True
        column._box_model_cache.clear()
        assert [box(column, height, width=width, greedy=greedy) for width, height, greedy in inputs] == expected


async def test_unset_height_and_custom_extrema_keep_the_full_context():
    from textual._extrema import Extrema

    class CustomExtrema(CachedColumn):
        def _resolve_extrema(self, container, viewport, width_fraction, height_fraction):
            return Extrema(min_height=Fraction(container.height))

    app = App()
    async with app.run_test() as pilot:
        fill = CachedColumn(Static("fill"))
        custom = CustomExtrema(Static("extent"))
        await app.mount(fill, custom)
        await pilot.pause()
        fill.styles.base.clear_rule("height")
        fill.styles.inline.clear_rule("height")
        assert fill.styles.height is None
        assert fill._box_depends_on_available_height()
        assert custom._box_depends_on_available_height()
        for height in (10, 30):
            assert box(fill, height).height == height
            assert box(custom, height).height == height


async def test_custom_scalar_resolver_is_not_classified_by_its_unit_alone():
    class ContextScalar(Scalar):
        def resolve(self, size, viewport, fraction_unit=Fraction(1)):
            return Fraction(size.height)

    app = App()
    async with app.run_test() as pilot:
        column = CachedColumn(Static("text"))
        await app.mount(column)
        await pilot.pause()
        column.styles.height = ContextScalar(1, Unit.CELLS, Unit.HEIGHT)
        assert column._box_depends_on_available_height()
        assert box(column, 10).height == 10
        assert box(column, 30).height == 30


async def test_raw_width_percentage_height_keeps_native_parent_stretch():
    # Native relative-child detection treats every percentage height as
    # relative, even when a raw scalar declares WIDTH as its percentage axis.
    # Preserve that parent stretch behavior rather than only the scalar value.
    app = App()
    async with app.run_test() as pilot:
        child = Static("text")
        column = CachedColumn(child)
        await app.mount(column)
        await pilot.pause()
        child.styles.set_rule("height", Scalar(50, Unit.PERCENT, Unit.WIDTH))
        child.refresh(layout=True)
        await pilot.pause()
        assert column._has_relative_children_height
        assert column._box_depends_on_available_height()
        assert box(column, 0).height == 20
        assert box(column, 100).height == 100
