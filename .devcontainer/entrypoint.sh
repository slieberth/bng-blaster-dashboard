#!/bin/bash
set -euo pipefail

echo "[entrypoint] starting redis-server..."

# Start Redis in the background
redis-server --daemonize yes

until redis-cli ping >/dev/null 2>&1; do
  echo "[entrypoint] waiting for redis..."
  sleep 0.5
done

echo "[entrypoint] redis is ready"

# ------------------------------------------------------------
# Create test veth interfaces (optional)
# ------------------------------------------------------------
if ip link add veth1.1 type veth peer name veth1.2 2>/dev/null; then
    ip link set veth1.1 up
    ip link set veth1.2 up
    echo "[entrypoint] veth interfaces ready"
else
    echo "[entrypoint] WARNING: cannot create veth interfaces (missing NET_ADMIN?)"
fi

# ------------------------------------------------------------
# Persistent bash history
# ------------------------------------------------------------
export HISTFILE=/commandhistory/.bash_history
export HISTSIZE=100000
export HISTFILESIZE=200000
shopt -s histappend
PROMPT_COMMAND="history -a; history -n"

# ------------------------------------------------------------
# Start bngblaster controller (port 5711)
# ------------------------------------------------------------
BNG_CTRL_BIN="/usr/local/bin/bngblasterctrl"
BNG_CTRL_PORT="5711"
BNG_CONTROLLER_BASE_URL="http://localhost:5711"
BNG_CTRL_LOGFILE="/tmp/bngblasterctrl.log"
BNG_CTRL_PID=""

if [ -x "$BNG_CTRL_BIN" ]; then
  echo "[entrypoint] Starting bngblaster controller on :${BNG_CTRL_PORT} ..."
  "$BNG_CTRL_BIN" -addr ":${BNG_CTRL_PORT}" >"$BNG_CTRL_LOGFILE" 2>&1 &
  BNG_CTRL_PID="$!"
else
  echo "[entrypoint] WARNING: bngblaster controller binary not found at $BNG_CTRL_BIN"
fi

# ------------------------------------------------------------
# Start Reflex WUI (dev mode)
#   Frontend: 5712
#   Backend : 5713
# ------------------------------------------------------------
# IMPORTANT:
# Set this to your new repo root in the container.
# Example path if your repo is named "bng-blaster-dashboard":
REFLEX_APP_DIR="/workspaces/bng-blaster-dashboard"

REFLEX_LOGFILE="/tmp/reflex.log"
REFLEX_PID=""

export REFLEX_FRONTEND_PORT="5712"
export REFLEX_BACKEND_PORT="5713"
export API_URL="http://127.0.0.1:${REFLEX_BACKEND_PORT}"  # optional

if command -v reflex >/dev/null 2>&1; then
  if [ -d "$REFLEX_APP_DIR" ]; then
    cd "$REFLEX_APP_DIR"

    # If rxconfig.py is missing, run reflex init once (non-interactive).
    if [ ! -f "rxconfig.py" ]; then
      echo "[entrypoint] rxconfig.py not found -> running 'reflex init' ..."
      reflex init -y >"$REFLEX_LOGFILE" 2>&1 || true
    fi

    echo "[entrypoint] Starting Reflex dev server (frontend:${REFLEX_FRONTEND_PORT} backend:${REFLEX_BACKEND_PORT}) ..."
    reflex run --env dev \
      --frontend-port "${REFLEX_FRONTEND_PORT}" \
      --backend-port "${REFLEX_BACKEND_PORT}" \
      >>"$REFLEX_LOGFILE" 2>&1 &
    REFLEX_PID="$!"
  else
    echo "[entrypoint] WARNING: Reflex app dir not found: $REFLEX_APP_DIR"
  fi
else
  echo "[entrypoint] WARNING: reflex not installed (pip install reflex)"
fi

# ------------------------------------------------------------
# Graceful shutdown
# ------------------------------------------------------------
term_handler() {
  echo "[entrypoint] Caught termination signal"

  if [ -n "${REFLEX_PID}" ] && kill -0 "${REFLEX_PID}" 2>/dev/null; then
    echo "[entrypoint] Stopping Reflex (PID ${REFLEX_PID})"
    kill "${REFLEX_PID}" || true
    wait "${REFLEX_PID}" || true
  fi

  if [ -n "${BNG_CTRL_PID}" ] && kill -0 "${BNG_CTRL_PID}" 2>/dev/null; then
    echo "[entrypoint] Stopping bngblaster controller (PID ${BNG_CTRL_PID})"
    kill "${BNG_CTRL_PID}" || true
    wait "${BNG_CTRL_PID}" || true
  fi

  exit 0
}

trap term_handler SIGTERM SIGINT

# ------------------------------------------------------------
# Keep container alive (and forward signals)
# ------------------------------------------------------------
sleep infinity &
wait $!