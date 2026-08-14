#!/bin/bash
# deploy-latest.sh — Deploy latest Akasha OS changes to the Pi
# Applies: splash intro video, logo removal, menu reorder
#
# Usage: ./scripts/deploy-latest.sh
# (run from the akasha-os repo root, on the same LAN as the Pi)

set -euo pipefail

PI_IP="192.168.1.88"
PI_PASS="Jt85948594"
SCRIPT_DIR="$(cd "$(dirname "$0")/.." && pwd)"

SSH_OPTS="-o StrictHostKeyChecking=no -o ConnectTimeout=5"
SSH="sshpass -p $PI_PASS ssh $SSH_OPTS root@$PI_IP"
SCP="sshpass -p $PI_PASS scp $SSH_OPTS"

echo "=== Deploying latest Akasha OS changes to $PI_IP ==="

# Test connectivity
if ! $SSH "echo connected" >/dev/null 2>&1; then
    echo "ERROR: Cannot connect to root@$PI_IP"
    echo "Make sure you're on the same network as the Pi."
    exit 1
fi

SKIN_DIR="/storage/.kodi/addons/skin.arctic.horizon.2"

echo "[1/5] Deploying splash intro video..."
$SSH "mkdir -p /storage/.kodi/media"
$SCP "$SCRIPT_DIR/kodi/media/splash-intro.mp4" "root@$PI_IP:/storage/.kodi/media/splash-intro.mp4"

echo "[2/5] Deploying Akasha Splash service addon..."
$SSH "mkdir -p /storage/.kodi/addons/service.akasha.splash"
$SCP "$SCRIPT_DIR/kodi/addons/service.akasha.splash/addon.xml" "root@$PI_IP:/storage/.kodi/addons/service.akasha.splash/addon.xml"
$SCP "$SCRIPT_DIR/kodi/addons/service.akasha.splash/service.py" "root@$PI_IP:/storage/.kodi/addons/service.akasha.splash/service.py"
# Remove deprecated autoexec.py if present
$SSH "rm -f /storage/.kodi/userdata/autoexec.py"
# Enable the addon in Kodi DB (try multiple DB versions)
$SSH "for db in /storage/.kodi/userdata/Database/Addons*.db; do [ -f \"\$db\" ] && sqlite3 \"\$db\" \"INSERT OR REPLACE INTO installed (addonID, enabled, installDate) VALUES ('service.akasha.splash', 1, datetime('now'));\" 2>/dev/null; done; true"

echo "[3/5] Removing Akasha logo overlay (top-left)..."
$SSH "rm -f $SKIN_DIR/extras/icons/akasha-logo.png"

echo "[4/5] Deploying updated menu (Akasha first position)..."
$SCP "$SCRIPT_DIR/skin-patches/shortcuts/mainmenu.DATA.xml" "root@$PI_IP:$SKIN_DIR/shortcuts/mainmenu.DATA.xml"
# Force skinshortcuts rebuild
$SSH "rm -f /storage/.kodi/userdata/addon_data/script.skinshortcuts/skin.arctic.horizon.2.hash"

echo "[5/5] Disabling Kodi built-in splash..."
$SSH "if [ ! -f /storage/.kodi/userdata/advancedsettings.xml ]; then echo '<advancedsettings><splash>false</splash></advancedsettings>' > /storage/.kodi/userdata/advancedsettings.xml; elif ! grep -q '<splash>' /storage/.kodi/userdata/advancedsettings.xml; then sed -i 's|</advancedsettings>|<splash>false</splash></advancedsettings>|' /storage/.kodi/userdata/advancedsettings.xml; fi"

echo ""
echo "=== Restarting Kodi to apply changes... ==="
$SSH "systemctl restart kodi"

echo ""
echo "Done! Changes applied:"
echo "  - Splash intro video plays on boot"
echo "  - Akasha logo removed from top-left"
echo "  - Akasha menu moved to first position"
echo ""
echo "Note: For the intro video, do a full reboot (power off/on) for best results."
