import reflex as rx
from .tokens import INPUT_SIZE

def text_input(
    *,
    value,
    on_change,
    placeholder: str = "",
    width: str = "100%",
    input_id: str | None = None,
    aria_invalid=None,
    aria_describedby: str | None = None,
) -> rx.Component:
    return rx.input(
        id=input_id,
        value=value,
        on_change=on_change,
        placeholder=placeholder,
        size=INPUT_SIZE,
        width=width,
        aria_invalid=aria_invalid,
        aria_describedby=aria_describedby,
    )

def password_input(
    *,
    value,
    on_change,
    placeholder: str = "",
    width: str = "100%",
    input_id: str | None = None,
    aria_invalid=None,
    aria_describedby: str | None = None,
) -> rx.Component:
    return rx.input(
        id=input_id,
        type="password",
        value=value,
        on_change=on_change,
        placeholder=placeholder,
        size=INPUT_SIZE,
        width=width,
        aria_invalid=aria_invalid,
        aria_describedby=aria_describedby,
    )

def number_input(
    *,
    value,
    on_change,
    min: int | None = None,
    max: int | None = None,
    step: float | None = None,
    width: str = "100%",
    input_id: str | None = None,
    aria_invalid=None,
    aria_describedby: str | None = None,
) -> rx.Component:
    return rx.input(
        id=input_id,
        type="number",
        value=value,
        on_change=on_change,
        min=min,
        max=max,
        step=step,
        size=INPUT_SIZE,
        width=width,
        aria_invalid=aria_invalid,
        aria_describedby=aria_describedby,
    )