from __future__ import annotations

import re
from typing import Iterable

from rich.cells import get_character_cell_size

from textual._cells import cell_len
from textual._loop import loop_last
from textual.expand_tabs import get_tab_widths

re_chunk = re.compile(r"\S+\s*|\s+")


def chunks(text: str) -> Iterable[tuple[int, int, str]]:
    """Yields each "chunk" from the text as a tuple containing (start_index, end_index, chunk_content).
    A "chunk" in this context refers to a word and any whitespace around it.

    Args:
        text: The text to split into chunks.

    Returns:
        Yields tuples containing the start, end and content for each chunk.
    """
    end = 0
    while (chunk_match := re_chunk.match(text, end)) is not None:
        start, end = chunk_match.span()
        chunk = chunk_match.group(0)
        yield start, end, chunk


class WrapOffset(int):
    """A codepoint break with the cell position computed by that same wrap."""

    _cell_offset: int

    def __new__(cls, column: int, cell_offset: int) -> WrapOffset:
        offset = super().__new__(cls, column)
        offset._cell_offset = cell_offset
        return offset

    @property
    def cell_offset(self) -> int:
        return self._cell_offset


def compute_wrap_offsets(
    text: str,
    width: int,
    tab_size: int,
    fold: bool = True,
    precomputed_tab_sections: list[tuple[str, int]] | None = None,
) -> list[WrapOffset]:
    """Given a string of text, and a width (measured in cells), return a list
    of codepoint indices which the string should be split at in order for it to fit
    within the given width.

    Args:
        text: The text to examine.
        width: The available cell width.
        tab_size: The tab stop width.
        fold: If True, words longer than `width` will be folded onto a new line.
        precomputed_tab_sections: The output of `get_tab_widths` can be passed here directly,
            to prevent us from having to recompute the value.

    Returns:
        A list of indices to break the line at.
    """
    tab_size = min(tab_size, width)
    if precomputed_tab_sections:
        tab_sections = precomputed_tab_sections
    else:
        tab_sections = get_tab_widths(text, tab_size)

    break_positions: list[WrapOffset] = []
    append = break_positions.append
    cell_offset = 0
    consumed_cells = 0
    _cell_len = cell_len

    cumulative_width = 0
    cumulative_widths: list[int] = []  # prefix sum of tab widths for each codepoint
    record_widths = cumulative_widths.extend

    for last, (tab_section, tab_width) in loop_last(tab_sections):
        # add 1 since the \t character is stripped by get_tab_widths
        section_codepoint_length = len(tab_section) + int(bool(tab_width))
        widths = [cumulative_width] * section_codepoint_length
        record_widths(widths)
        cumulative_width += tab_width
        if last:
            cumulative_widths.append(cumulative_width)

    for start, end, chunk in chunks(text):
        chunk_width = _cell_len(chunk)  # this cell len excludes tabs completely
        tab_width_before_start = cumulative_widths[start]
        tab_width_before_end = cumulative_widths[end]
        chunk_tab_width = tab_width_before_end - tab_width_before_start
        chunk_width += chunk_tab_width
        remaining_space = width - cell_offset
        chunk_fits = remaining_space >= chunk_width

        if chunk_fits:
            # Simplest case - the word fits within the remaining width for this line.
            cell_offset += chunk_width
        else:
            # Not enough space remaining for this word on the current line.
            if chunk_width > width:
                # The word doesn't fit on any line, so we must fold it
                if fold:
                    _get_character_cell_size = get_character_cell_size
                    if start:
                        append(WrapOffset(start, consumed_cells))
                    total_width = 0
                    absolute_cells = consumed_cells
                    for column, character in enumerate(chunk, start):
                        if character == "\t":
                            cell_width = cumulative_widths[column + 1] - cumulative_widths[column]
                        else:
                            cell_width = _get_character_cell_size(character)
                        if total_width and total_width + cell_width > width:
                            append(WrapOffset(column, absolute_cells))
                            total_width = 0
                        total_width += cell_width
                        absolute_cells += cell_width
                    cell_offset = total_width
                else:
                    # Folding isn't allowed, so crop the word.
                    if start:
                        append(WrapOffset(start, consumed_cells))
                    cell_offset = chunk_width
            elif cell_offset and start:
                # The word doesn't fit within the remaining space on the current
                # line, but it *can* fit on to the next (empty) line.
                append(WrapOffset(start, consumed_cells))
                cell_offset = chunk_width
        consumed_cells += chunk_width

    return break_positions
