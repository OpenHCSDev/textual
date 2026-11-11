"""Hint badges stay on their original targets, including during frame changes."""

from textual.app import App, ComposeResult
from textual.containers import VerticalScroll
from textual.geometry import Offset, Region
from textual.screen import Screen
from textual.widgets import Static
from textual.widgets._hints import HintLabel, HintSession, LegendHintSession, SpatialHintSession


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


def displayed_region(label: HintLabel) -> Region:
    return label.screen._compositor.published_widgets[label][0]


async def test_two_letter_keys_are_on_their_targets_not_in_other_blank_cells():
    app = ReadableHintsApp()
    async with app.run_test(size=(70, 35)) as pilot:
        await pilot.pause()
        original = screen_rows(app)
        await app.screen.action_show_hints()
        await pilot.pause()
        session = app.screen.query_one(SpatialHintSession)
        assert session.region.size.area == 0
        assert len(session.labels) == 27
        for label in session.labels:
            assert len(label.text) == 2
            assert label.region.offset == label.target.region.offset
            assert label.region in app.screen.size.region
            row = label.region.y
            # Only the target's badge cells change; unrelated body text stays put.
            assert screen_rows(app)[row][label.region.right:] == original[row][label.region.right:]
        chosen = next(label for label in session.labels if label.target.widget.id == "target-13")
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


async def test_overlapping_two_letter_keys_keep_readable_entries_and_all_targets():
    app = DenseHintsApp()
    async with app.run_test(size=(54, 2)) as pilot:
        await pilot.pause()
        await app.screen.action_show_hints()
        await pilot.pause()
        session = app.screen.query_one(LegendHintSession)
        assert len(session.labels) == 27
        assert all(label.display and len(label.text) == 2 for label in session.labels)
        assert all(label.preview.text == "x" for label in session.labels)
        assert session.labels[0].region.intersection(app.screen.region)
        await pilot.press(*session.labels[-1].text)
        await pilot.pause()
        assert app.picked == 26
        assert not app.screen.query(HintSession)


async def test_wide_combining_target_text_returns_unchanged_after_escape():
    app = ReadableHintsApp()
    async with app.run_test(size=(70, 35)) as pilot:
        app.query_one("#target-0", Static).update("[@click=app.pick(0)]界e\u0301 Target 00[/]")
        await pilot.pause()
        original = screen_rows(app)
        focus = app.screen.focused
        await app.screen.action_show_hints()
        await pilot.pause()
        first = app.screen.query_one(SpatialHintSession).labels[0]
        assert "界e\u0301" in first.preview.text
        await pilot.press("escape")
        await pilot.pause()
        assert screen_rows(app) == original
        assert app.screen.focused is focus
        assert app.picked is None


class PublishedHintScreen(Screen):
    def __init__(self):
        super().__init__()
        self.anchors: list[tuple[tuple[Offset, Offset, str], ...]] = []

    def _on_frame_published(self) -> None:
        self.anchors.append(tuple(
            (displayed_region(label).offset, label.target.region.offset, label.text)
            for session in self.query(SpatialHintSession)
            for label in session.labels
            if label.target.available()
        ))
        super()._on_frame_published()


class MovingHintsApp(App):
    CSS = """
    #moving { position: absolute; width: 16; height: 1; offset: 4 3; }
    #fixed { position: absolute; width: 16; height: 1; offset: 4 8; }
    """
    picked: str | None = None

    def get_default_screen(self) -> Screen:
        return PublishedHintScreen()

    def compose(self):
        yield Static("[@click=app.pick('moving')]Moving item[/]", id="moving")
        yield Static("[@click=app.pick('fixed')]Fixed item[/]", id="fixed")

    def action_pick(self, value: str) -> None:
        self.picked = value


async def test_a_moving_item_keeps_its_key_and_anchor_in_each_published_frame():
    app = MovingHintsApp()
    async with app.run_test(size=(70, 20)) as pilot:
        await pilot.pause()
        await app.screen.action_show_hints()
        await pilot.pause()
        session = app.screen.query_one(SpatialHintSession)
        moving = app.query_one("#moving", Static)
        label = next(label for label in session.labels if label.target.widget is moving)
        identity, key = label.target.identity, label.text
        app.screen.anchors.clear()
        moving.styles.offset = (35, 5)
        await pilot.pause()
        assert app.screen.query_one(HintSession) is session
        assert label.target.identity == identity and label.text == key
        assert displayed_region(label).offset == label.target.region.offset == moving.region.offset
        assert app.screen.anchors
        assert all(actual == target for frame in app.screen.anchors for actual, target, _ in frame)
        await pilot.press(*key)
        await pilot.pause()
        assert app.picked == "moving"


async def test_resizing_reconciles_existing_badges_without_reopening_the_session():
    app = MovingHintsApp()
    async with app.run_test(size=(70, 20)) as pilot:
        await pilot.pause()
        await app.screen.action_show_hints()
        await pilot.pause()
        session = app.screen.query_one(SpatialHintSession)
        identities = tuple((label.target.identity, label.text) for label in session.labels)
        await pilot.resize_terminal(54, 16)
        await pilot.pause()
        assert app.screen.query_one(HintSession) is session
        assert tuple((label.target.identity, label.text) for label in session.labels) == identities
        assert all(displayed_region(label).offset == label.target.region.offset for label in session.labels)
        assert all(displayed_region(label) in app.screen.size.region for label in session.labels)
        await pilot.press("escape")


class ScrollingHintsApp(App):
    CSS = "VerticalScroll { height: 6; } Static { height: 1; }"
    picked: int | None = None

    def compose(self):
        with VerticalScroll():
            for index in range(20):
                yield Static(f"[@click=app.pick({index})]Item {index:02}[/]", id=f"item-{index}")

    def action_pick(self, value: int) -> None:
        self.picked = value


async def test_scrolling_keeps_a_visible_targets_key_attached_to_its_new_position():
    app = ScrollingHintsApp()
    async with app.run_test(size=(60, 14)) as pilot:
        await pilot.pause()
        await app.screen.action_show_hints()
        await pilot.pause()
        session = app.screen.query_one(SpatialHintSession)
        label = next(label for label in session.labels if label.target.widget.id == "item-3")
        key = label.text
        app.query_one(VerticalScroll).scroll_to(y=2, animate=False, immediate=True)
        await pilot.pause()
        assert app.screen.query_one(HintSession) is session
        assert label.text == key
        assert displayed_region(label).offset == label.target.region.offset
        assert label.target.region.y == 1
        await pilot.press(*key)
        await pilot.pause()
        assert app.picked == 3


class CrowdedHintsApp(DenseHintsApp):
    def compose(self):
        yield from super().compose()
        yield Static("b" * 54)
        yield Static("c" * 54)


async def test_crowded_list_browses_and_returns_the_original_body_on_cancel():
    app = CrowdedHintsApp()
    async with app.run_test(size=(54, 4)) as pilot:
        await pilot.pause()
        original = screen_rows(app)
        await app.screen.action_show_hints()
        await pilot.pause()
        session = app.screen.query_one(LegendHintSession)
        assert all(label.preview.text == "x" for label in session.labels)
        await pilot.press("down")
        await pilot.pause()
        assert session.scroll_y > 0
        await pilot.press("escape")
        await pilot.pause()
        assert screen_rows(app) == original
