import pytest

from textual.layouts.factory import MissingLayout, get_layout
from textual.layouts.vertical import VerticalLayout
from textual.layouts.grid import GridLayout


def test_get_layout_valid_layout():
    layout = get_layout("vertical")
    assert type(layout) is VerticalLayout


def test_get_layout_invalid_layout():
    with pytest.raises(MissingLayout):
        get_layout("invalid")


def test_document_key_reads_current_grid_configuration_without_republishing_supply():
    layout = GridLayout()
    implementation = type(layout)._document_implementation
    original = layout.document_key()
    layout.min_column_width = 8
    assert layout.document_key() != original
    assert type(layout)._document_implementation is implementation
    acquired = layout.acquire_document()
    assert acquired.min_column_width == 8
    assert acquired.document_key() == layout.document_key()
