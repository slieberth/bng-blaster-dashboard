import reflex as rx
from .tokens import INPUT_SIZE

import reflex as rx
from .tokens import INPUT_SIZE

def ui_button(
    label: str | None = None,
    *,
    on_click=None,
    icon: str | None = None,
    aria_label: str | None = None,
    variant: str = "soft",
    color_scheme: str | None = None,
    size: str = INPUT_SIZE,
    disabled=None,
    width: str | None = None,
) -> rx.Component:
    a11y = aria_label or label or "Button"

    children = []
    if icon:
        children.append(rx.icon(icon))
    if label:
        children.append(rx.text(label, size="2"))

    return rx.button(
        *children,
        on_click=on_click,
        variant=variant,
        color_scheme=color_scheme,
        size=size,
        disabled=disabled,
        width=width,
        type="button",          # important in forms
        tab_index=0,            # ensure focusable
        aria_label=a11y,
        title=a11y,             # helpful for mouse/tooltip
    )