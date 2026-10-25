from itertools import combinations

from textual.app import App, ComposeResult
from textual.widgets import Static
from textual.widgets._hints import HintLabel


class DenseLinksApp(App):
    """27 targets two cells apart, so two-letter labels would touch."""

    CSS = "Static { margin-top: 5; }"

    def compose(self) -> ComposeResult:
        yield Static(" ".join(f"[@click=app.notify('{index}')]x[/]" for index in range(27)))


async def test_hint_labels_are_separated():
    app = DenseLinksApp()
    async with app.run_test(size=(80, 24)) as pilot:
        await pilot.pause()
        await app.screen.action_show_hints()
        await pilot.pause()
        regions = [label.region for label in app.screen.query_children(HintLabel)]
        assert len(regions) == 27
        for first, second in combinations(regions, 2):
            assert first.y != second.y or first.right < second.x or second.right < first.x, (first, second)
