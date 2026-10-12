"""New unrelated widget CSS must not discard already valid style work."""

from unittest.mock import patch

from textual.color import Color
from textual.css.model import RuleSet
from textual.css.stylesheet import Stylesheet
from textual.dom import DOMNode


def test_unrelated_source_keeps_match_cache_but_relevant_source_invalidates():
    sheet = Stylesheet()
    sheet.add_source(".item { color: red; }", read_from=("base", ""))
    node = DOMNode(classes="item")
    sheet.apply(node)
    sheet.add_source(".unrelated { color: blue; }", read_from=("new-widget", ""))
    with patch.object(RuleSet, "check", autospec=True, side_effect=RuleSet.check) as matching:
        sheet.apply(node)
        matching.assert_not_called()
    assert node.styles.color == Color.parse("red")
    sheet.add_source(".item { color: blue; }", read_from=("override", ""))
    sheet.apply(node)
    assert node.styles.color == Color.parse("blue")


def test_source_order_remains_part_of_cache_identity():
    sheet = Stylesheet()
    sheet.add_source(".item { color: red; }", read_from=("first", ""))
    sheet.add_source(".item { color: blue; }", read_from=("second", ""))
    node = DOMNode(classes="item")
    sheet.apply(node)
    assert node.styles.color == Color.parse("blue")
    first = sheet.source.pop(("first", ""))
    sheet.source[("first", "")] = first
    sheet.parse()
    sheet.apply(node)
    assert node.styles.color == Color.parse("red")


def test_variables_and_source_removal_cannot_reuse_old_rule_results():
    sheet = Stylesheet(variables={"shade": "red"})
    sheet.add_source(".item { color: $shade; }", read_from=("base", ""))
    sheet.add_source(".item { color: green; }", read_from=("override", ""))
    node = DOMNode(classes="item")
    sheet.apply(node)
    assert node.styles.color == Color.parse("green")
    sheet.source.pop(("override", ""))
    sheet.parse()
    sheet.apply(node)
    assert node.styles.color == Color.parse("red")
    sheet.set_variables({"shade": "blue"})
    sheet.reparse()
    sheet.apply(node)
    assert node.styles.color == Color.parse("blue")
