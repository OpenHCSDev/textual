from pathlib import Path

from textual.app import App, ComposeResult
from textual.widgets import DirectoryTree


class TreeApp(App[None]):
    def __init__(self, path: Path) -> None:
        super().__init__()
        self.path = path

    def compose(self) -> ComposeResult:
        yield DirectoryTree(self.path)


async def test_cursor_path_is_the_entry_under_the_cursor_or_the_root(tmp_path: Path):
    (tmp_path / "a.txt").write_text("a")
    app = TreeApp(tmp_path)
    async with app.run_test() as pilot:
        tree = app.query_one(DirectoryTree)
        await pilot.pause()
        tree.cursor_line = -1
        assert tree.cursor_path == tmp_path
        tree.cursor_line = 1
        await pilot.pause()
        assert tree.cursor_path == tmp_path / "a.txt"
