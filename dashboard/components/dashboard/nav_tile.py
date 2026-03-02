import reflex as rx


def nav_tile(
    title: str,
    description: str,
    href: str,
    icon: rx.Component,
) -> rx.Component:
    """Navigation tile component used on the landing page."""
    return rx.link(
        rx.card(
            rx.hstack(
                rx.center(
                    rx.box(
                        icon,
                        font_size="1.8rem",
                        line_height="1",
                    ),
                    width="56px",
                    height="56px",
                    border_radius="9999px",
                    background="rgba(0,0,0,0.03)",
                ),
                rx.vstack(
                    rx.heading(title, size="5"),
                    rx.text(description, color_scheme="gray"),
                    spacing="1",
                    align_items="start",
                    width="100%",
                ),
                spacing="4",
                align_items="center",
                width="100%",
            ),
            width="100%",
            height="120px",          # uniform tile height
            padding="1.25rem",
            variant="surface",
        ),
        href=href,
        underline="none",            # valid values: auto|hover|always|none
        width="100%",
    )
