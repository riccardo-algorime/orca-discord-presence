#!/bin/sh
set -eu

ROOT=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
DATA_HOME=${XDG_DATA_HOME:-"$HOME/.local/share"}
CONFIG_HOME=${XDG_CONFIG_HOME:-"$HOME/.config"}
DATA_DIR="$DATA_HOME/orca-discord-presence"
CONFIG_DIR="$CONFIG_HOME/orca-discord-presence"
SYSTEMD_DIR="$CONFIG_HOME/systemd/user"
SERVICE="$SYSTEMD_DIR/orca-discord-presence.service"
VENV="$DATA_DIR/venv"
EXECUTABLE="$VENV/bin/orca-discord-presence"
CONFIG="$CONFIG_DIR/config.toml"

python3 -c 'import sys; raise SystemExit(sys.version_info < (3, 11))' || {
    echo "Python 3.11 or newer is required." >&2
    exit 1
}
python3 -c 'import venv' || {
    echo "Python venv support is required." >&2
    exit 1
}

mkdir -p "$DATA_DIR" "$CONFIG_DIR" "$SYSTEMD_DIR"
python3 -m venv "$VENV"
"$VENV/bin/python" -m pip install --upgrade "$ROOT"

if [ ! -f "$CONFIG" ]; then
    cp "$ROOT/config.example.toml" "$CONFIG"
fi

sed \
    -e "s|@EXECUTABLE@|$EXECUTABLE|g" \
    -e "s|@CONFIG@|$CONFIG|g" \
    "$ROOT/systemd/orca-discord-presence.service.in" > "$SERVICE"

systemctl --user daemon-reload
systemctl --user enable orca-discord-presence.service
systemctl --user restart orca-discord-presence.service

echo "Installed and started orca-discord-presence.service"
echo "Configuration: $CONFIG"
echo "Logs: journalctl --user -u orca-discord-presence.service -f"
