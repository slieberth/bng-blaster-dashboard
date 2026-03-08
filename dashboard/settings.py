import os


BNG_CONTROLLER_BASE_URL = os.environ.get(
    "BNG_CONTROLLER_BASE_URL",
    "http://127.0.0.1:5711",
).rstrip("/")
