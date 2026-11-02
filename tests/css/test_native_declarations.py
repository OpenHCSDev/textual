import pytest

from textual.css.native import Keyword, NativeDeclaration, Percent, TextVariable, Variable
from textual.css.styles import Styles
from textual.css.stylesheet import Stylesheet
from textual.css.tokenizer import TokenError


@pytest.mark.parametrize("reference", (Variable("ink"), TextVariable("warning")))
@pytest.mark.parametrize("expression", ("#4488aa", "auto 75%", "red 50%", "$secondary", "ansi_yellow"))
def test_native_theme_colour_uses_the_css_value_owner(expression: str, reference: Variable) -> None:
    stylesheet = Stylesheet(variables={"ink": expression, "text-warning": expression, "secondary": "#aa8844"})
    stylesheet.add_source(f"Widget {{ color: {reference.text()}; }}")
    stylesheet.parse()

    native = stylesheet.native_styles(NativeDeclaration.of(Styles.color, reference))

    assert native.get_rules() == stylesheet.rules[0].styles.get_rules()


def test_native_border_keeps_the_property_alpha_rule() -> None:
    stylesheet = Stylesheet(variables={"primary": "#4488aa"})
    stylesheet.add_source("Widget { border: thick $primary 20%; }")
    stylesheet.parse()

    native = stylesheet.native_styles(
        NativeDeclaration.of(Styles.border, Keyword("thick"), Variable("primary"), Percent(20))
    )

    assert native.get_rules() == stylesheet.rules[0].styles.get_rules()
    assert native.border_top[1].a == 0.2


@pytest.mark.parametrize("aliases", ({"ink": "$ink"}, {"ink": "$other", "other": "$ink"}))
def test_circular_theme_variables_fail_at_the_shared_substitution_owner(aliases: dict[str, str]) -> None:
    stylesheet = Stylesheet(variables=aliases)

    with pytest.raises(TokenError):
        stylesheet.native_styles(NativeDeclaration.of(Styles.color, Variable("ink")))

    stylesheet.add_source("Widget { color: $ink; }")
    with pytest.raises(TokenError):
        stylesheet.parse()
