from __future__ import annotations

from fractions import Fraction
from typing import TYPE_CHECKING, NamedTuple

from textual.geometry import Size

if TYPE_CHECKING:
    from textual.css.styles import StylesBase


class Extrema(NamedTuple):
    """Specifies minimum and maximum dimensions."""

    min_width: Fraction | None = None
    max_width: Fraction | None = None
    min_height: Fraction | None = None
    max_height: Fraction | None = None

    def apply_width(self, width: Fraction) -> Fraction:
        """Apply width extrema.

        Args:
            width: Width value.

        Returns:
            Width, clamped between minimum and maximum.

        """
        min_width, max_width = self[:2]
        if min_width is not None:
            width = max(width, min_width)
        if max_width is not None:
            width = min(width, max_width)
        return width

    def apply_height(self, height: Fraction) -> Fraction:
        """Apply height extrema.

        Args:
            height: Height value.

        Returns:
            Height, clamped between minimum and maximum.

        """
        min_height, max_height = self[2:]
        if min_height is not None:
            height = max(height, min_height)
        if max_height is not None:
            height = min(height, max_height)
        return height

    def apply_dimensions(self, width: int, height: int) -> Size:
        """Apply extrema to integer dimensions.

        Args:
            width: Integer width.
            height: Integer height.

        Returns:
            Size with extrema applied.
        """
        return Size(
            int(self.apply_width(width)),
            int(self.apply_height(height)),
        )

    @classmethod
    def resolve(
        cls, styles: StylesBase, container: Size, viewport: Size,
        width_fraction: Fraction, height_fraction: Fraction,
    ) -> Extrema:
        """Resolve native min/max rules independently of scene custody."""
        min_width_rule = styles.min_width
        max_width_rule = styles.max_width
        min_height_rule = styles.min_height
        max_height_rule = styles.max_height
        if (min_width_rule is None and max_width_rule is None
                and min_height_rule is None and max_height_rule is None):
            return NO_EXTREMA

        min_width: Fraction | int | None = None
        max_width: Fraction | int | None = None
        min_height: Fraction | int | None = None
        max_height: Fraction | int | None = None

        container -= styles.margin.totals
        if styles.box_sizing == "border-box":
            gutter_width, gutter_height = styles.gutter.totals
        else:
            gutter_width = gutter_height = 0

        if min_width_rule is not None:
            min_width = (
                min_width_rule.resolve(container, viewport, width_fraction)
                - gutter_width
            )

        if max_width_rule is not None:
            max_width = (
                max_width_rule.resolve(container, viewport, width_fraction)
                - gutter_width
            )
        if min_height_rule is not None:
            min_height = (
                min_height_rule.resolve(container, viewport, height_fraction)
                - gutter_height
            )

        if max_height_rule is not None:
            max_height = (
                max_height_rule.resolve(container, viewport, height_fraction)
                - gutter_height
            )

        return cls(min_width, max_width, min_height, max_height)


NO_EXTREMA = Extrema()
"""Extrema of a node with no min or max rules."""
