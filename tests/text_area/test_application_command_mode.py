"""Real key dispatch: idle Normal permits app commands, editing retains its keys."""
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.document._editing import AwaitKey, Escape, Left, VimInsert, VimNormal, VimVisual
from textual.widgets import Input, TextArea


class CommandModeApp(App):
    BINDINGS = [Binding("H", "navigate", priority=True),
                Binding("ctrl+shift+k", "navigate", priority=True)]
    navigations = 0

    def compose(self) -> ComposeResult:
        editor = TextArea("abcHdef")
        editor.editing_mode = VimInsert()
        yield editor
        yield Input("abcHdef", select_on_focus=False)

    def check_action(self, action, parameters):
        if action == "navigate":
            return self.screen.allows_application_commands
        return super().check_action(action, parameters)

    def action_navigate(self):
        self.navigations += 1


async def test_idle_normal_allows_priority_without_stealing_editing():
    app = CommandModeApp()
    async with app.run_test() as pilot:
        editor = app.query_one(TextArea)
        editor.focus()
        await pilot.press("H")
        assert editor.text == "HabcHdef" and app.navigations == 0
        await pilot.press("escape", "H", "ctrl+shift+k")
        assert app.navigations == 2 and editor.has_focus
        assert editor.text == "HabcHdef"
        await pilot.press("2", "H", "v", "H", "escape", "d", "H")
        assert app.navigations == 2 and editor.text == "HabcHdef"
        await pilot.press("0", "f", "H")
        assert editor.cursor_location == (0, 4) and app.navigations == 2
        await pilot.press("i", "ctrl+shift+k")
        assert editor.text == "" and app.navigations == 2


async def test_ordinary_input_retains_printable_and_nonprintable_keys():
    app = CommandModeApp()
    async with app.run_test() as pilot:
        field = app.query_one(Input)
        field.value = "abc"
        field.cursor_position = 0
        field.focus()
        await pilot.press("H", "ctrl+shift+k")
        assert field.value == "Habc" and app.navigations == 0
        assert field.has_focus
        app.screen.set_focus(None)
        await pilot.press("H", "ctrl+shift+k")
        assert app.navigations == 2


async def test_remapped_editor_commands_keep_counts_operators_and_visual_scope():
    app = CommandModeApp()
    async with app.run_test() as pilot:
        editor = app.query_one(TextArea)
        editor.focus()
        await pilot.press("escape")
        app.set_keymap({Left.binding_id(VimNormal): "z", Left.binding_id(VimVisual): "q"})
        editor.cursor_location = (0, 4)
        await pilot.press("h")
        assert editor.cursor_location == (0, 4)
        await pilot.press("z")
        assert editor.cursor_location == (0, 3)
        await pilot.press("2", "z")
        assert editor.cursor_location == (0, 1)
        await pilot.press("v", "z")
        assert editor.cursor_location == (0, 1)
        await pilot.press("q")
        assert editor.cursor_location == (0, 0)
        assert editor.selection.start != editor.selection.end
        await pilot.press("escape")
        editor.cursor_location = (0, 3)
        await pilot.press("d", "z")
        assert editor.text == "abHdef"
        await pilot.press("f", "H")
        assert editor.cursor_location == (0, 2)
        assert app.navigations == 0
        editor.read_only = True
        await pilot.press("x", "d", "z")
        assert editor.text == "abHdef"


async def test_escape_remaps_cover_insert_visual_and_pending_character_commands():
    app = CommandModeApp()
    async with app.run_test() as pilot:
        editor = app.query_one(TextArea)
        editor.focus()
        app.set_keymap({Escape.binding_id(VimInsert): "f6",
                        Escape.binding_id(VimNormal): "f7",
                        Escape.binding_id(VimVisual): "f8"})
        await pilot.press("escape")
        assert isinstance(editor.editing_mode, VimInsert)
        await pilot.press("f6")
        assert isinstance(editor.editing_mode, VimNormal)
        before = editor.cursor_location
        await pilot.press("f")
        assert isinstance(editor.editing_mode, AwaitKey)
        await pilot.press("f7")
        assert isinstance(editor.editing_mode, VimNormal)
        assert editor.cursor_location == before
        await pilot.press("f", "H")
        assert editor.cursor_location == (0, 3)
        await pilot.press("v", "escape")
        assert isinstance(editor.editing_mode, VimVisual)
        await pilot.press("f8")
        assert type(editor.editing_mode) is VimNormal
        editor.read_only = True
        editor.editing_mode = VimInsert()
        await pilot.press("f6")
        assert type(editor.editing_mode) is VimNormal
        assert editor.text == "abcHdef"
