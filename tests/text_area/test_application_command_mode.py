"""Ordinary Input retains its keys when application commands are unavailable."""
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.widgets import Input


class CommandModeApp(App):
    BINDINGS = [Binding("H", "navigate", priority=True),
                Binding("ctrl+shift+k", "navigate", priority=True)]
    navigations = 0

    def compose(self) -> ComposeResult:
        yield Input("abcHdef", select_on_focus=False)

    def check_action(self, action, parameters):
        if action == "navigate":
            return self.screen.allows_application_commands
        return super().check_action(action, parameters)

    def action_navigate(self):
        self.navigations += 1


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
