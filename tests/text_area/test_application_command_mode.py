"""Real key dispatch: idle Normal permits app commands, editing retains its keys."""
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.document._editing import VimInsert
from textual.widgets import Input, TextArea


class CommandModeApp(App):
    BINDINGS = [Binding("H", "navigate", priority=True),
                Binding("ctrl+shift+k", "navigate", priority=True)]
    navigations = 0

    def compose(self) -> ComposeResult:
        editor = TextArea("abcHdef")
        editor.editing_mode = VimInsert()
        yield editor
        yield Input("abcHdef")

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
