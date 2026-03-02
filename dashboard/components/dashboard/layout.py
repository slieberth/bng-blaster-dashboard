import reflex as rx


def app_layout(
    *children: rx.Component,
    size: str = "3", 
    max_width: str | None = None,
    padding_y: str = "6",
    padding_x: str = "6",
) -> rx.Component:
    """Base app layout wrapper used by all pages (full-width).

    NOTE:
    - We intentionally do NOT use rx.container here, so the app can use full viewport width.
    - 'size' and 'max_width' are kept to avoid breaking existing pages; max_width is optional.
    """
    # Optional: allow limiting width if caller explicitly sets max_width.
    content = rx.vstack(
        *children,
        spacing="6",
        align_items="stretch",
        width="100%",
        padding_x="6", 
        padding_y="6",
    )

    if max_width:
        # Keep content full-width container, but limit inner content if requested.
        content = rx.box(
            content,
            width="100%",
            max_width=max_width,
            margin="0 auto",
            padding_y=padding_y,
            padding_x=padding_x,
        )

    return rx.box(
        content,
        width="100%",
        min_height="100vh",
        background=rx.color("gray", 1),
        color=rx.color("gray", 12),
        padding_y=padding_y,
        padding_x=padding_x,
    )


def page_layout(
    title: str,
    *children: rx.Component,
    size: str = "3",                # <- stays compatible
    max_width: str | None = None,   # <- stays compatible
) -> rx.Component:
    """Standard page layout with a title + content section (full-width)."""
    return app_layout(
        rx.heading(title, size="8"),
        rx.box(*children, width="100%"),
        size=size,
        max_width=max_width,
        padding_x="6", 
        padding_y="6",
    )
