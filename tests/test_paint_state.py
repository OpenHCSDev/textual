from unittest.mock import patch

import pytest
from rich.style import Style

from textual._paint_state import EMPTY_PAINT, PaintLayer, PaintState
from textual.color import Color, TRANSPARENT


def test_empty_layer_reuses_settled_parent():
    assert PaintState.resolve(EMPTY_PAINT, PaintLayer()) is EMPTY_PAINT
    parent = EMPTY_PAINT._replace(opacity=.5, text_style=Style(bold=True))
    assert PaintState.resolve(parent, PaintLayer()) is parent


def test_first_empty_child_advances_colored_parent_background_base():
    layer = PaintLayer()
    layer.paint_background = Color.parse("red 50%")
    parent = PaintState.resolve(EMPTY_PAINT, layer)
    assert parent.base_background != parent.layered_background
    child = PaintState.resolve(parent, PaintLayer())
    assert child is not parent
    assert child == parent._replace(base_background=parent.layered_background)
    assert PaintState.resolve(child, PaintLayer()) is child


@pytest.mark.parametrize(("name", "value"), [
    ("paint_background", TRANSPARENT),
    ("paint_background", Color.parse("red")),
    ("paint_foreground", TRANSPARENT),
    ("paint_foreground", Color.parse("blue")),
    ("layer_opacity", .5),
    ("text_style", Style(bold=True)),
    ("auto_color", True),
])
def test_authored_layer_does_not_take_identity_path(name, value):
    layer = PaintLayer()
    setattr(layer, name, value)
    assert PaintState.resolve(EMPTY_PAINT, layer) is not EMPTY_PAINT


def test_derived_visible_background_does_not_take_identity_path():
    with patch.object(PaintLayer, "background_color", property(lambda self: Color.parse("red"))):
        resolved = PaintState.resolve(EMPTY_PAINT, PaintLayer())
    assert resolved is not EMPTY_PAINT
    assert resolved.layered_background == Color.parse("red")
