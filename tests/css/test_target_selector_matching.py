"""Target-only selectors do not need a CSS ancestry walk or a cached match result."""

from copy import deepcopy
from itertools import product
from unittest.mock import PropertyMock, patch

import pytest

from textual.app import App
from textual.containers import Container
from textual.css.match import _check_selectors, match
from textual.css.model import CombinatorType
from textual.css.parse import parse_selectors
from textual.dom import DOMNode
from textual.widgets import Static


@pytest.mark.parametrize("query, expected", [
    ("*", True), ("Static", True), ("#target", True), (".selected", True),
    ("Static.selected#target", True), (".missing", False),
    ("Static.selected.missing", False), (".missing, #target", True),
])
def test_target_queries_do_not_construct_ancestor_paths(query, expected):
    node = Static(id="target", classes="selected")
    with patch.object(DOMNode, "css_path_nodes", new_callable=PropertyMock,
                      side_effect=AssertionError("Target-only query walked CSS ancestry")):
        assert match(parse_selectors(query), node) is expected


def test_universal_keeps_system_node_exclusion_and_matches_live_class_changes():
    node = DOMNode(classes="-textual-system selected")
    universal, selected = parse_selectors("*"), parse_selectors(".selected")
    assert not match(universal, node)
    assert match(selected, node)
    node._classes.clear()
    assert match(universal, node)
    assert not match(selected, node)


def test_match_parity_across_compounds_children_descendants_and_alternatives():
    root = DOMNode(id="root", classes="outer selected")
    middle = DOMNode(classes="middle selected")
    leaf = DOMNode(id="leaf", classes="leaf selected")
    middle._attach(root)
    leaf._attach(middle)
    terms = ("*", "DOMNode", ".selected", ".missing", "#leaf", "DOMNode.leaf")
    queries = [*terms, *(f"{left}{join}{right}" for left, join, right in product(
        terms, (" ", " > ", ", "), terms)),
        ".outer .selected > .leaf", ".outer > .selected .leaf", ".outer > .leaf",
        ".selected.selected", ".outer > .middle > .leaf"]
    for node in (root, middle, leaf):
        for query in queries:
            selectors = parse_selectors(query)
            expected = any(_check_selectors(group.selectors, node.css_path_nodes)
                           for group in selectors)
            assert match(iter(selectors), node) == expected, (query, node)


def test_custom_css_ancestry_remains_authoritative_for_relational_queries():
    outer = DOMNode(classes="virtual")
    physical = DOMNode(classes="physical")

    class VirtualPath(DOMNode):
        @property
        def css_path_nodes(self):
            return [outer, self]

    leaf = VirtualPath(classes="leaf")
    leaf._attach(physical)
    assert match(parse_selectors(".virtual > .leaf"), leaf)
    assert not match(parse_selectors(".physical .leaf"), leaf)
    assert match(parse_selectors("VirtualPath.leaf"), leaf)


def test_selector_edits_do_not_leave_a_stale_dependency_classification():
    root, leaf = DOMNode(classes="outer"), DOMNode(classes="leaf")
    leaf._attach(root)
    group = deepcopy(parse_selectors(".outer.leaf")[0])
    assert not match((group,), leaf)
    group.selectors[1].combinator = CombinatorType.DESCENDENT
    group.__post_init__()
    assert match((group,), leaf)


async def test_target_pseudo_classes_keep_inherited_disabled_and_native_focus():
    app = App()
    async with app.run_test() as pilot:
        first, second = Static("first"), Static("second")
        first.can_focus = second.can_focus = True
        parent = Container(first, second)
        await app.mount(parent)
        await pilot.pause()
        for disabled in (True, False, True, False):
            parent.disabled = disabled
            await pilot.pause()
            assert match(parse_selectors("Static:disabled"), first) == disabled
            assert match(parse_selectors("Static:enabled"), first) != disabled
        for focused in (first, second):
            focused.focus()
            await pilot.pause()
            assert match(parse_selectors("Static:focus"), first) == (focused is first)
            assert match(parse_selectors("Static:focus"), second) == (focused is second)
