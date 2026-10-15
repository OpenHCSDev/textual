from __future__ import annotations

from fractions import Fraction
from typing import TYPE_CHECKING, NamedTuple

from textual._extrema import Extrema, NO_EXTREMA
from textual.css.scalar import Scalar, ScalarOffset, Unit
from textual.geometry import NULL_OFFSET, Offset, Size, Spacing

if TYPE_CHECKING:
    from textual.color import Color
    from textual.css._style_properties import Edges
    from textual.layout import Layout
    from textual.widget import Widget


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
        """Inputs admitted by the stream layout's existing flow contract."""
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

    def _align_width(self, width: int, parent_width: int) -> int:
        align = self.align_horizontal
        return ((parent_width - width) // 2 if align == "center" else
                parent_width - width if align == "right" else 0)

    def _align_height(self, height: int, parent_height: int) -> int:
        align = self.align_vertical
        return ((parent_height - height) // 2 if align == "middle" else
                parent_height - height if align == "bottom" else 0)

    def _align_size(self, child: tuple[int, int], parent: tuple[int, int]) -> Offset:
        return Offset(self._align_width(child[0], parent[0]),
                      self._align_height(child[1], parent[1]))

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
        if (min_width_rule is None and max_width_rule is None
                and min_height_rule is None and max_height_rule is None):
            return NO_EXTREMA
        container -= self.margin.totals
        gutter_width, gutter_height = (
            self.box_gutter.totals if self.box_sizing == "border-box" else (0, 0)
        )
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
        is_border_box = self.box_sizing == "border-box"
        gutter, margin = self.box_gutter, self.margin
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
            if (self.overflow_x == "auto" and self.scrollbar_policy == "stable"
                    or node.show_vertical_scrollbar):
                content_width += self.vertical_scrollbar_size
            if content_width < content_container.width and node._has_relative_children_width:
                content_width = content_container.width
        else:
            content_width = width.resolve(container - margin.totals, viewport, width_fraction)
            if is_border_box:
                content_width -= gutter.width
        if min_width is not None:
            content_width = max(content_width, min_width, 0)
        if max_width is not None and not (
            container.width == 0 and not self.max_width.is_cells
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
            if (self.overflow_y == "auto" and self.scrollbar_policy == "stable"
                    or node.show_horizontal_scrollbar):
                content_height += self.horizontal_scrollbar_size
            if content_height < content_container.height and node._has_relative_children_height:
                content_height = content_container.height
        else:
            content_height = height.resolve(container - margin.totals, viewport, height_fraction)
            if is_border_box:
                content_height -= gutter.height
        if min_height is not None:
            content_height = max(content_height, min_height, 0)
        if max_height is not None and not (
            container.height == 0 and not self.max_height.is_cells
            and node._parent is not None and node._parent.geometry.is_auto_height
        ):
            content_height = min(content_height, max_height)
        content_height = max(0, content_height)
        return BoxModel(content_width + gutter.width, content_height + gutter.height, margin), extrema
