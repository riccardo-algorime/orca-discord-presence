#!/bin/sh
set -eu

DATA_HOME=${XDG_DATA_HOME:-"$HOME/.local/share"}
CONFIG_HOME=${XDG_CONFIG_HOME:-"$HOME/.config"}
DATA_DIR="$DATA_HOME/orca-discord-presence"
CONFIG_DIR="$CONFIG_HOME/orca-discord-presence"
SERVICE="$CONFIG_HOME/systemd/user/orca-discord-presence.service"

systemctl --user disable --now orca-discord-presence.service 2>/dev/null || true
rm -f "$SERVICE"
rm -rf "$DATA_DIR"
systemctl --user daemon-reload
systemctl --user reset-failed

if [ "${1:-}" = "--purge" ]; then
    rm -rf "$CONFIG_DIR"
    echo "Removed service, application data, and configuration."
else
    echo "Removed service and application data."
    echo "Preserved configuration: $CONFIG_DIR/config.toml"
fi
