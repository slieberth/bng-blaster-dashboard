import reflex as rx
from reflex.constants import LogLevel

config = rx.Config(
    app_name="dashboard",

    loglevel=LogLevel.INFO,
    
    # Frontend
    frontend_port=5712,

    # DEV: allowed origins for Websocket/Eventing
    cors_allowed_origins=["*"],
    # cors_allowed_origins=[
    #     "http://localhost:5712",
    #     "http://127.0.0.1:5712",
    # ],


    backend_host="127.0.0.1",
    frontend_host="0.0.0.0",

    backend_port=5713,

    # temp
    api_url="http://127.0.0.1:5713",

    disable_plugins=[
        "reflex.plugins.sitemap.SitemapPlugin",
    ],
)
