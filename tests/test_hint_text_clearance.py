"""Hints preserve the displayed target text, not only separation between keys."""

from textual.app import App, ComposeResult
from textual.screen import Screen
from textual.widgets import Static
from textual.widgets._hints import HintLabel, HintSession


class ReadableHintsApp(App):
    CSS = "Static { height: 1; }"
    picked: int | None = None

    def compose(self) -> ComposeResult:
        for index in range(27):
            yield Static(f"[@click=app.pick({index})]Target {index:02}[/]", id=f"target-{index}")

    def action_pick(self, index: int) -> None:
        self.picked = index


def screen_rows(app: App) -> list[str]:
    return [strip.text for strip in app.screen._compositor.render_strips()]


async def test_two_letter_hints_preserve_composed_target_text():
    app = ReadableHintsApp()
    async with app.run_test(size=(70, 35)) as pilot:
        await pilot.pause()
        before = screen_rows(app)
        await app.screen.action_show_hints()
        await pilot.pause()
        labels = list(app.screen.query(HintLabel))
        assert len(labels) == 27
        assert all(len(label.text) == 2 for label in labels)
        after = screen_rows(app)
        for row in range(27):
            assert after[row][:9] == before[row][:9], (row, before[row], after[row])
        chosen = next(label for label in labels if label.target.widget.id == "target-13")
        await pilot.press(*chosen.text)
        await pilot.pause()
        assert app.picked == 13
        assert not app.screen.query(HintSession)


class DenseHintsApp(App):
    CSS = "Static { height: 1; }"
    picked: int | None = None

    def compose(self) -> ComposeResult:
        yield Static(" ".join(f"[@click=app.pick({index})]x[/]" for index in range(27)))

    def action_pick(self, index: int) -> None:
        self.picked = index


async def test_dense_two_letter_hints_keep_body_and_all_targets():
    """No two-cell body gap: the footer legend must retain every hint."""
    app = DenseHintsApp()
    async with app.run_test(size=(54, 2)) as pilot:
        await pilot.pause()
        before = screen_rows(app)[0]
        await app.screen.action_show_hints()
        await pilot.pause()
        labels = list(app.screen.query(HintLabel))
        assert len(labels) == 27
        assert all(label.display and len(label.text) == 2 for label in labels)
        assert screen_rows(app)[0] == before
        await pilot.press(*labels[-1].text)
        await pilot.pause()
        assert app.picked == 26
        assert not app.screen.query(HintSession)


async def test_hints_preserve_wide_combining_text_and_escape():
    app = ReadableHintsApp()
    async with app.run_test(size=(70, 35)) as pilot:
        first = app.query_one("#target-0", Static)
        first.update("[@click=app.pick(0)]界e\u0301 Target 00[/]")
        await pilot.pause()
        before = screen_rows(app)[0]
        original_focus = app.screen.focused
        await app.screen.action_show_hints()
        await pilot.pause()
        assert screen_rows(app)[0][:12] == before[:12]
        await pilot.press("escape")
        await pilot.pause()
        assert not app.screen.query(HintSession)
        assert app.screen.focused is original_focus
        assert app.picked is None


class PublishedHintScreen(Screen):
    def __init__(self):
        super().__init__()
        self.frames: list[tuple[str, ...]] = []

    def _on_frame_published(self) -> None:
        # Observe admission before HintHost's later reconciliation can move paint.
        self.frames.append(tuple(strip.text for strip in self._compositor.render_published_strips()))
        super()._on_frame_published()


class ChangingHintsApp(ReadableHintsApp):
    def get_default_screen(self) -> Screen:
        return PublishedHintScreen()


async def test_new_body_glyphs_are_clear_in_every_published_hint_frame():
    app = ChangingHintsApp()
    async with app.run_test(size=(70, 35)) as pilot:
        await pilot.pause()
        await app.screen.action_show_hints()
        await pilot.pause()
        screen = app.screen
        assert isinstance(screen, PublishedHintScreen)
        screen.frames.clear()
        expanded = "Expanded target zero label"
        app.query_one("#target-0", Static).update(
            f"[@click=app.pick(0)]{expanded}[/]")
        await pilot.pause()
        changed_rows = [frame[0] for frame in screen.frames if frame[0].startswith("Expanded")]
        assert changed_rows
        assert all(row.startswith(expanded) for row in changed_rows), changed_rows
