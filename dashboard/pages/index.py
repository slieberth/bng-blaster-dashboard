import reflex as rx
import logging

from dashboard.state.auth import AuthState
from dashboard.components.ui.button import ui_button
from dashboard.components.dashboard.layout import page_layout
from dashboard.components.dashboard.header import dashboard_header
from dashboard.state.instances import InstancesState
from dashboard.models.bbl_models import InstanceModel

logger = logging.getLogger("dashboard.pages.index")


@rx.page(route="/", title="Dashboard", on_load=AuthState.require_login)
def index() -> rx.Component:
    return _dashboard()


def _dashboard() -> rx.Component:
    return page_layout(
        dashboard_header(
            breadcrumbs_items=[rx.link("Home", href="/", size="4")],
            actions=rx.hstack(
                ui_button("Logout", icon="log-out", on_click=AuthState.logout, size="1"),
            ),
        ),
        rx.box(
            main_table(),
            width="100%",
            overflow_x="auto",
        ),
        size="4",
        max_width="1600px",
        # initial load + start periodic refresh
        on_mount=[InstancesState.fetch_instances, InstancesState.start_refresh_loop],
        on_unmount=InstancesState.stop_refresh_loop,
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
    return rx.table.root(
        rx.table.header(
            rx.table.row(
                _header_cell("Instance", "route"),
                _header_cell("Status", "activity"),
                _header_cell("Action", "cog"),
            )
        ),
        rx.table.body(
            rx.foreach(
                InstancesState.items,
                lambda item, index: _show_item(item, index),
            )
        ),
        variant="surface",
        size="3",
        width="100%",
    )


def _show_item(item: InstanceModel, index: int) -> rx.Component:
    bg_color = rx.cond(index % 2 == 0, rx.color("gray", 1), rx.color("accent", 2))
    hover_color = rx.cond(index % 2 == 0, rx.color("gray", 3), rx.color("accent", 3))

    return rx.table.row(
        rx.table.row_header_cell(item.name),
        rx.table.cell(item.status),
        rx.table.cell(
            rx.hstack(
                rx.tooltip(
                    ui_button(
                        "Inspect",
                        icon="info",
                        on_click=lambda: rx.redirect(f"/instance-dashboard/{item.name}"),
                        size="1",
                    ),
                    content="Inspect Instance",
                ),
                ui_button(
                    "Start",
                    icon="play",
                    on_click=lambda: InstancesState.start_instance(item.name),
                    disabled=item.status == "started",
                    color_scheme="grass",
                    size="1",
                ),
                ui_button(
                    "Stop",
                    icon="square",
                    on_click=lambda: InstancesState.stop_instance(item.name),
                    disabled=item.status != "started",
                    color_scheme="orange",
                    size="1",
                ),
                rx.spacer(),
                spacing="2",
                width="100%",
                align="center",
            )
        ),
        style={"bg": bg_color, "_hover": {"bg": hover_color}},
        align="center",
        key=item.name,
    )