#!/bin/bash
set -euo pipefail

# ==============================================================================
#  J.A.R.V.I.S Installer
#
#  Layout created by this script (JARVISH_HOME = ~/.jarvish):
#    ~/.jarvish/
#      app/       <- git checkout of this repository (source code only)
#      venv/      <- python virtual environment
#      config/    <- .env, credentials, antigravity-accounts.json
#      data/      <- sqlite db, session state
#      logs/      <- service logs
#      VERSION    <- currently installed git tag/commit (used by `jarvish update`)
#
#  Re-running this script is safe: it upgrades an existing install in place
#  instead of re-cloning or duplicating services.
# ==============================================================================

echo "=============================================="
echo "   J.A.R.V.I.S Installer                       "
echo "=============================================="
echo ""

# 1. Require Sudo
if [ "$EUID" -ne 0 ]; then
  echo "[INFO] This script requires root (sudo) privileges."
  if [ -f "$0" ]; then
      exec sudo bash "$0" "$@"
  else
      echo "[ERROR] Piped from curl without sudo. Run as: curl -sSL <URL> | sudo bash"
      exit 1
  fi
fi

if [ -n "${SUDO_USER:-}" ]; then
    REAL_USER="$SUDO_USER"
    REAL_HOME_DIR=$(getent passwd "$SUDO_USER" | cut -d: -f6)
else
    REAL_USER=$(whoami)
    REAL_HOME_DIR="$HOME"
fi

JARVISH_HOME="$REAL_HOME_DIR/.jarvish"
APP_DIR="$JARVISH_HOME/app"
VENV_DIR="$JARVISH_HOME/venv"
CONFIG_DIR="$JARVISH_HOME/config"
DATA_DIR="$JARVISH_HOME/data"
LOG_DIR="$JARVISH_HOME/logs"
REPO_URL="https://github.com/yayangkasep/jarvish.git"

run_as_user() { sudo -u "$REAL_USER" "$@"; }

echo "[INFO] Install root: $JARVISH_HOME"
run_as_user mkdir -p "$APP_DIR" "$CONFIG_DIR" "$DATA_DIR" "$LOG_DIR"
run_as_user touch "$LOG_DIR/jarvish.log" "$LOG_DIR/jarvish.error.log"

# 2. System dependencies
echo "[INFO] Checking required system packages..."
apt-get update -yqq >/dev/null 2>&1 || true
for pkg in python3 python3-pip git curl; do
    if ! command -v "$pkg" &>/dev/null; then
        echo "[INFO] Installing $pkg..."
        apt-get install -y "$pkg" >/dev/null 2>&1
    fi
done

