#!/usr/bin/env bash
# Install host timer that scales lotto container limits with server load.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
UNIT_DIR="/etc/systemd/system"

if [[ "$(id -u)" -ne 0 ]]; then
  echo "Run as root: sudo $0"
  exit 1
fi

if ! python3 -c "import yaml" 2>/dev/null; then
  echo "Installing python3-yaml for resource_governor.py..."
  apt-get update -qq && apt-get install -y -qq python3-yaml
fi

install -m 0644 "$ROOT/deploy/systemd/lotto-resource-governor.service" "$UNIT_DIR/"
install -m 0644 "$ROOT/deploy/systemd/lotto-resource-governor.timer" "$UNIT_DIR/"
systemctl daemon-reload
systemctl enable --now lotto-resource-governor.timer
systemctl start lotto-resource-governor.service
echo "OK: lotto-resource-governor.timer active (every ~1 min). Check: systemctl status lotto-resource-governor.timer"
