import asyncio

from textual import errors
from textual._compositor import Compositor
from textual.app import App, ComposeResult
from textual.containers import VerticalScroll
from textual.screen import Screen
from textual.widgets import Static, TextArea


class ObservedCompositor(Compositor):
    """Observe real arrangement invocations without replacing their behavior."""

    def __init__(self):
        super().__init__()
        self.arrangements = []

    def _arrange_root(self, root, size, visible_only=True, retain_geometry=(), **kwargs):
        retained = tuple(retain_geometry)
        result = super()._arrange_root(
            root, size, visible_only=visible_only, retain_geometry=retained, **kwargs
        )
        self.arrangements.append((root, visible_only, retained, len(result[0])))
        return result


class ReaderScreen(Screen):
    CSS = "VerticalScroll { height: 1fr; } Static { height: 1; } TextArea { height: 3; }"

    def __init__(self):
        super().__init__()
        self._compositor = ObservedCompositor()

    def _use_viewport_layout(self):
        return True

    def compose(self) -> ComposeResult:
        with VerticalScroll(id="history"):
            for index in range(100):
                yield Static(f"Original row {index}", id=f"row-{index}")
            yield TextArea("original draft", id="editor")


class ReaderApp(App):
    def get_default_screen(self):
        return ReaderScreen()


async def test_real_undo_acquires_only_missing_editor_and_preserves_reader_paths():
    app = ReaderApp()

    async def drive(pilot):
        await pilot.pause()
        screen = app.screen
        history = screen.query_one("#history", VerticalScroll)
        editor = screen.query_one("#editor", TextArea)
        editor.focus(scroll_visible=False)
        await pilot.press("x")
        changed = editor.text
        assert changed != "original draft"
        history.scroll_to(y=0, immediate=True, animate=False)
        await pilot.pause()
        screen._refresh_layout(app.size, scroll=True)
        compositor = screen._compositor
        assert editor not in compositor._visible_map
        original_full = compositor._full_map
        earlier = compositor.find_widget(screen.query_one("#row-80"))
        assert editor not in compositor._visible_map
        compositor.arrangements.clear()

        # Hidden editors lose focus through original Hide handling. Invoke the
        # original Undo action on this retained editor, rather than send a key
        # to a different focused widget. The action executes its real watcher.
        editor.action_undo()
        assert editor.text == "original draft"
        assert compositor.arrangements
        assert all(visible for _, visible, _, _ in compositor.arrangements)
        assert any(editor in retained for _, _, retained, _ in compositor.arrangements)
        assert compositor._full_map is original_full
        # Reacquire both positions synchronously after any ordinary frame reflow.
        actual_editor = compositor.find_widget(editor)
        actual_earlier = compositor.find_widget(screen.query_one("#row-80"))
        assert actual_earlier == earlier
        assert actual_editor == compositor.full_map[editor]
        assert actual_earlier == compositor.full_map[screen.query_one("#row-80")]
        assert len(compositor.full_map) > max(n for _, visible, _, n in compositor.arrangements if visible)
        app.exit()

    await asyncio.wait_for(app.run_async(headless=True, size=(40, 8), auto_pilot=drive), 10)
    assert app._exception is None
    assert app._task is None


async def test_committed_full_scene_survives_completeness_invalidation():
    class FullScreen(ReaderScreen):
        def _use_viewport_layout(self):
            return False

    class FullApp(ReaderApp):
        def get_default_screen(self):
            return FullScreen()

    app = FullApp()

    async def drive(pilot):
        await pilot.pause()
        screen = app.screen
        compositor = screen._compositor
        editor = screen.query_one("#editor")
        original = compositor.find_widget(editor)
        compositor.arrangements.clear()
        # This original invalidation means completeness needs reacquisition,
        # not that the scene's already-published coordinates have been retired.
        compositor.update_widgets({Static("not in this scene")})
        assert compositor._full_map_invalidated
        assert compositor.find_widget(editor) is original
        assert list(compositor.published_geometry((editor,))) == [(editor, original)]
        assert not compositor.arrangements

        await editor.remove()
        try:
            compositor.find_widget(editor)
        except errors.NoWidget:
            pass
        else:
            raise AssertionError("Retired editor geometry survived removal")
        app.exit()

    await asyncio.wait_for(app.run_async(headless=True, size=(40, 8), auto_pilot=drive), 10)
    assert app._exception is None
    assert app._task is None
