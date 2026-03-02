import reflex as rx


def form_field(
    *,
    field_id: str,
    label: str,
    control: rx.Component,
    help_text: str | rx.Var = "",
    error_text: str | rx.Var = "",
) -> rx.Component:
    """
    Var-safe accessible form field wrapper for Reflex.
    """
    help_id = f"{field_id}-help"
    err_id = f"{field_id}-err"

    return rx.vstack(
        rx.text(
            label,
            as_="label",
            html_for=field_id,
            size="2",
            color=rx.color("gray", 12),
            weight="medium",
        ),
        control,
        rx.cond(
            help_text != "",
            rx.text(help_text, id=help_id, size="1", color=rx.color("gray", 11)),
        ),
        rx.cond(
            error_text != "",
            rx.text(error_text, id=err_id, size="1", color=rx.color("red", 11)),
        ),
        spacing="1",
        width="100%",
    )
