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

echo "[1/9] Deploying boot files..."
$SSH "mount -o remount,rw /flash"
$SCP "$SCRIPT_DIR/boot/config.txt" "root@$PI_IP:/flash/config.txt"
$SCP "$SCRIPT_DIR/boot/cmdline.txt" "root@$PI_IP:/flash/cmdline.txt"
$SCP "$SCRIPT_DIR/boot/oemsplash.png" "root@$PI_IP:/flash/oemsplash.png"
$SSH "mount -o remount,ro /flash"

echo "[2/9] Deploying system config..."
$SCP "$SCRIPT_DIR/system/autostart.sh" "root@$PI_IP:/storage/.config/autostart.sh"
$SCP "$SCRIPT_DIR/system/cec-standby.sh" "root@$PI_IP:/storage/.config/cec-standby.sh"
$SSH "chmod +x /storage/.config/autostart.sh /storage/.config/cec-standby.sh"
$SSH "mkdir -p /storage/.config/system.d"
$SCP "$SCRIPT_DIR/system/system.d/cec-tv.service" "root@$PI_IP:/storage/.config/system.d/cec-tv.service"
$SCP "$SCRIPT_DIR/system/system.d/cec-tv.service.d/override.conf" "root@$PI_IP:/storage/.config/system.d/cec-tv.service.d/override.conf"
$SCP "$SCRIPT_DIR/system/system.d/cec-wakeup.service" "root@$PI_IP:/storage/.config/system.d/cec-wakeup.service"
$SCP "$SCRIPT_DIR/system/system.d/splash-poweroff.service" "root@$PI_IP:/storage/.config/system.d/splash-poweroff.service"
$SCP "$SCRIPT_DIR/system/system.d/splash-reboot.service" "root@$PI_IP:/storage/.config/system.d/splash-reboot.service"
$SSH "systemctl daemon-reload && systemctl enable cec-tv.service cec-wakeup.service splash-poweroff.service splash-reboot.service"
# Drop-in: show reboot splash on Kodi restart
$SSH "mkdir -p /storage/.config/system.d/kodi.service.d"
$SCP "$SCRIPT_DIR/system/system.d/kodi.service.d/splash-restart.conf" "root@$PI_IP:/storage/.config/system.d/kodi.service.d/splash-restart.conf"

echo "[3/9] Deploying Kodi splash + boot intro video..."
$SSH "mkdir -p /storage/.kodi/media"
$SCP "$SCRIPT_DIR/kodi/media/splash.png" "root@$PI_IP:/storage/.kodi/media/splash.png"
$SCP "$SCRIPT_DIR/kodi/media/splash-intro.mp4" "root@$PI_IP:/storage/.kodi/media/splash-intro.mp4"

echo "[3b/9] Deploying Akasha Splash service addon..."
$SSH "mkdir -p /storage/.kodi/addons/service.akasha.splash"
$SCP -r "$SCRIPT_DIR/kodi/addons/service.akasha.splash/" "root@$PI_IP:/storage/.kodi/addons/service.akasha.splash/"
# Enable the addon in Kodi's addon database
$SSH "sqlite3 /storage/.kodi/userdata/Database/Addons33.db \"INSERT OR REPLACE INTO installed (addonID, enabled, installDate) VALUES ('service.akasha.splash', 1, datetime('now'));\" 2>/dev/null || true"

echo "[3c/9] Deploying shutdown/reboot splash scripts & images..."
$SSH "mkdir -p /storage/.kodi/scripts"
$SCP "$SCRIPT_DIR/kodi/scripts/show-splash.sh" "root@$PI_IP:/storage/.kodi/scripts/show-splash.sh"
$SCP "$SCRIPT_DIR/kodi/scripts/show-splash-if-restart.sh" "root@$PI_IP:/storage/.kodi/scripts/show-splash-if-restart.sh"
$SCP "$SCRIPT_DIR/kodi/scripts/generate-splash-messages.py" "root@$PI_IP:/storage/.kodi/scripts/generate-splash-messages.py"
$SSH "chmod +x /storage/.kodi/scripts/show-splash.sh /storage/.kodi/scripts/show-splash-if-restart.sh"
$SSH "python3 /storage/.kodi/scripts/generate-splash-messages.py"

$SSH "systemctl daemon-reload"

echo "[4/9] Deploying Akasha Settings addon..."
$SSH "mkdir -p /storage/.kodi/addons/script.akasha.settings"
$SCP -r "$SCRIPT_DIR/kodi/addons/script.akasha.settings/" "root@$PI_IP:/storage/.kodi/addons/script.akasha.settings/"

