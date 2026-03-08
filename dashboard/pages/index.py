import reflex as rx
import logging

from dashboard.state.auth import AuthState
from dashboard.state.instances import InstancesState
from dashboard.models.reflex_models import InstanceRow

from dashboard.components.ui.button import ui_button
from dashboard.components.dashboard.layout import page_layout
from dashboard.components.dashboard.header import dashboard_header
from dashboard.components.tools.monaco_editor import MonacoEditor

logger = logging.getLogger("dashboard.pages.index")

@rx.page(route="/", title="Dashboard", on_load=InstancesState.update_dashboard)

def index() -> rx.Component:
    return _dashboard()


def _dashboard() -> rx.Component:
    return rx.box(
        page_layout(
            dashboard_header(
                breadcrumbs_items=[
                    rx.link("Home", href="/", size="2"),
                ],
                actions=rx.hstack(
                    ui_button(
                        "Logout",
                        icon="log-out",
                        on_click=AuthState.logout,
                        size="1",
                    ),
                    spacing="2",
                ),
            ),
            rx.vstack(
                rx.box(
                    main_table(),
                    width="100%",
                    overflow_x="auto",
                ),
                spacing="3",
                width="100%",
            ),

            # ----------------------------
            # Config dialog (editable, Monaco)
            # ----------------------------
            rx.dialog.root(
                rx.dialog.content(
                    rx.dialog.title("Instance Configuration (YAML)"),
                    rx.box(
                        MonacoEditor.create(
                            value=InstancesState.edited_config_yaml,
                            language="yaml",
                            theme="vs",
                            height="500px",
                            on_change=InstancesState.on_config_editor_change,
                            options={
                                "minimap": {"enabled": False},
                                "wordWrap": "on",
                                "fontSize": 13,
                            },
                        ),
                        padding="10px",
                        background_color=rx.color("gray", 2),
                        border_radius="md",
                    ),
                    rx.flex(
                        rx.text(
                            InstancesState.config_save_status,
                            font_size="12px",
                            color=rx.cond(
                                InstancesState.config_save_status.startswith("Save error"),
                                rx.color("red", 9),
                                rx.color("gray", 10),
                            ),
                        ),
                        rx.spacer(),
                        rx.button(
                            "Save",
                            on_click=InstancesState.save_config,
                            variant="solid",
                            disabled=~InstancesState.is_config_dirty,
                        ),
                        rx.button(
                            "Close",
                            on_click=InstancesState.close_config,
                            variant="soft",
                        ),
                        margin_top="4",
                        justify="end",
                        spacing="3",
                    ),
                    max_width="900px",
                ),
                open=InstancesState.is_config_open,
                on_open_change=InstancesState.close_config,
            ),

            size="4",
            max_width="1600px",

        ),
        on_mount=InstancesState.fetch_instances,
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
                _header_cell("Sessions", "users"),
                _header_cell("Streams", "git-branch"),
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
        width="100%",
    )


def _show_item(item: InstanceRow, index: int) -> rx.Component:
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
        rx.table.cell(item.session_text),
        rx.table.cell(item.streams_text),
        rx.table.cell(
            rx.hstack(
                rx.cond(
                    item.status == "started",
                    rx.tooltip(
                        rx.link(
                            ui_button(
                                "View",
                                icon="gauge",
                                disabled=item.status == "stopped",
                                size="1",
                            ),
                            # href=f"/instance_dashboard/{item.name}?instance_name={item.name}",
                            href=f"/instance_dashboard?instance_name={item.name}",
                        ),
                        content="Open instance dashboard",
                    ),                
                    ui_button(
                    "Edit",
                    icon="pencil",
                    on_click=lambda: InstancesState.edit_config(item.name),
                    disabled=item.status == "started",
                    size="1",
                    )
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
                spacing="2",
                align="center",
                width="100%",
            ),
        ),
        style={
            "bg": bg_color,
            "_hover": {"bg": hover_color},
        },
        align="center",
        key=item.name,
    )