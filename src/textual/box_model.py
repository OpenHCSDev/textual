from __future__ import annotations

from fractions import Fraction
from typing import TYPE_CHECKING, NamedTuple, get_args

from textual._extrema import Extrema, NO_EXTREMA
from textual.css.scalar import Scalar, ScalarOffset, Unit
from textual.css.types import AlignHorizontal, AlignVertical
from textual.geometry import NULL_OFFSET, NULL_SPACING, Offset, Size, Spacing

if TYPE_CHECKING:
    from textual.color import Color
    from textual.css._style_properties import Edges
    from textual.layout import Layout
    from textual.widget import Widget


DEFAULT_LAYER = "default"
"""The layer a widget paints in when it declares none."""


class BoxModel(NamedTuple):
    """The result of `get_box_model`."""

    width: Fraction | int
    height: Fraction | int
    margin: Spacing


class BoxGeometry:
    """Geometry inputs and their shared measurement/placement algorithms.

    CSS styles supply these inputs through their descriptors. A widget may
    instead inherit this capability and declare its inputs directly. Neither
    path translates into, or keeps a copy of, the other path's declarations.
    """

    width: Scalar | None
    height: Scalar | None
    min_width: Scalar | None
    min_height: Scalar | None
    max_width: Scalar | None
    max_height: Scalar | None
    padding: Spacing
    margin: Spacing
    border: Edges
    box_sizing: str
    width_policy: str
    dock: str
    split: str
    overflow_x: str
    overflow_y: str
    scrollbar_policy: str
    vertical_scrollbar_size: int
    horizontal_scrollbar_size: int
    scrollbar_visibility: str
    align_horizontal: str
    align_vertical: str
    grid_rows: tuple[Scalar, ...]
    grid_columns: tuple[Scalar, ...]
    grid_size_columns: int
    grid_size_rows: int
    grid_gutter_horizontal: int
    grid_gutter_vertical: int
    row_span: int
    column_span: int
    keyline: tuple[str, Color]
    position: str
    overlay: str
    constrain_x: str
    constrain_y: str

    @property
    def box_gutter(self) -> Spacing:
        return self.padding + self.border.spacing

    @property
    def child_layout(self) -> Layout | None:
        """An explicitly supplied child layout, if any."""
        raise NotImplementedError

    @property
    def placement_offset(self) -> ScalarOffset | None:
        raise NotImplementedError

    def set_placement_offset(self, offset: ScalarOffset) -> None:
        raise NotImplementedError

    @property
    def layer_name(self) -> str:
        raise NotImplementedError

    @property
    def layer_order(self) -> tuple[str, ...] | None:
        raise NotImplementedError

    @property
    def flow_geometry(self) -> BoxGeometry:
        """Inputs accepted by the stream layout's existing flow contract."""
        return self

    @property
    def auto_dimensions(self) -> bool:
        return self.is_auto_width or self.is_auto_height

    @property
    def is_relative_width(self) -> bool:
        width = self.width
        return width is not None and width.unit in (Unit.FRACTION, Unit.PERCENT)

    @property
    def is_relative_height(self) -> bool:
        height = self.height
        return height is not None and height.unit in (Unit.FRACTION, Unit.PERCENT)

    @property
    def is_auto_width(self) -> bool:
        width = self.width
        return width is not None and width.is_auto

    @property
    def is_auto_height(self) -> bool:
        height = self.height
        return height is not None and height.is_auto

    @property
    def is_dynamic_height(self) -> bool:
        height = self.height
        return height is not None and height.unit in (Unit.AUTO, Unit.FRACTION, Unit.PERCENT)

    @property
    def is_docked(self) -> bool:
        return self.dock != "none"

    @property
    def is_split(self) -> bool:
        return self.split != "none"

    @property
    def sizing_gutter(self) -> Spacing:
        """The gutter that a declared size includes."""
        return self.box_gutter if self.box_sizing == "border-box" else NULL_SPACING

    @property
    def stable_gutter(self) -> bool:
        """Whether the scrollbar gutter is reserved while the scrollbar is hidden."""
        return self.scrollbar_policy == "stable"

    def _reserves_gutter(self, overflow: str) -> bool:
        return overflow == "auto" and self.stable_gutter

    def _align_size(self, child: tuple[int, int], parent: tuple[int, int]) -> Offset:
        # Each alignment Literal declares start, middle, end: its index halves the free space.
        x = get_args(AlignHorizontal).index(self.align_horizontal)
        y = get_args(AlignVertical).index(self.align_vertical)
        return Offset((parent[0] - child[0]) * x // 2, (parent[1] - child[1]) * y // 2)

    def resolve_offset(self, size: Size, viewport: Size) -> Offset:
        offset = self.placement_offset
        return NULL_OFFSET if offset is None else offset.resolve(size, viewport)

    def resolve_extrema(
        self, container: Size, viewport: Size,
        width_fraction: Fraction, height_fraction: Fraction,
    ) -> Extrema:
        """Resolve constraints independently of the scene's measurement cache."""
        min_width_rule, max_width_rule = self.min_width, self.max_width
        min_height_rule, max_height_rule = self.min_height, self.max_height
        if all(rule is None for rule in (min_width_rule, max_width_rule,
                                         min_height_rule, max_height_rule)):
            return NO_EXTREMA
        container -= self.margin.totals
        gutter_width, gutter_height = self.sizing_gutter.totals
        return Extrema(
            None if min_width_rule is None else min_width_rule.resolve(
                container, viewport, width_fraction) - gutter_width,
            None if max_width_rule is None else max_width_rule.resolve(
                container, viewport, width_fraction) - gutter_width,
            None if min_height_rule is None else min_height_rule.resolve(
                container, viewport, height_fraction) - gutter_height,
            None if max_height_rule is None else max_height_rule.resolve(
                container, viewport, height_fraction) - gutter_height,
        )

    def resolve_box(
        self, node: Widget, container: Size, viewport: Size,
        width_fraction: Fraction, height_fraction: Fraction,
        constrain_width: bool = False, greedy: bool = True,
    ) -> tuple[BoxModel, Extrema]:
        """Resolve these dimensions using the widget's intrinsic measurements."""
        gutter, margin, sizing_gutter = self.box_gutter, self.margin, self.sizing_gutter
        width, height = self.width, self.height
        if not greedy and width is not None and width.is_fraction:
            width = Scalar(1.0, Unit.AUTO, Unit.AUTO)
        is_auto_width = width is not None and width.is_auto
        is_auto_height = height is not None and height.is_auto
        content_container = container - gutter.totals
        extrema = node._extrema = self.resolve_extrema(
            container, viewport, width_fraction, height_fraction
        )
        min_width, max_width, min_height, max_height = extrema

        if width is None:
            content_width = content_container.width - margin.width
        elif is_auto_width:
            content_width = node.get_content_width(content_container - margin.totals, viewport)
            if self._reserves_gutter(self.overflow_x) or node.show_vertical_scrollbar:
                content_width += self.vertical_scrollbar_size
            if content_width < content_container.width and node._has_relative_children_width:
                content_width = content_container.width
        else:
            content_width = width.resolve(container - margin.totals, viewport, width_fraction)
            content_width -= sizing_gutter.width
        if min_width is not None:
            content_width = max(content_width, min_width, 0)
        if max_width is not None and not (
            container.width == 0 and self.max_width.unit.resolves_against_container
            and node._parent is not None and node._parent.geometry.is_auto_width
        ):
            content_width = min(content_width, max_width)
        content_width = max(0, content_width)
        if constrain_width:
            content_width = min(container.width - gutter.width, content_width)

        if height is None:
            content_height = content_container.height - margin.height
        elif is_auto_height:
            content_height = node.get_content_height(
                content_container - margin.totals, viewport, int(content_width)
            )
            if self._reserves_gutter(self.overflow_y) or node.show_horizontal_scrollbar:
                content_height += self.horizontal_scrollbar_size
            if content_height < content_container.height and node._has_relative_children_height:
                content_height = content_container.height
        else:
            content_height = height.resolve(container - margin.totals, viewport, height_fraction)
            content_height -= sizing_gutter.height
        if min_height is not None:
            content_height = max(content_height, min_height, 0)
        if max_height is not None and not (
            container.height == 0 and self.max_height.unit.resolves_against_container
            and node._parent is not None and node._parent.geometry.is_auto_height
        ):
            content_height = min(content_height, max_height)
        content_height = max(0, content_height)
        return BoxModel(content_width + gutter.width, content_height + gutter.height, margin), extrema
