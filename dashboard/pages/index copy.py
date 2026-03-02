# dashboard/pages/index.py
import reflex as rx

from dashboard.components.ui.form_field import form_field
from dashboard.components.ui.inputs import text_input
from dashboard.components.ui.button import ui_button
from dashboard.components.ui.alerts import info

class DemoState(rx.State):
    name: str = ""
    error: str = ""

    @rx.event
    def set_name(self, v: str):
        self.name = v

    @rx.event
    def submit(self):
        self.error = ""
        if not self.name.strip():
            self.error = "Name is required."
        else:
            self.error = ""

@rx.page(route="/", title="Dashboard")
def index() -> rx.Component:
    return rx.center(
        rx.vstack(
            rx.heading("BNG Blaster Dashboard", size="7"),
            info("This page uses A11y-first UI primitives (labelled fields, error linking, consistent controls)."),
            form_field(
                field_id="name",
                label="Name",
                control=text_input(value=DemoState.name, on_change=DemoState.set_name, placeholder="Type your name…"),
                help_text="This label is programmatically associated with the input.",
                error_text=DemoState.error,
            ),
            ui_button("Submit", icon="check", on_click=DemoState.submit, width="220px"),
            spacing="4",
            padding="6",
            width="520px",
        ),
        height="100vh",
    )