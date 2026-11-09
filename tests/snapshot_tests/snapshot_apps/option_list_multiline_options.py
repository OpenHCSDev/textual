from __future__ import annotations


from textual.app import App, ComposeResult
from textual.widgets import OptionList, Header, Footer
from textual.widgets.option_list import Option
from textual.binding import MethodBinding


class OptionListApp(App[None]):

    def compose(self) -> ComposeResult:
        yield Header()
        yield OptionList(
            Option("1. Single line", id="one"),
            Option("2. Two\nlines", id="two"),
            Option("3. Three\nlines\nof text", id="three"),
        )

        yield Footer()

    @MethodBinding.declare("1")
    def key_1(self):
        self.query_one(OptionList).replace_option_prompt_at_index(0, "1. Another single line")

    @MethodBinding.declare("2")
    def key_2(self):
        self.query_one(OptionList).replace_option_prompt_at_index(0, "1. Two\nlines")

    @MethodBinding.declare("3")
    def key_3(self):
        self.query_one(OptionList).replace_option_prompt_at_index(1, "1. Three\nlines\nof text")


if __name__ == "__main__":
    OptionListApp().run()
