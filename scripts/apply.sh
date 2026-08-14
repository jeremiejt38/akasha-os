#!/bin/bash
# apply.sh — Deploy Akasha OS customizations to a LibreELEC RPi4
# Usage: ./scripts/apply.sh <pi-ip> <pi-password>
#
# This now ships the entire repo to the Pi and runs scripts/install.sh locally
# so the deployment logic is single-sourced and can be re-run safely after a
# LibreELEC / Kodi update.

set -euo pipefail

PI_IP="${1:?Usage: $0 <pi-ip> <pi-password>}"
PI_PASS="${2:?Usage: $0 <pi-ip> <pi-password>}"
SCRIPT_DIR="$(cd "$(dirname "$0")/.." && pwd)"

SSH_OPTS="-o StrictHostKeyChecking=no -o PreferredAuthentications=password -o PubkeyAuthentication=no"
SSH="sshpass -p $PI_PASS ssh $SSH_OPTS root@$PI_IP"
SCP="sshpass -p $PI_PASS scp $SSH_OPTS"

TAR_NAME="akasha-os-deploy.tar.gz"
TAR_PATH="/tmp/$TAR_NAME"
REMOTE_UPDATE_DIR="/storage/.update/akasha-os/deploy"

echo "=== Akasha OS Deployer ==="
echo "Target: root@$PI_IP"
echo "Source: $SCRIPT_DIR"
echo ""

# Test connectivity
if ! $SSH "echo connected" >/dev/null 2>&1; then
    echo "ERROR: Cannot connect to root@$PI_IP"
    exit 1
fi

echo "[1/4] Packing repo..."
rm -f "$TAR_PATH"
# Exclude .git and any update artifacts to keep the tarball small
cd "$SCRIPT_DIR"
tar -czf "$TAR_PATH" --exclude='.git' --exclude='.github' --exclude='node_modules' .

echo "[2/4] Uploading to Pi..."
$SSH "mkdir -p $REMOTE_UPDATE_DIR"
$SCP "$TAR_PATH" "root@$PI_IP:$REMOTE_UPDATE_DIR/$TAR_NAME"

echo "[3/4] Extracting and running installer..."
$SSH "
    cd $REMOTE_UPDATE_DIR
    rm -rf akasha-os
    mkdir akasha-os
    tar -xzf $TAR_NAME -C akasha-os
    cd akasha-os
    chmod +x scripts/install.sh
    ./scripts/install.sh
"

echo "[4/4] Restarting Kodi to apply changes..."
$SSH "systemctl restart kodi"

echo ""
echo "=== Deployment complete! ==="
echo "Done. Akasha OS is deployed on $PI_IP."
echo "The Pi will need a full reboot for boot partition changes to take effect."