import reflex as rx
from .tokens import TEXT_SIZE

def simple_table(*, columns: list[str], rows, key_field: str | None = None) -> rx.Component:
    """
    Accessible table wrapper.
    - columns: list of column names
    - rows: iterable of dict-like (Var or dict)
    - key_field: optional stable key for rx.foreach rows
    """
    def cell(row, col: str) -> rx.Component:
        return rx.table.cell(rx.text(row.get(col, ""), size=TEXT_SIZE))

    return rx.table.root(
        rx.table.header(
            rx.table.row(*[rx.table.column_header_cell(rx.text(c, size=TEXT_SIZE)) for c in columns])
        ),
        rx.table.body(
            rx.foreach(
                rows,
                lambda row: rx.table.row(
                    *[cell(row, c) for c in columns],
                    key=(row.get(key_field, "").to_string() if key_field else None),
                ),
            )
        ),
        variant="surface",
        width="100%",
        table_layout="auto",
    )
