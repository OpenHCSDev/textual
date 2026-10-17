"""Inherited paint and the declaration inputs that produce it."""
from __future__ import annotations

from dataclasses import replace
from typing import NamedTuple
from rich.style import NULL_STYLE, Style
from textual.color import Color, TRANSPARENT
from textual.style import Style as VisualStyle


class PaintLayer:
    """One local colour layer, independent of how its inputs are declared."""

    paint_foreground: Color | None = None
    paint_background: Color | None = None
    background_tint = TRANSPARENT
    text_style = NULL_STYLE
    text_opacity = layer_opacity = 1.0
    auto_color = False

    @property
    def paint_layer(self) -> PaintLayer:
        return self

    @property
    def background_color(self) -> Color:
        color = self.paint_background
        return TRANSPARENT if color is None else color


class PaintState(NamedTuple):
    background: Color
    foreground: Color
    text_opacity: float
    text_style: Style
    opacity: float
    base_background: Color
    layered_background: Color

    @property
    def rich_style(self) -> Style:
        background, color = self.background, self.foreground
        return self.text_style + Style.from_color(
            (background + color).rich_color if (background.a or color.a) else None,
            background.rich_color if background.a else None,
        )

    @property
    def visual_style(self) -> VisualStyle:
        return replace(VisualStyle.from_rich_style(self.text_style),
                       background=self.background, foreground=self.foreground)

    def component_style(self, node, *names: str, partial: bool = False) -> VisualStyle:
        """Apply component declarations to this render's already inherited paint."""
        background = TRANSPARENT if partial else self.background
        foreground = (Color(255, 255, 255, 0) if partial
                      else self.foreground.multiply_alpha(self.text_opacity))
        text_style = NULL_STYLE if partial else self.text_style
        opacity = 1.0 if partial else self.opacity
        for name in names:
            layer = node.get_component_styles(name)
            opacity *= layer.layer_opacity
            local_background = layer.paint_background
            if local_background is not None:
                tinted = local_background.tint(layer.background_tint)
                text_background = background + tinted
                background = (background.blend(tinted, 1 - tinted.a).multiply_alpha(opacity)
                              if partial else background + tinted.multiply_alpha(opacity))
            else:
                text_background = background
            if (color := layer.paint_foreground) is not None:
                foreground = color.multiply_alpha(layer.text_opacity)
            text_style += layer.text_style
            if layer.auto_color:
                foreground = text_background.get_contrast_text(foreground.a)
        return replace(VisualStyle.from_rich_style(text_style),
                       background=background, foreground=foreground)

    def get_style(self, node, style: VisualStyle | str) -> VisualStyle:
        """Decode Content's inline/component style using this render's paint."""
        if isinstance(style, VisualStyle):
            return style
        if style.startswith("."):
            owner = node.find_component_owner(style[1:])
            return (VisualStyle() if owner is None
                    else self.component_style(owner, style[1:], partial=True))
        try:
            return node._parse_visual_style(style)
        except Exception:
            return VisualStyle()

    def link_style(self, styles, *, hover: bool = False) -> Style:
        """Resolve link paint against the original layered background."""
        if hover:
            background, color = styles.link_background_hover, styles.link_color_hover
            auto, text = styles.auto_link_color_hover, styles.link_style_hover
        else:
            background, color = styles.link_background, styles.link_color
            auto, text = styles.auto_link_color, styles.link_style
        painted_background = self.layered_background + background
        painted_color = painted_background + (
            painted_background.get_contrast_text(color.a) if auto else color)
        return text + Style.from_color(
            painted_color.rich_color,
            painted_background.rich_color if hover or background.a else None,
        )

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
            background, foreground,
            parent.text_opacity if local_foreground is None else layer.text_opacity,
            parent.text_style + layer.text_style, opacity,
            parent.layered_background,
            parent.layered_background + tinted.multiply_alpha(opacity),
        )


EMPTY_PAINT = PaintState(
    Color(0, 0, 0, 0), Color(255, 255, 255, 0), 1.0,
    NULL_STYLE, 1.0, Color(0, 0, 0, 0), Color(0, 0, 0, 0),
)
