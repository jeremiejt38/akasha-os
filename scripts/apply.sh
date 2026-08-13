#!/bin/bash
# apply.sh — Deploy Akasha OS customizations to a LibreELEC RPi4
# Usage: ./scripts/apply.sh <pi-ip> <pi-password>
#
# Prerequisites:
#   - Fresh LibreELEC 12 (Omega) installed on the target Pi
#   - SSH enabled (default on LibreELEC)
#   - sshpass installed on the deploying machine

set -euo pipefail

PI_IP="${1:?Usage: $0 <pi-ip> <pi-password>}"
PI_PASS="${2:?Usage: $0 <pi-ip> <pi-password>}"
SCRIPT_DIR="$(cd "$(dirname "$0")/.." && pwd)"

SSH_OPTS="-o StrictHostKeyChecking=no -o PreferredAuthentications=password -o PubkeyAuthentication=no"
SSH="sshpass -p $PI_PASS ssh $SSH_OPTS root@$PI_IP"
SCP="sshpass -p $PI_PASS scp $SSH_OPTS"

echo "=== Akasha OS Deployer ==="
echo "Target: root@$PI_IP"
echo "Source: $SCRIPT_DIR"
echo ""

# Test connectivity
if ! $SSH "echo connected" >/dev/null 2>&1; then
    echo "ERROR: Cannot connect to root@$PI_IP"
    exit 1
fi

echo "[1/8] Deploying boot files..."
$SSH "mount -o remount,rw /flash"
$SCP "$SCRIPT_DIR/boot/config.txt" "root@$PI_IP:/flash/config.txt"
$SCP "$SCRIPT_DIR/boot/cmdline.txt" "root@$PI_IP:/flash/cmdline.txt"
$SCP "$SCRIPT_DIR/boot/oemsplash.png" "root@$PI_IP:/flash/oemsplash.png"
$SSH "mount -o remount,ro /flash"

echo "[2/8] Deploying system config..."
$SCP "$SCRIPT_DIR/system/autostart.sh" "root@$PI_IP:/storage/.config/autostart.sh"
$SCP "$SCRIPT_DIR/system/cec-standby.sh" "root@$PI_IP:/storage/.config/cec-standby.sh"
$SSH "chmod +x /storage/.config/autostart.sh /storage/.config/cec-standby.sh"
$SSH "mkdir -p /storage/.config/system.d"
$SCP "$SCRIPT_DIR/system/system.d/cec-tv.service" "root@$PI_IP:/storage/.config/system.d/cec-tv.service"
$SSH "systemctl daemon-reload && systemctl enable cec-tv.service"

echo "[3/8] Deploying Kodi splash..."
$SSH "mkdir -p /storage/.kodi/media"
$SCP "$SCRIPT_DIR/kodi/media/splash.png" "root@$PI_IP:/storage/.kodi/media/splash.png"

echo "[4/8] Deploying Akasha Settings addon..."
$SSH "mkdir -p /storage/.kodi/addons/script.akasha.settings"
$SCP -r "$SCRIPT_DIR/kodi/addons/script.akasha.settings/" "root@$PI_IP:/storage/.kodi/addons/script.akasha.settings/"

echo "[5/8] Deploying Cloud Gaming addon + scripts..."
$SSH "mkdir -p /storage/.kodi/addons/script.cloud.gaming"
$SCP -r "$SCRIPT_DIR/kodi/addons/script.cloud.gaming/" "root@$PI_IP:/storage/.kodi/addons/script.cloud.gaming/"
$SSH "mkdir -p /storage/.kodi/scripts/cloud-gaming"
$SCP "$SCRIPT_DIR/kodi/scripts/cloud-gaming/Dockerfile" "root@$PI_IP:/storage/.kodi/scripts/cloud-gaming/Dockerfile"
$SCP "$SCRIPT_DIR/kodi/scripts/cloud-gaming/entrypoint.sh" "root@$PI_IP:/storage/.kodi/scripts/cloud-gaming/entrypoint.sh"
$SCP "$SCRIPT_DIR/kodi/scripts/cloud-gaming/launch.sh" "root@$PI_IP:/storage/.kodi/scripts/cloud-gaming/launch.sh"
$SCP "$SCRIPT_DIR/kodi/scripts/cloud-gaming/guide_watchdog.py" "root@$PI_IP:/storage/.kodi/scripts/cloud-gaming/guide_watchdog.py"
$SSH "chmod +x /storage/.kodi/scripts/cloud-gaming/launch.sh /storage/.kodi/scripts/cloud-gaming/entrypoint.sh /storage/.kodi/scripts/cloud-gaming/guide_watchdog.py"

echo "[6/8] Deploying skin patches (Arctic Horizon 2)..."
SKIN_DIR="/storage/.kodi/addons/skin.arctic.horizon.2"
$SSH "mkdir -p $SKIN_DIR/shortcuts $SKIN_DIR/extras/icons"
$SCP "$SCRIPT_DIR/skin-patches/akasha-logo.png" "root@$PI_IP:$SKIN_DIR/extras/icons/akasha-logo.png"
$SCP "$SCRIPT_DIR/skin-patches/overrides.xml" "root@$PI_IP:$SKIN_DIR/shortcuts/overrides.xml"
$SCP "$SCRIPT_DIR/skin-patches/shortcuts/mainmenu.DATA.xml" "root@$PI_IP:$SKIN_DIR/shortcuts/mainmenu.DATA.xml"
$SCP "$SCRIPT_DIR/skin-patches/shortcuts/games.DATA.xml" "root@$PI_IP:$SKIN_DIR/shortcuts/games.DATA.xml"
$SCP "$SCRIPT_DIR/skin-patches/shortcuts/games-1.DATA.xml" "root@$PI_IP:$SKIN_DIR/shortcuts/games-1.DATA.xml"
$SCP "$SCRIPT_DIR/skin-patches/shortcuts/music.DATA.xml" "root@$PI_IP:$SKIN_DIR/shortcuts/music.DATA.xml"
# Force skinshortcuts rebuild
$SSH "rm -f /storage/.kodi/userdata/addon_data/script.skinshortcuts/skin.arctic.horizon.2.hash"

echo "[7/8] Deploying controller buttonmap..."
BUTTONMAP_DIR="/storage/.kodi/userdata/addon_data/peripheral.joystick/resources/buttonmaps/xml/linux"
if [ -f "$SCRIPT_DIR/kodi/userdata/addon_data/peripheral.joystick/resources/buttonmaps/xml/linux/Xbox_Wireless_Controller_15b_8a.xml" ]; then
    $SSH "mkdir -p $BUTTONMAP_DIR"
    $SCP "$SCRIPT_DIR/kodi/userdata/addon_data/peripheral.joystick/resources/buttonmaps/xml/linux/Xbox_Wireless_Controller_15b_8a.xml" "root@$PI_IP:$BUTTONMAP_DIR/Xbox_Wireless_Controller_15b_8a.xml"
else
    echo "  (skipped — buttonmap file not present)"
fi

echo "[8/8] Building Cloud Gaming Docker image..."
$SSH "cd /storage/.kodi/scripts/cloud-gaming && docker build -t akasha-chromium . 2>&1 | tail -5"

echo ""
echo "=== Deployment complete! ==="
echo "Setting device name to 'Akasha OS'..."
$SSH "echo 'Akasha OS' > /storage/.cache/hostname"

echo "Restarting Kodi to apply changes..."
$SSH "systemctl restart kodi"

echo ""
echo "Done. Akasha OS is deployed on $PI_IP."
echo "The Pi will need a full reboot for boot partition changes to take effect."
