import pytest

from textual.layout import Layout
from textual.layouts.horizontal import HorizontalLayout
from textual.layouts.vertical import VerticalLayout
from textual.screen import Screen
from textual.widget import Widget


@pytest.mark.parametrize(
    "layout,display,expected_in_displayed_children",
    [
        (HorizontalLayout, "block", True),
        (VerticalLayout, "block", True),
        (HorizontalLayout, "none", False),
        (VerticalLayout, "none", False),
    ],
)
def test_nodes_take_display_property_into_account_when_they_display_their_children(
    layout: type[Layout], display: str, expected_in_displayed_children: bool
):
    widget = Widget(name="widget that might not be visible 🥷 ")
    widget.styles.display = display

    screen = Screen()
    screen.styles.layout = layout()
    screen._add_child(widget)

    displayed_children = screen.displayed_children
    assert isinstance(displayed_children, list)
    assert (widget in screen.displayed_children) is expected_in_displayed_children
