"""Reapplying static CSS should not trigger unchanged descriptor side effects."""

from unittest.mock import patch

from textual.app import App, ComposeResult
from textual.color import Color
from textual.containers import VerticalScroll
from textual.css.stylesheet import Stylesheet
from textual.widgets import Static


async def test_identical_rules_keep_notification_without_repainting_scrollbars():
    class ScrollApp(App):
        CSS = "VerticalScroll { height: 4; color: red; } Static { height: 1; }"

        def compose(self) -> ComposeResult:
            with VerticalScroll():
                for index in range(10):
                    yield Static(str(index))

    app = ScrollApp()
    async with app.run_test() as pilot:
        await pilot.pause()
        scroller = app.query_one(VerticalScroll)
        child = app.query_one(Static)
        assert scroller.show_vertical_scrollbar
        rules = scroller.styles.base.get_rules()
        with patch.object(scroller.vertical_scrollbar, "refresh", wraps=scroller.vertical_scrollbar.refresh) as repaint:
            with patch.object(scroller, "notify_style_update", wraps=scroller.notify_style_update) as notify:
                Stylesheet.replace_rules(scroller, rules.copy())
                repaint.assert_not_called()
                notify.assert_called_once()

        changed = dict(rules, color=Color.parse("blue"), scrollbar_color=Color.parse("green"))
        with patch.object(scroller.vertical_scrollbar, "refresh", wraps=scroller.vertical_scrollbar.refresh) as repaint:
            Stylesheet.replace_rules(scroller, changed)
            assert repaint.called
        await pilot.pause()
        assert scroller.styles.scrollbar_color == Color.parse("green")
        assert child.rich_style.color.get_truecolor() == (0, 0, 255)

        # Clearing a declaration must still restore inheritance and defaults.
        changed.pop("color")
        Stylesheet.replace_rules(scroller, changed)
        assert not scroller.styles.base.has_rule("color")
        Stylesheet.replace_rules(scroller, rules)
        await pilot.pause()
        assert child.rich_style.color.get_truecolor() == (255, 0, 0)
