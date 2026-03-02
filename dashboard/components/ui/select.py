import reflex as rx
from .tokens import INPUT_SIZE

def ui_select(*, options: list[str], value, on_change, width: str = "100%") -> rx.Component:
    return rx.select(options, value=value, on_change=on_change, size=INPUT_SIZE, width=width)
