"""Detached native preparation against the actual mounted Markdown owner."""

import asyncio
import pickle

import pytest

from textual.app import App, ComposeResult
from textual.containers import VerticalScroll
from textual.selection import Selection
from textual.widgets import Label, Markdown
from textual.widgets._markdown import MarkdownFence

SOURCE = """# Native document

This **strong** paragraph has [a native link](https://example.com), `code`, and 界.

> A quote with enough text to wrap when the acquired width changes.

- outer item
  - nested item
- second item

3. third
4. fourth

| left | right |
| --- | --- |
| [cell](https://example.org) | content |

```python
print('native fence')
```

---

Last paragraph.

## Repeated heading

First section.

## Repeated heading

Second section.

> ## Nested heading
>
> Nested headings do not appear in the top-level contents.
"""


class AcquiredMarkdown(Markdown):
    BLOCKS = Markdown.BLOCKS.copy()

    async def _parse_tokens(self, *args, **kwargs):
        tokens = await super()._parse_tokens(*args, **kwargs)
        self.acquired_tokens = tokens
        return tokens


class DocumentCodeLabel(Label):
    DEFAULT_CSS = "DocumentCodeLabel { color: magenta; padding: 1 2; }"


class DocumentFence(MarkdownFence):
    def compose(self) -> ComposeResult:
        yield self.code_label(self._highlighted_code, DocumentCodeLabel)

    @classmethod
    def document_node(cls, block):
        return block.fence_node(label_type=DocumentCodeLabel)

    @classmethod
    def document_declarations(cls):
        return cls, DocumentCodeLabel


AcquiredMarkdown.BLOCKS.update(fence=DocumentFence, code_block=DocumentFence)


def painted_characters(lines):
    """Compare actual paint and native metadata independent of segmentation."""
    return tuple(
        tuple(
            (
                character,
                str(segment.style),
                (
                    {
                        key: value
                        for key, value in segment.style.meta.items()
                        if key != "document_leaf"
                    }
                    if segment.style is not None
                    else {}
                ),
            )
            for segment in line
            for character in segment.text
        )
        for line in lines
    )


class DocumentApp(App):
    CSS = """
    VerticalScroll { scrollbar-size-vertical: 0; }
    Markdown { margin: 0; }
    """

    def compose(self) -> ComposeResult:
        with VerticalScroll():
            yield AcquiredMarkdown(SOURCE)


@pytest.mark.asyncio
async def test_native_document_rows_currentness_and_interactions(monkeypatch):
    monkeypatch.delenv("NO_COLOR", raising=False)
    app = DocumentApp()
    async with app.run_test(size=(54, 100)) as pilot:
        await pilot.pause()
        markdown = app.query_one(AcquiredMarkdown)
        document = markdown.acquire_document(SOURCE, markdown.acquired_tokens)
        paint = await asyncio.to_thread(document.prepare, markdown.region.width)
        size, mounted = app.screen._compositor.render_subtree_strips(
            markdown,
            app.screen._compositor.find_widget(markdown),
        )
        assert paint.size == size
        assert paint.gutter == markdown.styles.gutter
        assert paint.content_size == size.region.shrink(paint.gutter).size
        assert [(level, title) for level, title, _ in paint.table_of_contents] == [
            (level, title) for level, title, _ in markdown.table_of_contents
        ]
        assert all(heading.placement is not None for heading in paint.headings)
        assert paint.anchor_region("repeated-heading") is not None
        assert paint.anchor_region("repeated-heading-1") is not None
        assert paint.anchor_region("repeated-heading") != paint.anchor_region(
            "repeated-heading-1"
        )
        assert paint.anchor_region("nested-heading") is None
        assert tuple(line.text for line in paint.lines) == tuple(
            line.text for line in mounted
        )
        assert painted_characters(paint.lines) == painted_characters(mounted)
        assert paint.is_current(markdown, size.width)
        # Returned worker data retain this original acquisition identity.
        delivered = pickle.loads(pickle.dumps(paint))
        assert delivered.matches(document, size.width)
        assert delivered.table_of_contents == paint.table_of_contents
        assert not delivered.matches(
            markdown.acquire_document(SOURCE, markdown.acquired_tokens), size.width
        )
        assert any(
            "@click" in segment.style.meta
            for line in paint.lines
            for segment in line
            if segment.style is not None
        )
        assert any(leaf.selected_text(Selection(None, None)) for leaf in paint.leaves)
        assert any(leaf.declaration is DocumentCodeLabel for leaf in paint.leaves)
        link = next(
            (x, y)
            for y, line in enumerate(paint.lines)
            for x in range(line.cell_length)
            if "@click" in line.get_style_at(x).meta
        )
        leaf_index, offset = paint.get_leaf_and_offset_at(*link)
        assert leaf_index is not None and offset is not None
        assert paint.leaves[leaf_index].selected_text(Selection(None, None))
        assert any(
            block.source_text(document).startswith("# Native") for block in paint.blocks
        )
        markdown.styles.color = "red"
        assert not paint.is_current(markdown, size.width)
        refreshed = document.with_presentation(markdown)
        updated = await asyncio.to_thread(refreshed.prepare, size.width)
        assert updated.is_current(markdown, size.width)
        await pilot.resize_terminal(38, 100)
        await pilot.pause()
        current = document.with_presentation(markdown)
        assert not paint.matches(current, markdown.region.width)
        resized = await asyncio.to_thread(current.prepare, markdown.region.width)
        size, mounted = app.screen._compositor.render_subtree_strips(
            markdown,
            app.screen._compositor.find_widget(markdown),
        )
        assert resized.size == size
        assert tuple(line.text for line in resized.lines) == tuple(
            line.text for line in mounted
        )
        assert painted_characters(resized.lines) == painted_characters(mounted)
        assert resized.table_of_contents == paint.table_of_contents
