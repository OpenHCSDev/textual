"""Detached native preparation against the actual mounted Markdown owner."""

import asyncio


from textual.app import App, ComposeResult
from textual.containers import VerticalScroll
from textual.selection import SELECT_ALL
from textual.visual import Visual
from textual.widgets import Label, Markdown
from textual.widgets._markdown import MarkdownBlock, MarkdownFence

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


async def test_document_preparation_inputs_share_matches_without_participant_admission():
    from textual.document._paint import DocumentPaint

    markdown = AcquiredMarkdown("One original paragraph.")
    ancestor = VerticalScroll(markdown)
    app = App()
    async with app.run_test(size=(54, 20)) as pilot:
        await app.mount(ancestor)
        await pilot.pause()
        document = markdown.acquire_document(markdown.source, markdown.acquired_tokens)
        width = markdown.region.width
        paint = await asyncio.to_thread(document.prepare, width)
        original = DocumentPaint.preparation_inputs(document, width)
        assert paint.preparation_key == original
        assert paint.matches(document, width)

        # Genuine style writes change admission; restoring the original rule
        # absence restores answer inputs, not that publication lifetime.
        ancestor.styles.color = "red"
        ancestor.styles.clear_rule("color")
        await pilot.pause()
        rebound = document.with_presentation(markdown)
        assert document.presentation.admission != rebound.presentation.admission
        assert DocumentPaint.preparation_inputs(rebound, width) == original
        assert paint.matches(rebound, width)
        assert not paint.is_current(markdown, width)
        assert paint.with_presentation(rebound).is_current(markdown, width)

        independent = markdown.acquire_document(markdown.source, markdown.acquired_tokens)
        assert DocumentPaint.preparation_inputs(independent, width) != original
        assert not paint.matches(independent, width)
        assert not paint.matches(document, width + 1)

        assert paint.leaves
        for selected in (
            {"root_selection": SELECT_ALL},
            {"selections": {}},
            {"selections": {0: SELECT_ALL}},
            {"selection_style": Visual.selection_style(markdown)},
            {"selecting": True},
        ):
            assert DocumentPaint.preparation_inputs(document, width, **selected) != original
            assert not paint.matches(document, width, **selected)

        # Same acquired UUID with a genuinely changed grammar configuration
        # still refuses reuse. Effective style change independently refuses it.
        markdown.BULLETS = ("different native bullet",)
        changed = document.with_presentation(markdown)
        assert not document.same_source(changed)
        assert DocumentPaint.preparation_inputs(changed, width) != original
        assert not paint.matches(changed, width)
        ancestor.styles.color = "red"
        changed_style = rebound.with_presentation(markdown)
        assert changed_style.presentation.key != rebound.presentation.key
        assert DocumentPaint.preparation_inputs(changed_style, width) != original


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


class BoundSourceMarkdown(AcquiredMarkdown):
    """Observe actual scene suppliers without replacing native conversion."""

    live_inline_calls = 0
    live_fence_calls = 0

    def _get_token_content(self, token, *, block):
        self.live_inline_calls += 1
        return super()._get_token_content(token, block=block)

    def acquire_document_content(self):
        return MarkdownBlock._token_to_content

    def _get_prepared_fence(self, *args):
        self.live_fence_calls += 1
        return super()._get_prepared_fence(*args)


class BoundSourceApp(DocumentApp):
    def compose(self):
        with VerticalScroll():
            yield BoundSourceMarkdown(SOURCE)


class GrammarExtension(MarkdownBlock):
    def __init__(self, markdown, token, marker, *, source_block=None):
        self.marker = marker
        super().__init__(markdown, token, source_block=source_block)

    @classmethod
    def document_node(cls, block):
        cls._require_native_document(constructor=cls.__init__)
        return cls.native_document_node(block)


def acquired_grammar_extension(token, create):
    if token.type == "html_block":
        return create("html_block", token, "original-constructor-argument")
    return None


class ExtendedSourceMarkdown(AcquiredMarkdown):
    BLOCKS = {**AcquiredMarkdown.BLOCKS, "html_block": GrammarExtension}

    def unhandled_token(self, token):
        if token.type == "html_block":
            return GrammarExtension(self, token, "original-constructor-argument")
        return None

    def acquire_document_unhandled(self):
        return acquired_grammar_extension


class IndependentlyAcquiredMarkdown(AcquiredMarkdown):
    document = None

    def get_current_document(self):
        return self.document


class BeforeMountMarkdown(Markdown):
    async def _parse_tokens(self, parser, markdown, *, use_thread):
        tokens = await super()._parse_tokens(parser, markdown, use_thread=use_thread)
        assert not self.children
        self.host_pseudos = frozenset(self.get_pseudo_classes())
        self.document = self.acquire_document(markdown, tokens)
        self.document_paint = await asyncio.to_thread(
            self.document.prepare, self.region.width,
            root_selection=self.text_selection,
            selection_style=(Visual.selection_style(self) if self.text_selection is not None else None),
            selecting=self.screen._selecting,
        )
        return tokens


class BeforeMountApp(App):
    CSS = """
    VerticalScroll { scrollbar-size-vertical: 0; }
    BeforeMountMarkdown { margin: 0; background: cyan; padding: 0 2; }
    BeforeMountMarkdown:empty { background: red; padding: 1 3; }
    BeforeMountMarkdown:last-child { border-left: solid yellow; }
    """

    def compose(self) -> ComposeResult:
        with VerticalScroll():
            yield Label("Actual host sibling")
            yield BeforeMountMarkdown()


class EmptyDisplayApp(BeforeMountApp):
    CSS = (
        BeforeMountApp.CSS + "BeforeMountMarkdown MarkdownParagraph { display: none; }"
    )


class StreamBeforeMountApp(BeforeMountApp):
    CSS = BeforeMountApp.CSS + "VerticalScroll { layout: stream; }"


