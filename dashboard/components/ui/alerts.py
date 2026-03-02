import reflex as rx
from .tokens import TEXT_SIZE

def info(text: str) -> rx.Component:
    return rx.callout(rx.text(text, size=TEXT_SIZE), icon="info", color_scheme="gray", variant="surface")

def error(text: str) -> rx.Component:
    return rx.callout(rx.text(text, size=TEXT_SIZE), icon="triangle_alert", color_scheme="red", variant="surface")

def success(text: str) -> rx.Component:
    return rx.callout(rx.text(text, size=TEXT_SIZE), icon="check", color_scheme="grass", variant="surface")
