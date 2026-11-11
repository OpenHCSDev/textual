import pytest

from textual.app import App, ComposeResult
from textual.geometry import Region
from textual.widgets import Static, Input, TextArea, Checkbox, RadioButton, Switch, Collapsible, Select
from textual.widgets._collapsible import CollapsibleTitle
from textual.widgets._hints import HintClick, HintLabel, HintSession, SpatialHintSession


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
        regions = [Region(label.region.x, label.region.y, len(label.text), 1)
                   for label in app.screen.query(HintLabel)]
        assert len(regions) == 27
        ordered = sorted(regions, key=lambda region: (region.y, region.x))
        for first, second in zip(ordered, ordered[1:]):
            assert first.y != second.y or first.right < second.x, (first, second)


class NativeControlsApp(App):
    CSS = "TextArea { height: 4; } Input { height: 3; }"

    def compose(self):
        yield Input('search stays', id='search')
        yield TextArea('draft stays', id='draft')
        yield Checkbox('Filter', id='filter')
        yield RadioButton('Choice', id='choice')
        yield Switch(id='switch')
        with Collapsible(title='Group', collapsed=True):
            yield Static('Members')
        yield Select([('One', 1), ('Two', 2)], id='select')
        yield Static("[@click=app.notify('target')]Hint target[/]")


async def test_native_hints_focus_inputs_and_activate_control_owners():
    app = NativeControlsApp()
    async with app.run_test(size=(90, 40)) as pilot:
        await pilot.pause()

        async def choose(widget):
            await app.screen.action_show_hints()
            await pilot.pause()
            labels = [label for label in app.screen.query(HintLabel)
                      if label.target.widget is widget and label.display]
            assert len(labels) == 1, (widget, labels)
            await pilot.press(*labels[0].text)
            await pilot.pause()
            assert not app.screen.query_children(HintSession)

        search, draft = app.query_one(Input), app.query_one(TextArea)
        await choose(search)
        assert search.has_focus and search.value == 'search stays'
        await choose(draft)
        assert draft.has_focus and draft.text == 'draft stays'
        for widget in (app.query_one(Checkbox), app.query_one(RadioButton), app.query_one(Switch)):
            assert not widget.value
            await choose(widget)
            assert widget.value
            assert draft.has_focus and draft.text == 'draft stays'
        group = app.query_one(Collapsible)
        await choose(group.query_one(CollapsibleTitle))
        assert not group.collapsed
        await choose(group.query_one(CollapsibleTitle))
        assert group.collapsed
        select = app.query_one(Select)
        await choose(select)
        assert select.expanded
        await pilot.press('escape')


async def test_native_control_hint_preview_contains_its_label_not_only_its_marker():
    app = NativeControlsApp()
    async with app.run_test(size=(90, 40)) as pilot:
        await pilot.pause()
        checkbox = app.query_one(Checkbox)
        await app.screen.action_show_hints()
        await pilot.pause()
        previews = {label.target.widget: label.preview.text
                    for label in app.screen.query(HintLabel)}
        assert checkbox.label.plain in previews[checkbox]
        search = app.query_one(Input)
        assert search.value in previews[search]
        await pilot.press("escape")


@pytest.mark.parametrize("click", tuple(HintClick))
async def test_hint_input_keeps_original_focus_without_painting_a_status_row(click):
    app = NativeControlsApp()
    async with app.run_test(size=(90, 40)) as pilot:
        editor = app.query_one(TextArea)
        editor.focus()
        await pilot.pause()
        await app.screen._show_hints(click)
        await pilot.pause()
        session = app.screen.query_one(HintSession)
        assert session.original_focus is editor
        assert app.screen.focused is session
        assert session.region.size.area == 0
        assert isinstance(session, SpatialHintSession)
        assert all(label.region.offset == label.painted.preview_region.offset for label in session.labels)
        await pilot.press("escape")
        await pilot.pause()
        assert editor.has_focus
        assert not app.screen.query(HintSession)
