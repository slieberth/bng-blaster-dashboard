import reflex as rx


def breadcrumbs(items: list[rx.Component]) -> rx.Component:
    out: list[rx.Component] = []
    for i, comp in enumerate(items):
        out.append(comp)
        if i < len(items) - 1:
            out.append(rx.text("/", color=rx.color("gray", 9)))
    return rx.hstack(*out, spacing="2", align="center")


def dashboard_header(
    *,
    breadcrumbs_items: list[rx.Component],
    title: rx.Component | None = None,
    actions: rx.Component | None = None,
) -> rx.Component:
    return rx.vstack(
        rx.hstack(
            breadcrumbs(breadcrumbs_items),
            rx.spacer(),
            rx.box(actions) if actions is not None else rx.box(),
            width="100%",
            align="center",
        ),
        rx.box(title, width="100%") if title is not None else rx.box(),
        width="100%",
        spacing="3",
    )
