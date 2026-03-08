import reflex as rx
import logging

from dashboard.state.auth import AuthState
from dashboard.state.instance_dashboard import InstanceDashboard

from dashboard.components.ui.button import ui_button
from dashboard.components.dashboard.layout import page_layout
from dashboard.components.dashboard.header import dashboard_header

logger = logging.getLogger("dashboard.pages.instance_dashboard")


@rx.page(
    route="/instance_dashboard",
    title="Instance Dashboard",
    on_load=InstanceDashboard.background_refresh,
)
def instance_dashboard() -> rx.Component:
    return rx.box(
        page_layout(
            dashboard_header(
                breadcrumbs_items=[
                    rx.link("Home", href="/", size="3"),
                    rx.text(
                        InstanceDashboard.instance_name,
                        size="3",
                        color=rx.color("gray", 12),
                        weight="bold",
                    ),
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
            rx.tabs.root(
                rx.tabs.list(
                    rx.tabs.trigger("Session Counters", value="counters", flex="1", text_align="center"),
                    rx.tabs.trigger("Session Info", value="session_info", flex="1", text_align="center"),
                    rx.tabs.trigger("Logs", value="logs", flex="1", text_align="center"),
                    width="100%",
                ),
                rx.tabs.content(_counters_view(), value="counters"),
                rx.tabs.content(_session_info_view(), value="session_info"),
                rx.tabs.content(_logs_view(), value="logs"),
                value=InstanceDashboard.active_tab,
                on_change=InstanceDashboard.set_active_tab,
                width="100%",
            ),
            size="4",
            max_width="1600px",
        )
    )


def _counters_view() -> rx.Component:
    return rx.box(
        rx.vstack(
            rx.hstack(
                rx.heading("Session Counters", size="6"),
                rx.spacer(),
                rx.text(InstanceDashboard.session_counters_status, color=rx.color("gray", 11)),
                ui_button(
                    "Refresh",
                    icon="refresh-cw",
                    on_click=InstanceDashboard.refresh_session_counters,
                    size="1",
                ),
                width="100%",
                align="center",
            ),
            rx.cond(
                InstanceDashboard.session_counters_is_not_running,
                rx.callout(
                    "Not running",
                    icon="info",
                    color_scheme="gray",
                    variant="surface",
                ),
                rx.table.root(
                    rx.table.header(
                        rx.table.row(
                            rx.table.column_header_cell("Key"),
                            rx.table.column_header_cell("Value"),
                        )
                    ),
                    rx.table.body(
                        rx.foreach(
                            InstanceDashboard.session_counters_items,
                            lambda kv: rx.table.row(
                                rx.table.cell(rx.text(kv[0])),
                                rx.table.cell(rx.text(kv[1])),
                            ),
                        )
                    ),
                    variant="surface",
                    width="100%",
                    table_layout="fixed",
                ),
            ),
            spacing="3",
            width="100%",
        ),
        padding="4",
        width="100%",
    )


def _session_info_view() -> rx.Component:
    return rx.box(
        rx.vstack(
            rx.hstack(
                rx.heading("Session Info", size="6"),
                rx.spacer(),
                rx.text(InstanceDashboard.session_info_status, color=rx.color("gray", 11)),
                ui_button(
                    "Refresh view",
                    icon="refresh-cw",
                    on_click=InstanceDashboard.refresh_session_infos,
                    size="1",
                ),
                width="100%",
                align="center",
            ),
            rx.hstack(
                rx.text("Filtered:", color=rx.color("gray", 11)),
                rx.text(InstanceDashboard.session_info_filtered_count, color=rx.color("gray", 11)),
                rx.spacer(),
                rx.input(
                    placeholder="Search…",
                    value=InstanceDashboard.session_info_search,
                    on_change=InstanceDashboard.set_session_info_search,
                    width="320px",
                ),
                rx.select(
                    ["all", "pppoe", "ipoe", "dhcp", "dhcpv6"],
                    value=InstanceDashboard.session_info_filter_type,
                    on_change=InstanceDashboard.set_session_info_filter_type,
                    width="180px",
                ),
                rx.select(
                    ["all", "established", "terminated", "idle"],
                    value=InstanceDashboard.session_info_filter_state,
                    on_change=InstanceDashboard.set_session_info_filter_state,
                    width="180px",
                ),
                ui_button(
                    "Clear",
                    on_click=InstanceDashboard.clear_session_info_filters,
                    size="1",
                ),
                width="100%",
                align="center",
            ),
            rx.hstack(
                rx.hstack(
                    ui_button("First", on_click=InstanceDashboard.session_info_first, size="1"),
                    ui_button("Prev", on_click=InstanceDashboard.session_info_prev, size="1"),
                    ui_button("Next", on_click=InstanceDashboard.session_info_next, size="1"),
                    spacing="2",
                ),
                rx.spacer(),
                rx.text("Rows", color=rx.color("gray", 11)),
                rx.select(
                    ["5", "10", "20", "30"],
                    value=InstanceDashboard.session_info_page_size_str,
                    on_change=InstanceDashboard.session_info_set_page_size,
                    width="120px",
                ),
                width="100%",
                align="center",
            ),
            rx.cond(
                InstanceDashboard.session_info_is_not_running,
                rx.callout(
                    "Not running",
                    icon="info",
                    color_scheme="gray",
                    variant="surface",
                ),
                rx.cond(
                    InstanceDashboard.session_info_has_rows,
                    rx.box(
                        rx.table.root(
                            rx.table.header(
                                rx.table.row(
                                    rx.foreach(
                                        InstanceDashboard.session_info_columns,
                                        lambda c: rx.table.column_header_cell(c),
                                    )
                                )
                            ),
                            rx.table.body(
                                rx.foreach(
                                    InstanceDashboard.session_info_table_rows,
                                    lambda row: rx.table.row(
                                        rx.foreach(
                                            InstanceDashboard.session_info_columns,
                                            lambda col: rx.table.cell(
                                                rx.text(
                                                    row[col],
                                                    title=row[col],
                                                ),
                                                style={
                                                    "whiteSpace": "nowrap",
                                                    "overflow": "hidden",
                                                    "textOverflow": "ellipsis",
                                                    "maxWidth": "220px",
                                                },
                                            ),
                                        ),
                                    ),
                                )
                            ),
                            variant="surface",
                            width="100%",
                            table_layout="auto",
                        ),
                        overflow_x="auto",
                        width="100%",
                    ),
                    rx.text(
                        "No session info available.",
                        color=rx.color("gray", 11),
                    ),
                ),
            ),
            spacing="3",
            width="100%",
        ),
        padding="4",
        width="100%",
    )


def _logs_view() -> rx.Component:
    return rx.box(
        rx.callout(
            "Log view is not connected yet.",
            icon="info",
            color_scheme="gray",
            variant="surface",
        ),
        padding="4",
        width="100%",
    )