echo "[5/9] Deploying Cloud Gaming addon + scripts..."
$SSH "mkdir -p /storage/.kodi/addons/script.cloud.gaming"
$SCP -r "$SCRIPT_DIR/kodi/addons/script.cloud.gaming/" "root@$PI_IP:/storage/.kodi/addons/script.cloud.gaming/"
$SSH "mkdir -p /storage/.kodi/scripts/cloud-gaming"
$SCP "$SCRIPT_DIR/kodi/scripts/cloud-gaming/Dockerfile" "root@$PI_IP:/storage/.kodi/scripts/cloud-gaming/Dockerfile"
$SCP "$SCRIPT_DIR/kodi/scripts/cloud-gaming/entrypoint.sh" "root@$PI_IP:/storage/.kodi/scripts/cloud-gaming/entrypoint.sh"
$SCP "$SCRIPT_DIR/kodi/scripts/cloud-gaming/launch.sh" "root@$PI_IP:/storage/.kodi/scripts/cloud-gaming/launch.sh"
$SCP "$SCRIPT_DIR/kodi/scripts/cloud-gaming/guide_watchdog.py" "root@$PI_IP:/storage/.kodi/scripts/cloud-gaming/guide_watchdog.py"
$SSH "chmod +x /storage/.kodi/scripts/cloud-gaming/launch.sh /storage/.kodi/scripts/cloud-gaming/entrypoint.sh /storage/.kodi/scripts/cloud-gaming/guide_watchdog.py"

echo "[6/9] Deploying skin patches (Arctic Horizon 2)..."
SKIN_DIR="/storage/.kodi/addons/skin.arctic.horizon.2"
$SSH "mkdir -p $SKIN_DIR/shortcuts $SKIN_DIR/extras/icons"
# Deploy Akasha OS startup logo
$SCP "$SCRIPT_DIR/kodi/media/akasha-logo-circle.png" "root@$PI_IP:$SKIN_DIR/extras/icons/akasha-logo-circle.png"
$SCP "$SCRIPT_DIR/skin-patches/patch_startup_logo.py" "root@$PI_IP:/tmp/patch_startup_logo.py"
# Patch startup logo/texte in Includes_Objects.xml
$SSH "python3 /tmp/patch_startup_logo.py"
# Remove old Akasha logo overlay if present
$SSH "rm -f $SKIN_DIR/extras/icons/akasha-logo.png"
$SCP "$SCRIPT_DIR/skin-patches/overrides.xml" "root@$PI_IP:$SKIN_DIR/shortcuts/overrides.xml"
$SCP "$SCRIPT_DIR/skin-patches/shortcuts/mainmenu.DATA.xml" "root@$PI_IP:$SKIN_DIR/shortcuts/mainmenu.DATA.xml"
$SCP "$SCRIPT_DIR/skin-patches/shortcuts/games.DATA.xml" "root@$PI_IP:$SKIN_DIR/shortcuts/games.DATA.xml"
$SCP "$SCRIPT_DIR/skin-patches/shortcuts/games-1.DATA.xml" "root@$PI_IP:$SKIN_DIR/shortcuts/games-1.DATA.xml"
$SCP "$SCRIPT_DIR/skin-patches/shortcuts/music.DATA.xml" "root@$PI_IP:$SKIN_DIR/shortcuts/music.DATA.xml"
# Force skinshortcuts rebuild
$SSH "rm -f /storage/.kodi/userdata/addon_data/script.skinshortcuts/skin.arctic.horizon.2.hash"

echo "[7/9] Deploying controller buttonmap..."
BUTTONMAP_DIR="/storage/.kodi/userdata/addon_data/peripheral.joystick/resources/buttonmaps/xml/linux"
if [ -f "$SCRIPT_DIR/kodi/userdata/addon_data/peripheral.joystick/resources/buttonmaps/xml/linux/Xbox_Wireless_Controller_15b_8a.xml" ]; then
    $SSH "mkdir -p $BUTTONMAP_DIR"
    $SCP "$SCRIPT_DIR/kodi/userdata/addon_data/peripheral.joystick/resources/buttonmaps/xml/linux/Xbox_Wireless_Controller_15b_8a.xml" "root@$PI_IP:$BUTTONMAP_DIR/Xbox_Wireless_Controller_15b_8a.xml"
else
    echo "  (skipped — buttonmap file not present)"
fi

echo "[8/9] Building Cloud Gaming Docker image..."
$SSH "cd /storage/.kodi/scripts/cloud-gaming && docker build -t akasha-chromium . 2>&1 | tail -5"

echo "[9/9] Disabling Kodi built-in splash (replaced by intro video)..."
$SSH "mkdir -p /storage/.kodi/userdata"
$SSH "if [ ! -f /storage/.kodi/userdata/advancedsettings.xml ]; then echo '<advancedsettings><splash>false</splash></advancedsettings>' > /storage/.kodi/userdata/advancedsettings.xml; elif ! grep -q '<splash>' /storage/.kodi/userdata/advancedsettings.xml; then sed -i 's|</advancedsettings>|<splash>false</splash></advancedsettings>|' /storage/.kodi/userdata/advancedsettings.xml; fi"

echo ""
echo "=== Deployment complete! ==="
echo "Setting device name to 'Akasha OS'..."
$SSH "echo 'Akasha OS' > /storage/.cache/hostname"

echo "Restarting Kodi to apply changes..."
$SSH "systemctl restart kodi"

echo ""
echo "Done. Akasha OS is deployed on $PI_IP."
echo "The Pi will need a full reboot for boot partition changes to take effect."
