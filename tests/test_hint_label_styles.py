"""Presentation choices leave hint identity, placement and activation unchanged."""
import pytest

from textual.app import App
from textual.hint_labels import FullKeyHints, NextLetterHints
from textual.screen import Screen
from textual.widgets import Input, Static
from textual.widgets._hints import HintLabel, HintSession


class LabelScreen(Screen):
    def __init__(self, style):
        super().__init__()
        self.style = style

    @property
    def hint_label_style(self):
        return self.style


class LabelApp(App):
    CSS = "Input { height: 3; } Static { height: 1; }"
    picked = None

    def __init__(self, style):
        super().__init__()
        self.style = style

    def get_default_screen(self):
        return LabelScreen(self.style)

    def compose(self):
        yield Input("unchanged draft")
        for index in range(27):
            yield Static(f"[@click=app.pick({index})]Target {index}[/]", id=f"target-{index}")

    def action_pick(self, index):
        self.picked = index


@pytest.mark.parametrize("style,before,refined", [
    (NextLetterHints, slice(0, 1), slice(1, 2)),
    (FullKeyHints, slice(None), slice(None)),
])
async def test_both_styles_keep_the_whole_key_and_original_target(style, before, refined):
    app = LabelApp(style)
    async with app.run_test(size=(70, 36)) as pilot:
        original = app.query_one(Input)
        original.focus()
        await app.screen.action_show_hints()
        await pilot.pause()
        session = app.screen.query_one(HintSession)
        assigned = tuple((label.target.identity, label.text) for label in session.labels)
        for label in session.labels:
            assert label.render().plain == label.text[before]
            assert label.screen._compositor.published_widgets[label][0].offset == label.target.region.offset
        chosen = next(label for label in session.labels if label.target.widget.id == "target-13")
        key = chosen.text
        assert len(key) == 2
        await pilot.press(key[0])
        await pilot.pause()
        assert tuple((label.target.identity, label.text) for label in session.labels) == assigned
        assert chosen.render().plain == key[refined]
        assert chosen.screen._compositor.published_widgets[chosen][0].offset == chosen.target.region.offset
        await pilot.press(key[1])
        await pilot.pause()
        assert app.picked == 13
        assert original.has_focus and original.value == "unchanged draft"
        assert not app.screen.query(HintSession)
        await app.screen.action_show_hints()
        await pilot.press("escape")
        await pilot.pause()
        assert original.has_focus and not app.screen.query(HintLabel)
