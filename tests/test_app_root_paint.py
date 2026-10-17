"""The app's declared foreground reaches ordinary, uncoloured containers."""
from textual.app import App, ComposeResult
from textual.containers import Vertical
from textual.widgets import Checkbox, Collapsible, Label
from textual.widgets._collapsible import CollapsibleTitle


class RootPaintApp(App):
    AUTO_FOCUS = ""

    def compose(self) -> ComposeResult:
        with Vertical(id="uncoloured"):
            yield Label("Visible label", id="label")
            yield Checkbox("Visible checkbox", id="checkbox")
            yield Collapsible(Label("Contents"), title="Visible title", collapsed=False)


async def test_app_defaults_reach_labels_without_local_colour():
    app = RootPaintApp()
    async with app.run_test(size=(60, 20)) as pilot:
        await pilot.pause()
        container = app.query_one("#uncoloured")
        assert not container.styles.has_rule("color")
        nodes = (app.query_one("#label", Label), app.query_one("#checkbox", Checkbox),
                 app.query_one(CollapsibleTitle))
        print("App defaults:", app.styles.color, app.styles.background)
        print("Stored root:", app._paint_state)
        for node in nodes:
            print(type(node).__name__, "foreground", repr(node._paint_state.foreground),
                  "background", repr(node._paint_state.background))
        for node in nodes:
            paint = node._paint_state
            assert paint.foreground.a > 0, (type(node).__name__, paint)
            assert paint.foreground != paint.background, (type(node).__name__, paint)
        assert app._paint_state.foreground == app.styles.paint_foreground
        assert app.query_one("#label", Label)._paint_state.foreground == app._paint_state.foreground
        # Raw root rule publication must update already attached descendants too.
        app.styles.color = "#80c0ff"
        assert app._paint_state.foreground == app.styles.paint_foreground
        assert app.query_one("#label", Label)._paint_state.foreground == app._paint_state.foreground
        assert app.query_one("#checkbox", Checkbox)._paint_state.foreground == app._paint_state.foreground
