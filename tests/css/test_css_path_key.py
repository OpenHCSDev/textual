"""Linear ancestry keys preserve inherited and customized pseudo-class state."""

from textual.app import App, ComposeResult
from textual.color import Color
from textual.containers import Container
from textual.dom import DOMNode
from textual.widgets import Static


class CustomDisabled(Container):
    @property
    def is_disabled(self):
        return True


class CustomKey(Container):
    @property
    def _pseudo_classes_cache_key(self):
        return (*super()._pseudo_classes_cache_key, self.has_class("extra"))


class Badge(Static):
    COMPONENT_CLASSES = {"path-key--badge"}


class PathApp(App):
    CSS = """
    Badge { color: red; }
    Container:disabled Badge { color: blue; }
    Badge > .path-key--badge { color: red; }
    Container:disabled Badge > .path-key--badge { color: blue; }
    #referenced { background: green; }
    """

    def compose(self) -> ComposeResult:
        for index, container in enumerate((Container, CustomDisabled, CustomKey)):
            with Container(id=f"root-{index}"):
                with container(classes="scope", id="referenced" if index == 0 else None):
                    with Container():
                        yield Badge(str(index), id=f"badge-{index}")


async def test_inherited_disabled_rules_and_components_survive_repeated_updates():
    app = PathApp()
    async with app.run_test() as pilot:
        await pilot.pause()
        root = app.query_one("#root-0")
        badge = app.query_one("#badge-0", Badge)
        other = app.query_one("#badge-2", Badge)
        for disabled, color in ((True, "blue"), (False, "red"), (True, "blue")):
            root.disabled = disabled
            await pilot.pause()
            app.stylesheet.update(app.screen)
            assert badge.styles.color == Color.parse(color)
            assert badge.get_component_styles("path-key--badge").color == Color.parse(color)
            assert other.styles.color == Color.parse("red")
            assert other.get_component_styles("path-key--badge").color == Color.parse("red")


async def test_nonwidget_parent_breaks_disabled_inheritance():
    app = PathApp()
    async with app.run_test() as pilot:
        await pilot.pause()
        root = app.query_one("#root-0")
        root.disabled = True
        virtual = DOMNode()
        virtual._attach(root)
        child = Static()
        child._attach(virtual)
        path = child.css_path_nodes
        result = app.stylesheet._css_path_key(path, frozenset())
        assert result[-1][3] == child._pseudo_classes_cache_key
        assert not result[-1][3][-1]
