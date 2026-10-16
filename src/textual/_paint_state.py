"""Inherited paint and the declaration inputs that produce it."""
from __future__ import annotations

from typing import NamedTuple
from rich.style import NULL_STYLE, Style
from textual.color import Color, TRANSPARENT


class PaintLayer:
    """One local colour layer, independent of how its inputs are declared."""

    paint_foreground: Color | None
    paint_background: Color | None
    background_tint: Color
    text_style: Style
    text_opacity: float
    layer_opacity: float
    auto_color: bool
    paint_key: int | None
    paint_cacheable: bool

    @property
    def background_color(self) -> Color:
        color = self.paint_background
        return TRANSPARENT if color is None else color


class PaintState(NamedTuple):
    parent: PaintState | None
    style_key: int | None
    background: Color
    foreground: Color
    text_style: Style
    opacity: float
    base_background: Color
    layered_background: Color
    cacheable: bool = True

    def same_paint(self, other: PaintState) -> bool:
        return self[2:8] == other[2:8]

    @classmethod
    def resolve(cls, parent: PaintState, layer: PaintLayer) -> PaintState:
        """Apply one declaration layer, preserving native alpha order."""
        opacity = parent.opacity * layer.layer_opacity
        local_background = layer.paint_background
        tinted = layer.background_color.tint(layer.background_tint)
        background = text_background = parent.background
        if local_background is not None:
            text_background = background + tinted
            background += tinted.multiply_alpha(opacity)
        local_foreground = layer.paint_foreground
        foreground = parent.foreground if local_foreground is None else local_foreground
        if layer.auto_color:
            foreground = text_background.get_contrast_text(foreground.a)
        return cls(
            parent, layer.paint_key, background, foreground,
            parent.text_style + layer.text_style, opacity,
            parent.layered_background,
            parent.layered_background + tinted.multiply_alpha(opacity),
            parent.cacheable and layer.paint_cacheable,
        )


EMPTY_PAINT = PaintState(
    None, -1, Color(0, 0, 0, 0), Color(255, 255, 255, 0),
    NULL_STYLE, 1.0, Color(0, 0, 0, 0), Color(0, 0, 0, 0),
)
