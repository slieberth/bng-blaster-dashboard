import reflex as rx


class MonacoEditor(rx.Component):
    """Wrapper for @monaco-editor/react"""

    library = "@monaco-editor/react"
    tag = "Editor"
    is_default = True  # Editor is default export in @monaco-editor/react

    # The NPM package Reflex should install.
    lib_dependencies: list[str] = ["@monaco-editor/react"]

    # Props
    value: rx.Var[str]
    language: rx.Var[str] = "yaml"
    theme: rx.Var[str] = "vs-dark"
    height: rx.Var[str] = "500px"
    width: rx.Var[str] = "100%"

    # IMPORTANT: options must be a dict-like prop; keep it Any.
    options: rx.Var[dict] = {}

    def get_event_triggers(self) -> dict[str, callable]:
        # onChange(value, event) in Monaco -> we only want value
        return {"on_change": lambda value, event=None: [value]}
    
    # Example usage with JSON validation:
    # https://codesandbox.io/p/sandbox/monaco-editor-json-validation-example-gue0q?file=%2Fsrc%2FApp.js%3A17%2C22

    # Example usage with YAML validation:
    # https://monaco-yaml.js.org/
