# wui/components/session_info_view.py
import reflex as rx
from wui.state.instance_dashboard import InstanceDashboard

_LABEL_SIZE = "2"
_HEADING_SIZE = "4"
_INPUT_SIZE = "2"


def _session_actions_cell(row) -> rx.Component:
    sid = row.get("session-id", "").to_string()
    state = row.get("session-state", "").to_string()

    is_pending = InstanceDashboard.session_action_pending_ids.contains(sid)
    is_established = state.lower().contains("established")

    start_or_stop = rx.cond(
        is_established,
        rx.button(
            "Stop",
            on_click=lambda: InstanceDashboard.session_stop(sid),
            color_scheme="orange",
            size=_INPUT_SIZE,
            disabled=is_pending,
            variant="soft",
        ),
        rx.button(
            "Start",
            on_click=lambda: InstanceDashboard.session_start(sid),
            color_scheme="grass",
            size=_INPUT_SIZE,
            disabled=is_pending,
            variant="soft",
        ),
    )
    return rx.hstack(start_or_stop, spacing="2")


def session_info_view() -> rx.Component:
    return rx.box(
        rx.vstack(
            # Header
            rx.hstack(
                rx.heading("Session Info", size=_HEADING_SIZE),
                rx.spacer(),
                rx.text(
                    InstanceDashboard.session_info_status,
                    color=rx.color("gray", 11),
                    size=_LABEL_SIZE,
                ),
                rx.button(
                    rx.icon("refresh_cw"),
                    rx.text("Refresh view", size=_LABEL_SIZE),
                    on_click=InstanceDashboard.refresh_session_infos,
                    variant="soft",
                    size=_INPUT_SIZE,
                ),
                width="100%",
                align="center",
            ),

            # Action status
            rx.cond(
                InstanceDashboard.session_action_status != "",
                rx.text(
                    InstanceDashboard.session_action_status,
                    color=rx.color("gray", 11),
                    size=_LABEL_SIZE,
                ),
            ),

            # Filters
            rx.hstack(
                rx.text(
                    InstanceDashboard.session_info_cache_status,
                    color=rx.color("gray", 11),
                    size=_LABEL_SIZE,
                ),
                rx.spacer(),
                rx.text("Filtered:", color=rx.color("gray", 11), size=_LABEL_SIZE),
                rx.text(
                    InstanceDashboard.session_info_filtered_count,
                    color=rx.color("gray", 11),
                    size=_LABEL_SIZE,
                ),
                rx.input(
                    placeholder="Search…",
                    value=InstanceDashboard.session_info_search,
                    on_change=[
                        InstanceDashboard.set_session_info_search,
                        InstanceDashboard.refresh_session_infos,
                    ],
                    width="260px",
                    size=_INPUT_SIZE,
                ),
                rx.select(
                    InstanceDashboard.session_info_type_options,
                    value=InstanceDashboard.session_info_filter_type,
                    on_change=[
                        InstanceDashboard.set_session_info_filter_type,
                        InstanceDashboard.refresh_session_infos,
                    ],
                    width="150px",
                    size=_INPUT_SIZE,
                ),
                rx.select(
                    InstanceDashboard.session_info_state_options,
                    value=InstanceDashboard.session_info_filter_state,
                    on_change=[
                        InstanceDashboard.set_session_info_filter_state,
                        InstanceDashboard.refresh_session_infos,
                    ],
                    width="150px",
                    size=_INPUT_SIZE,
                ),
                rx.button(
                    "Clear",
                    on_click=[
                        InstanceDashboard.clear_session_info_filters,
                        InstanceDashboard.refresh_session_infos,
                    ],
                    variant="soft",
                    size=_INPUT_SIZE,
                ),
                width="100%",
                align="center",
            ),

            # Paging
            rx.hstack(
                rx.hstack(
                    rx.button(
                        "First",
                        on_click=[
                            InstanceDashboard.session_info_first,
                            InstanceDashboard.refresh_session_infos,
                        ],
                        variant="soft",
                        size=_INPUT_SIZE,
                    ),
                    rx.button(
                        "Prev",
                        on_click=[
                            InstanceDashboard.session_info_prev,
                            InstanceDashboard.refresh_session_infos,
                        ],
                        variant="soft",
                        size=_INPUT_SIZE,
                    ),
                    rx.button(
                        "Next",
                        on_click=[
                            InstanceDashboard.session_info_next,
                            InstanceDashboard.refresh_session_infos,
                        ],
                        variant="soft",
                        size=_INPUT_SIZE,
                    ),
                    spacing="2",
                ),
                rx.spacer(),
                rx.text("Rows", color=rx.color("gray", 11), size=_LABEL_SIZE),
                rx.select(
                    ["5", "10", "20", "30"],
                    value=InstanceDashboard.session_info_page_size_str,
                    on_change=[
                        InstanceDashboard.session_info_set_page_size,
                        InstanceDashboard.refresh_session_infos,
                    ],
                    width="100px",
                    size=_INPUT_SIZE,
                ),
                width="100%",
                align="center",
            ),

            # Table
            rx.box(
                rx.cond(
                    InstanceDashboard.session_info_is_not_running,
                    rx.callout(
                        "Not running",
                        icon="info",
                        color_scheme="gray",
                        variant="surface",
                    ),
                    rx.cond(
                        ~InstanceDashboard.session_info_has_rows,
                        rx.text(
                            "No session info available.",
                            color=rx.color("gray", 11),
                            size=_LABEL_SIZE,
                        ),
                        rx.box(
                            rx.table.root(
                                rx.table.header(
                                    rx.table.row(
                                        rx.foreach(
                                            InstanceDashboard.session_info_columns,
                                            lambda c: rx.table.column_header_cell(
                                                rx.text(c, size=_LABEL_SIZE)
                                            ),
                                        ),
                                        rx.table.column_header_cell(
                                            rx.text("actions", size=_LABEL_SIZE)
                                        ),
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
                                                        size=_LABEL_SIZE,
                                                    ),
                                                    style={
                                                        "whiteSpace": "nowrap",
                                                        "overflow": "hidden",
                                                        "textOverflow": "ellipsis",
                                                        "maxWidth": "200px",
                                                    },
                                                ),
                                            ),
                                            rx.table.cell(_session_actions_cell(row)),
                                            key=row["session-id"],
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
                    ),
                ),
                rx.cond(
                    InstanceDashboard.session_info_loading
                    | InstanceDashboard.session_info_cache_loading,
                    rx.box(
                        rx.center(rx.spinner(), width="100%"),
                        position="absolute",
                        inset="0",
                        background_color=rx.color("gray", 1),
                        opacity="0.7",
                        border_radius="md",
                    ),
                ),
                position="relative",
                width="100%",
                min_height="220px",
            ),

            spacing="3",
            width="100%",
        ),
        padding="4",
        width="100%",
    )
