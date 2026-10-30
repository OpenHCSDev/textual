"""Arrow identities supply modal spellings, including controls not hand-patched."""
from textual import widgets
from textual.app import App, ComposeResult
from textual.containers import VerticalScroll
from textual.document._editing import EditingMode, VimMode
from textual.dom import DOMNode
from textual.events import Key
from textual.keys import DownKey, NavigationKey
from textual.screen import Screen
from textual.widgets import Input, TextArea, Tree


def test_navigation_spellings_follow_every_declared_context() -> None:
    # Load the declared widget exports before traversing the actual class graph.
    for name in widgets.__all__:
        getattr(widgets, name)
    checked = 0
    for owner in DOMNode.contexts():
        standard = owner.binding_defaults(EditingMode)
        modal = owner.binding_defaults(VimMode)
        for direction in NavigationKey.__subclasses__():
            arrows = tuple(
                binding for binding in modal.key_to_bindings.get(direction.key.value, ())
                if binding.declared_key == direction()
            )
            if any(binding.declared_key == direction()
                   for binding in standard.key_to_bindings.get(direction.key.value, ())):
                assert arrows, (owner, direction)
            for arrow in arrows:
                assert arrow.with_key(direction.modal) in modal.key_to_bindings.get(direction.modal, ()), (owner, direction)
                assert arrow.id == direction().binding_identity(VimMode)
                assert not any(
                    binding.declared_key == direction()
                    for binding in standard.key_to_bindings.get(direction.modal, ())
                ), (owner, direction)
                checked += 1
        assert list(modal.project(VimMode)) == list(modal), owner
    assert checked > 0


class VimProfile(VimMode):
    """A modal scope for native controls, without starting an external editor."""

    @property
    def binding_mode(self) -> type[EditingMode]:
        return VimMode

    async def handle_key(self, editor: TextArea, event: Key) -> bool:
        return await EditingMode.handle_key(self, editor, event)


class NavigationScreen(Screen):
    @property
    def key_mode(self) -> type[EditingMode]:
        return VimProfile

    def compose(self) -> ComposeResult:
        tree = Tree("root")
        tree.root.add_leaf("first")
        tree.root.add_leaf("second")
        tree.root.expand()
        tree.styles.height = 8
        yield tree
        with VerticalScroll():
            yield Input()


class NavigationApp(App[None]):
    def get_default_screen(self) -> Screen:
        return NavigationScreen()


async def test_modal_tree_input_and_arrow_remap() -> None:
    app = NavigationApp()
    async with app.run_test() as pilot:
        tree = app.query_one(Tree)
        entry = app.query_one(Input)
        tree.focus()
        await pilot.pause()
        tree.move_cursor(tree.root)
        await pilot.press("j")
        assert tree.cursor_node == tree.root.children[0]
        entry.focus()
        await pilot.press("h", "j", "k", "l")
        assert entry.value == "hjkl"
        assert entry.binding_mode is EditingMode
        assert app.query_one(VerticalScroll).scroll_y == 0
        tree.focus()
        await pilot.pause()
        app.set_keymap({DownKey().binding_identity(VimMode): "n"})
        await pilot.press("n")
        assert tree.cursor_node == tree.root.children[1]
        await pilot.press("j")
        assert tree.cursor_node == tree.root.children[1]
        assert entry.value == "hjkl"
