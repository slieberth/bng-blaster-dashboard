import reflex as rx


def app_layout(
    *children: rx.Component,
    size: str = "3",
    max_width: str | None = None,
    padding_y: str = "24px",
    padding_x: str = "24px",
) -> rx.Component:
    """Full-width app layout with padded content area."""

    inner = rx.vstack(
        *children,
        spacing="6",
        align_items="stretch",
        width="100%",
    )

    # Content wrapper: centering + max width + real padding via CSS
    content = rx.box(
        inner,
        width="100%",
        max_width=max_width or "100%",
        margin="0 auto" if max_width else None,
        style={
            "paddingLeft": padding_x,
            "paddingRight": padding_x,
            "paddingTop": padding_y,
            "paddingBottom": padding_y,
        },
    )

    # Outer wrapper: full viewport background, NO padding here
    return rx.box(
        content,
        width="100%",
        min_height="100vh",
        background=rx.color("gray", 1),
        color=rx.color("gray", 12),
        size=size,
    )


def page_layout(
    title: str,
    *children: rx.Component,
    size: str = "3",
    max_width: str | None = None,
) -> rx.Component:
    return app_layout(
        rx.heading(title, size="8"),
        rx.box(*children, width="100%"),
        size=size,
        max_width=max_width,
    )