"""Keyboard-target admission is independent of an editor's cursor appearance."""

from textual.geometry import Region
from textual.widget import Widget


class EditableInput(Widget):
    """A focused editable control advertises its clipped input content."""

    def input_region(self, content_region: Region) -> Region:
        return content_region
