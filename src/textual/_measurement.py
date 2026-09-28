"""Declaration-owned available-height dependencies for optional layout reuse."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Callable, TypeVar

from textual.css.scalar import Scalar, Unit

if TYPE_CHECKING:
    from textual.widget import Widget


class HeightDependency(ABC):
    @abstractmethod
    def depends(self, widget: Widget) -> bool:
        """Whether incoming container height can change the measured result."""

    def box_depends(self, widget: Widget) -> bool:
        return self.depends(widget) or widget._has_relative_children_height


class ContextHeight(HeightDependency):
    def depends(self, widget: Widget) -> bool:
        return True


class IndependentHeight(HeightDependency):
    def depends(self, widget: Widget) -> bool:
        return False


class NativeWidgetHeight(HeightDependency):
    def depends(self, widget: Widget) -> bool:
        if not widget.is_container:
            # Native leaf visuals receive rules and width, not container height.
            return False
        if not widget._native_measurement_layout_hooks:
            return True
        return widget.layout._content_height_dependency.depends(widget)

    def box_depends(self, widget: Widget) -> bool:
        if not widget.is_container:
            return False
        if not widget._native_measurement_layout_hooks:
            return True
        return widget.layout._content_height_dependency.box_depends(widget)


class NativeLayoutHeight(HeightDependency):
    def depends(self, widget: Widget) -> bool:
        # Conservatively require a declaration for the arranger too. Even the
        # fixed-zero branch need not opt unknown/custom layout hooks into reuse.
        return arrangement_depends_on_available_height(widget)

    def box_depends(self, widget: Widget) -> bool:
        if _arrangement_wrapper_uses_height(widget):
            return True
        return widget.layout._arrangement_height_dependency.box_depends(widget)


class FlowHeight(HeightDependency):
    def depends(self, widget: Widget) -> bool:
        styles = widget.styles
        if (not widget._native_measurement_layout_hooks
                or styles.align_horizontal != "left" or styles.align_vertical != "top"):
            return True
        for child in widget.displayed_children:
            child_styles = child.styles
            if child_styles.is_docked or child_styles.is_split or child_styles.overlay == "screen":
                return True
            # Match native auto-parent stretch semantics, which treat all
            # percentage heights as relative even for a raw width-axis scalar.
            if child_styles.is_relative_height:
                return True
            if child._box_depends_on_available_height():
                return True
        return False

    # Child box proofs already reject auto descendants with relative heights.
    # Rewalking that same subtree through _has_relative_children_height would
    # duplicate the dependency traversal we just completed.
    box_depends = depends


class StreamHeight(HeightDependency):
    def depends(self, widget: Widget) -> bool:
        # Stream measures content directly, even when a child's CSS box height
        # is fixed. A box proof alone cannot certify this operation.
        return any(child._content_height_dependency.depends(child)
                   for child in widget.displayed_children)


def _scalar_uses_height(scalar: Scalar, *, height_fraction: bool = False) -> bool:
    unit = scalar.percent_unit if scalar.unit is Unit.PERCENT else scalar.unit
    return (type(scalar).resolve is not Scalar.resolve or unit is Unit.HEIGHT
            or (height_fraction and unit is Unit.FRACTION))


def _content_width_uses_height(widget: Widget) -> bool:
    return (not widget._native_content_width or (widget.is_container and (
        not widget._native_measurement_layout_hooks
        or widget.layout._content_width_dependency.depends(widget)
    )))


class GridHeight(HeightDependency):
    def depends(self, widget: Widget) -> bool:
        styles = widget.styles
        rows, columns = styles.grid_rows or (), styles.grid_columns or ()
        # Default rows become fractional at nonzero height for non-auto parents.
        if (not rows and not styles.is_auto_height
                or any(_scalar_uses_height(row, height_fraction=True) for row in rows)
                or any(_scalar_uses_height(column) for column in columns)):
            return True
        for child in widget.displayed_children:
            child_styles = child.styles
            # Auto cells pass the outer size directly to content measurement
            # and extrema. Final boxes/offsets receive the already-resolved cell
            # size, so fractional child boxes are safe once tracks are proven.
            if child._content_height_dependency.depends(child):
                return True
            if _content_width_uses_height(child):
                return True
            if any(scalar is not None and _scalar_uses_height(scalar) for scalar in (
                child_styles.min_width, child_styles.max_width,
                child_styles.min_height, child_styles.max_height,
            )):
                return True
        return False


CONTEXT_HEIGHT = ContextHeight()
INDEPENDENT_HEIGHT = IndependentHeight()
NATIVE_WIDGET_HEIGHT = NativeWidgetHeight()
NATIVE_LAYOUT_HEIGHT = NativeLayoutHeight()
FLOW_HEIGHT = FlowHeight()
STREAM_HEIGHT = StreamHeight()
GRID_HEIGHT = GridHeight()

Function = TypeVar("Function", bound=Callable)


def height_dependency(policy: HeightDependency) -> Callable[[Function], Function]:
    """Declare a method's dependency; unknown overrides remain context-dependent.

    This does not cache a method's result or retain a widget. A declaration must
    describe the whole implementation, including additional work around super().
    """
    def decorate(function: Function) -> Function:
        function._height_dependency = policy  # type: ignore[attr-defined]
        return function
    return decorate


def _local_box_inputs(widget: Widget) -> tuple[bool, bool, bool]:
    """Resolve local scalar dependencies once per owning style generation."""
    styles = widget.styles
    revision = styles._cache_key
    cached = widget.__dict__.get("_height_style_dependency_cache")
    if cached is not None and cached[0] == revision:
        return cached[1]
    width, height = styles.width, styles.height
    min_width, max_width = styles.min_width, styles.max_width
    min_height, max_height = styles.min_height, styles.max_height
    for scalar in (width, height, min_width, max_width, min_height, max_height):
        if scalar is not None:
            # Compile this check at the style-plan boundary, not each cache hit.
            # A custom scalar resolver need not obey its nominal unit's inputs.
            if type(scalar).resolve is not Scalar.resolve:
                result = (True, False, False)
                break
            unit = scalar.percent_unit if scalar.unit is Unit.PERCENT else scalar.unit
            if unit is Unit.HEIGHT:
                result = (True, False, False)
                break
    else:
        result = (
            height is None or height.is_fraction
            or (min_height is not None and min_height.is_fraction)
            # Non-cell max heights have a zero-height auto-parent exception.
            or (max_height is not None and not max_height.is_cells),
            width is not None and (width.is_auto or width.is_fraction),
            height is not None and height.is_auto,
        )
    widget._height_style_dependency_cache = revision, result
    return result


def box_depends_on_available_height(widget: Widget) -> bool:
    """Conservative proof for the native box resolver, including its extrema."""
    if not widget._native_box_measurement:
        return True
    depends, content_width, content_height = _local_box_inputs(widget)
    if depends:
        return True
    if content_width:
        if not widget._native_content_width:
            return True
        if widget.is_container and (
            not widget._native_measurement_layout_hooks
            or widget.layout._content_width_dependency.depends(widget)
        ):
            return True
    if content_height:
        return widget._content_height_dependency.box_depends(widget)
    return False


def _arrangement_wrapper_uses_height(widget: Widget) -> bool:
    styles = widget.styles
    if (not widget._native_measurement_layout_hooks
            or styles.align_horizontal != "left" or styles.align_vertical != "top"):
        return True
    return any(child.styles.is_docked or child.styles.is_split
               or child.styles.overlay == "screen" for child in widget.displayed_children)


def arrangement_depends_on_available_height(widget: Widget) -> bool:
    """Prove the complete native dock/alignment/flow arrangement, not just boxes."""
    return (_arrangement_wrapper_uses_height(widget)
            or widget.layout._arrangement_height_dependency.depends(widget))
