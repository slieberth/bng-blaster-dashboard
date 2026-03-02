import reflex as rx
import logging

from dashboard.state.auth import AuthState
from dashboard.components.ui.inputs import text_input, password_input
from dashboard.components.ui.button import ui_button
from dashboard.components.ui.form_field import form_field


@rx.page(route="/login", title="Login")
def login() -> rx.Component:
    user_id = "login-user"
    pw_id = "login-password"

    # we always provide both ids; it's fine if error is empty
    user_desc = f"{user_id}-help {user_id}-err"
    pw_desc = f"{pw_id}-help {pw_id}-err"


    return rx.center(
        rx.box(
            rx.vstack(
                rx.heading("BNG Blaster Dashboard", size="4"),
                rx.text("Please sign in", size="2", color=rx.color("gray", 11)),
                rx.text("Demo users: admin/admin, exec/exec, viewer/view", size="2", color=rx.color("gray", 11)),

                form_field(
                    field_id=user_id,
                    label="Username",
                    help_text="Demo users: admin, exec, viewer",
                    error_text="",  # keep per-field error empty for now
                    control=text_input(
                        input_id=user_id,
                        value=AuthState.login_user,
                        on_change=AuthState.set_user,
                        placeholder="Enter username",
                        width="100%",
                        aria_invalid=False,
                        aria_describedby=user_desc,
                    ),
                ),

                form_field(
                    field_id=pw_id,
                    label="Password",
                    help_text="Demo passwords: admin, exec, viewer",
                    error_text="",  # keep per-field error empty for now
                    control=password_input(
                        input_id=pw_id,
                        value=AuthState.login_password,
                        on_change=AuthState.set_password,
                        placeholder="Enter password",
                        width="100%",
                        aria_invalid=False,
                        aria_describedby=pw_desc,
                    ),
                ),
                ui_button("Login", icon="log-in", on_click=AuthState.login, width="100%"),
                rx.cond(
                    AuthState.error != "",
                    rx.text(AuthState.error, color=rx.color("red", 11), size="2"),
                ),
                spacing="3",
                width="360px",
            ),
            padding="6",
            border=f"1px solid {rx.color('gray', 4)}",
            border_radius="12px",
            width="420px",
        ),
        height="100vh",
    )