# 3. Migrate old flat layout (git repo directly at ~/.jarvish) if present.
#    Config/data already live at the right place (paths.py always pointed at
#    ~/.jarvish/config and ~/.jarvish/data) — only the source checkout moves.
if [ ! -d "$APP_DIR/.git" ] && [ -d "$JARVISH_HOME/.git" ]; then
    echo "[INFO] Migrating existing install to the new app/ layout..."
    run_as_user mkdir -p "$APP_DIR"
    shopt -s dotglob
    for item in "$JARVISH_HOME"/*; do
        base=$(basename "$item")
        case "$base" in
            app|venv|config|data|logs|VERSION|.env|.|..) continue ;;
        esac
        run_as_user mv "$item" "$APP_DIR/"
    done
    shopt -u dotglob
    echo "[OK] Migration complete: source now lives in $APP_DIR"
fi

# 3b. Clone or update repository (idempotent)
if [ ! -d "$APP_DIR/.git" ]; then
    if [ -n "$(ls -A "$APP_DIR" 2>/dev/null)" ]; then
        echo "[WARNING] $APP_DIR exists and is not empty. Backing up..."
        mv "$APP_DIR" "${APP_DIR}_backup_$(date +%s)"
        run_as_user mkdir -p "$APP_DIR"
    fi
    echo "[INFO] Cloning repository into $APP_DIR..."
    run_as_user git clone "$REPO_URL" "$APP_DIR"
else
    echo "[INFO] Existing installation detected. Fetching latest code..."
    
    # Fix ownership of searxng in case docker changed it (preventing git reset failures)
    if [ -d "$APP_DIR/searxng" ]; then
        chown -R "$REAL_USER:$REAL_USER" "$APP_DIR/searxng" || true
    fi
    
    run_as_user git -C "$APP_DIR" fetch --tags origin
    run_as_user git -C "$APP_DIR" reset --hard origin/master
fi

# Record installed version (tag if present, else short commit hash)
INSTALLED_VERSION=$(run_as_user git -C "$APP_DIR" describe --tags --always)
echo "$INSTALLED_VERSION" | run_as_user tee "$JARVISH_HOME/VERSION" >/dev/null
echo "[INFO] Installed version: $INSTALLED_VERSION"

# 4. Install 'uv'
echo "[INFO] Ensuring 'uv' is installed..."
if ! run_as_user command -v uv &>/dev/null; then
    run_as_user curl -LsSf https://astral.sh/uv/install.sh | run_as_user sh
fi
UV_BIN="$REAL_HOME_DIR/.local/bin/uv"
[ -f "$UV_BIN" ] || UV_BIN="$REAL_HOME_DIR/.cargo/bin/uv"
[ -f "$UV_BIN" ] || UV_BIN=$(run_as_user which uv || true)
if [ -z "$UV_BIN" ] || [ ! -f "$UV_BIN" ]; then
    echo "[ERROR] uv installation failed."
    exit 1
fi

# 5. Virtual environment + package install (idempotent: reuses existing venv)
echo "[INFO] Setting up virtual environment at $VENV_DIR..."
if [ ! -d "$VENV_DIR" ]; then
    run_as_user "$UV_BIN" venv "$VENV_DIR"
fi

echo "[INFO] Installing J.A.R.V.I.S package..."
run_as_user "$UV_BIN" pip install -e "$APP_DIR" --python "$VENV_DIR"

# 6. Docker backend services
echo ""
echo "[INFO] Checking Docker installation..."
if ! command -v docker &>/dev/null; then
    echo "[INFO] Installing Docker Engine..."
    curl -fsSL https://get.docker.com -o /tmp/get-docker.sh
    sh /tmp/get-docker.sh >/dev/null 2>&1
    rm -f /tmp/get-docker.sh
    usermod -aG docker "$REAL_USER"
    systemctl enable docker
    systemctl start docker
    echo "[OK] Docker installed."
else
    echo "[OK] Docker already installed."
fi

if [ -f "$APP_DIR/docker-compose.yml" ]; then
    echo "[INFO] Pulling backend images..."
    docker pull searxng/searxng:latest

    # docker-compose.yml expects env_file at $HOME/.jarvish/.env — keep that contract
    run_as_user touch "$JARVISH_HOME/.env"

    echo "[INFO] Starting backend services..."
    if docker compose version &>/dev/null; then
        HOME="$REAL_HOME_DIR" docker compose -f "$APP_DIR/docker-compose.yml" --project-directory "$APP_DIR" up -d searxng
    elif command -v docker-compose &>/dev/null; then
        HOME="$REAL_HOME_DIR" docker-compose -f "$APP_DIR/docker-compose.yml" --project-directory "$APP_DIR" up -d searxng
    fi
    echo "[OK] Backend services started."
fi

# 7. Systemd service
echo ""
echo "[INFO] Installing systemd service..."
SERVICE_PATH="/etc/systemd/system/jarvish.service"
cat <<EOF > "$SERVICE_PATH"
[Unit]
Description=Jarvish AI Telegram Bot
After=network.target docker.service

[Service]
Type=simple
User=$REAL_USER
WorkingDirectory=$APP_DIR
ExecStart=$VENV_DIR/bin/jarvish-server
Environment=PYTHONUNBUFFERED=1
StandardOutput=append:$LOG_DIR/jarvish.log
StandardError=append:$LOG_DIR/jarvish.error.log
Restart=on-failure
RestartSec=5s

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable jarvish.service
systemctl restart jarvish.service
echo "[OK] jarvish.service is running."

# 8. Global CLI wrapper
echo ""
echo "[INFO] Linking global 'jarvish' command..."
ln -sf "$VENV_DIR/bin/jarvish" /usr/local/bin/jarvish
chmod +x /usr/local/bin/jarvish

echo ""
echo "=============================================="
echo "  Installation Complete — version $INSTALLED_VERSION"
echo "  Home directory:      $JARVISH_HOME"
echo ""
echo "  jarvish configure   - set up API keys / secrets"
echo "  jarvish doctor       - verify the install is healthy"
echo "  jarvish update       - check for a new version (no changes made)"
echo "  jarvish upgrade       - install the latest version"
echo "  jarvish status / logs / restart"
echo "=============================================="
