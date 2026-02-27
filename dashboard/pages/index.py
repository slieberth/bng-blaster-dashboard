import reflex as rx

@rx.page(route="/", title="Dashboard")
def index_page() -> rx.Component:
    return rx.center(
        rx.vstack(
            rx.heading("Dashboard", size="7"),
            rx.text("Reflex app skeleton is running.", color=rx.color("gray", 11)),
            spacing="3",
            padding="6",
        ),
        height="100vh",
    )
