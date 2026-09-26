import pytest

from textual.css.stylesheet import Stylesheet


@pytest.mark.parametrize("css, local", [
    (".hide { display: none; }", True),
    ("Widget > .hide.extra { display: none; }", True),
    ("Widget > .extra.hide:hover { display: none; }", True),
    (".hide > Label { display: none; }", False),
    (".hide.extra Label { display: none; }", False),
    (".hide { color: red; }", False),
    (".hide { display: none; background: red; }", False),
    (".other { display: none; }", False),
])
def test_display_only_class_scope_comes_from_parsed_declarations(css, local):
    stylesheet = Stylesheet()
    stylesheet.add_source(css, read_from=("fixture", "display"))
    assert stylesheet.is_local_display_class("hide") is local


def test_class_scope_is_invalidated_by_source_replacement_and_reparse():
    stylesheet = Stylesheet()
    location = ("fixture", "display")
    stylesheet.add_source(".hide { display: none; }", read_from=location)
    assert stylesheet.is_local_display_class("hide")
    stylesheet.add_source(".hide Label { color: red; }", read_from=location)
    assert not stylesheet.is_local_display_class("hide")
    stylesheet.add_source(".hide { display: none; }", read_from=location)
    stylesheet.reparse()
    assert stylesheet.is_local_display_class("hide")
