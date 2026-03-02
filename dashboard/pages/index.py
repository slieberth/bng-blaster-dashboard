import reflex as rx
import logging
import inspect
from dashboard.state.auth import AuthState
from dashboard.components.ui.button import ui_button
from dashboard.components.ui.alerts import info
from dashboard.components.dashboard.layout import app_layout
from dashboard.components.dashboard.header import dashboard_header
from dashboard.components.tools.monaco_editor import MonacoEditor
from dashboard.state.instances import InstancesState
from dashboard.models.bbl_models import InstanceModel

logger = logging.getLogger("dashboard.pages.index")
logging.basicConfig(level=logging.INFO)

@rx.page(route="/", title="Dashboard", on_load=AuthState.require_login)
def index() -> rx.Component:
    return _dashboard()


def _dashboard() -> rx.Component:
    return app_layout(
        dashboard_header(
            breadcrumbs_items=[
                rx.link("Home", href="/", size="4"),
            ],
            # title=rx.hstack(
            #     rx.text("User:", color=rx.color("gray", 11), size="2"),
            #     rx.text(AuthState.username, weight="bold", size="2"),
            #     # rx.text("Role:", color=rx.color("gray", 11), size="2"),
            #     # rx.badge(AuthState.role, variant="soft"),
            #     rx.cond(AuthState.can_execute, ui_button("Execute Action", size="1")),
            #     rx.cond(AuthState.is_admin, ui_button("Admin Action", color_scheme="red", size="1")),
            #     spacing="2",
            # ),
            actions=rx.hstack(
                ui_button("Logout", icon="log-out", on_click=AuthState.logout, size="1"),
            )
        ),

        # rx.divider(),

        rx.box(
            main_table(),
            width="100%",
            overflow_x="auto",
        ),

    )

def _header_cell(text: str, icon: str) -> rx.Component:
    return rx.table.column_header_cell(
        rx.hstack(
            rx.icon(icon, size=18),
            rx.text(text),
            align="center",
            spacing="2",
        ),
    )


def main_table() -> rx.Component:
    return rx.box(
        rx.table.root(
            rx.table.header(
                rx.table.row(
                    _header_cell("Instance", "route"),
                    _header_cell("Status", "activity"),
                    _header_cell("Action", "cog"),
                ),
            ),
            rx.table.body(
                rx.foreach(
                    InstancesState.items,
                    lambda item, index: _show_item(item, index),
                )
            ),
            variant="surface",
            size="3",
            on_mount=InstancesState.fetch_instances,
            width="100%",
        ),
        width="100%",
    )

def _show_item(item: InstanceModel, index: int) -> rx.Component:
    bg_color = rx.cond(
        index % 2 == 0,
        rx.color("gray", 1),
        rx.color("accent", 2),
    )
    hover_color = rx.cond(
        index % 2 == 0,
        rx.color("gray", 3),
        rx.color("accent", 3),
    )

    return rx.table.row(
        rx.table.row_header_cell(item.name),
        rx.table.cell(item.status),
        rx.table.cell(
            rx.hstack(
                rx.tooltip(
                    rx.link(
                        ui_button("Inspect", icon="info", on_click=rx.redirect(f"/instance-dashboard/{item.name}"), size="1"),
                    ),
                    content="Inspect Instance",
                ),
                ui_button(
                    "Start",
                    icon="play", 
                    on_click=InstancesState.start_instance(item.name), 
                    disabled=item.status == "started",
                    color_scheme="grass",
                    size="1"),
                ui_button(
                    "Stop",
                    icon="square", 
                    on_click=InstancesState.stop_instance(item.name),
                    disabled=item.status != "started",
                    color_scheme="orange",
                    size="1"),
                rx.spacer(),
            ),
        ),
        style={"_hover": {"bg": hover_color}, "bg": bg_color},
        align="center",
    )
