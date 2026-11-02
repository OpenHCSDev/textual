"""Class-owned native geometry and frame paint for composed widget views."""

from __future__ import annotations

from . import events
from .app import App
from .widget import Widget
from ._paint_state import PaintLayer
from ._styles_cache import FramePaint
from .box_model import (
    BoxGeometry,
    DEFAULT_LAYER,
    Dimension,
)
from .color import TRANSPARENT
from .css._style_properties import Edges
from .css.scalar import (
    Scalar,
    ScalarOffset,
    Unit,
)
from .geometry import Spacing

AUTO = Scalar(1.0, Unit.AUTO, Unit.AUTO)


FILL = Scalar(1.0, Unit.FRACTION, Unit.WIDTH)


_EMPTY_EDGES = Edges(*(("", TRANSPARENT),) * 4)


class WidgetView(BoxGeometry, PaintLayer, FramePaint, Widget):
    """The view supplies native inputs directly, without a CSS declaration mirror."""

    width: Dimension = None
    height: Dimension = AUTO
    min_width: Dimension = None
    min_height: Dimension = None
    max_width: Dimension = None
    max_height: Dimension = None
    padding = margin = Spacing(0, 0, 0, 0)
    outline = _EMPTY_EDGES
    box_sizing = "border-box"
    width_policy = "greedy"
    dock = split = "none"
    overflow_x = overflow_y = "hidden"
    scrollbar_policy = "auto"
    vertical_scrollbar_size = 2
    horizontal_scrollbar_size = 1
    scrollbar_visibility = "visible"
    align_horizontal = "left"
    align_vertical = "top"
    grid_rows = grid_columns = ()
    grid_size_columns = 1
    grid_size_rows = grid_gutter_horizontal = grid_gutter_vertical = 0
    row_span = column_span = 1
    keyline = ("none", TRANSPARENT)
    position = "relative"
    overlay = constrain_x = constrain_y = "none"
    child_layout = None
    placement_offset = None
    layer_name = DEFAULT_LAYER
    layer_order = None

    tint = TRANSPARENT
    hatch = None
    border_title_align = "left"
    border_subtitle_align = "right"

    @property
    def border(self) -> Edges:
        return _EMPTY_EDGES

    @property
    def geometry(self) -> BoxGeometry:
        return self

    @property
    def frame_paint(self) -> FramePaint:
        return self

    @property
    def paint_gutter(self) -> Spacing:
        return self.box_gutter

    def set_placement_offset(self, offset: ScalarOffset) -> None:
        self.placement_offset = offset
        self.refresh(layout=True)


class FocusWithinView(WidgetView):
    """A native widget whose focus changes invalidate its frame paint."""

    def _post_register(self, app: App) -> None:
        super()._post_register(app)
        self.listen(events.DescendantFocus, self.refresh_paint)
        self.listen(events.DescendantBlur, self.refresh_paint)

    def _on_unmount(self) -> None:
        self.unlisten(events.DescendantFocus, self.refresh_paint)
        self.unlisten(events.DescendantBlur, self.refresh_paint)
