import reflex as rx

def tabs_3(*, value, on_change, config: rx.Component, state: rx.Component, control: rx.Component) -> rx.Component:
    """
    3-tab pattern with consistent sizing.
    Keyboard navigation is handled by the tabs component itself.
    """
    return rx.tabs.root(
        rx.tabs.list(
            rx.tabs.trigger("Config", value="config", flex="1", text_align="center"),
            rx.tabs.trigger("State", value="state", flex="1", text_align="center"),
            rx.tabs.trigger("Control", value="control", flex="1", text_align="center"),
            width="100%",
        ),
        rx.tabs.content(config, value="config"),
        rx.tabs.content(state, value="state"),
        rx.tabs.content(control, value="control"),
        value=value,
        on_change=on_change,
        width="100%",
    )
