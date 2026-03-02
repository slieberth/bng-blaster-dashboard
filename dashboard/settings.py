import os

# Single source of truth for the BNG Blaster Controller base URL.
# Provided via environment variable in .devcontainer/entrypoint.sh:
#   export BNG_CONTROLLER_BASE_URL="http://localhost:5711"

BNG_CONTROLLER_BASE_URL = os.environ.get(
    "BNG_CONTROLLER_BASE_URL",
    "http://127.0.0.1:5711",
).rstrip("/")
