import reflex as rx
import logging

from dashboard.state.auth import AuthState
from dashboard.state.instance_dashboard import InstanceDashboard
from dashboard.models.bbl_models import InstanceMeta

from dashboard.components.ui.button import ui_button
from dashboard.components.dashboard.layout import page_layout
from dashboard.components.dashboard.header import dashboard_header

logger = logging.getLogger("dashboard.pages.instance_dashboard")

@rx.page(
    route="/instance_dashboard",
    title="Instance Dashboard",
    on_load=InstanceDashboard.on_load,
)

def instance_dashboard() -> rx.Component:
    return rx.box(
        page_layout(
            dashboard_header(
                breadcrumbs_items=[
                    rx.link("Home", href="/", size="2"),
                    rx.text(
                        InstanceDashboard.instance_name,
                        size="2",
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
            rx.vstack(
                rx.box(
                    main_table(),
                    width="100%",
                    overflow_x="auto",
                ),
                spacing="3",
                width="100%",
            ),
        )
    )

def main_table() -> rx.Component:
    return rx.table.root(
        rx.table.body(),
        variant="surface",
        size="3",
        width="100%",
    )
