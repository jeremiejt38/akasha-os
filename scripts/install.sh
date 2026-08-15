#!/bin/bash
# install.sh — Apply Akasha OS customizations locally on a LibreELEC device.
# This script is meant to run on the RPi itself (called by update-akasha-os.py
# or by a release tarball). It is idempotent and safe to re-run after a
# LibreELEC / Kodi update.
#
# Usage: /path/to/repo/scripts/install.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")/.." && pwd)"

log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] $*" | tee -a /storage/.kodi/temp/akasha-install.log
}

# Persistent Akasha OS version marker (source of truth is package.json)
mkdir -p /storage/.config/akasha-os
python3 -c "import json; print(json.load(open('$SCRIPT_DIR/package.json'))['version'])" > /storage/.config/akasha-os/VERSION

# Keep update-status.json if it exists; the startup service will show and
# delete it after the reboot. Only remove a stale one during a manual fresh
# install, which is rare and should not happen during an OTA update.

log "=== Akasha OS local installer ==="
log "Source: $SCRIPT_DIR"

# ---------------------------------------------------------------------------
# 1. Boot files
# ---------------------------------------------------------------------------
log "[1/13] Installing boot files..."
if [ -f "$SCRIPT_DIR/boot/config.txt" ]; then
    mount -o remount,rw /flash
    cp "$SCRIPT_DIR/boot/config.txt" /flash/config.txt
    cp "$SCRIPT_DIR/boot/cmdline.txt" /flash/cmdline.txt
    cp "$SCRIPT_DIR/boot/oemsplash.png" /flash/oemsplash.png
    mount -o remount,ro /flash
fi

# ---------------------------------------------------------------------------
# 2. System config / systemd
# ---------------------------------------------------------------------------
log "[2/13] Installing system config..."
mkdir -p /storage/.config/system.d
mkdir -p /storage/.config/system.d/cec-tv.service.d
mkdir -p /storage/.config/system.d/kodi.service.d

cp "$SCRIPT_DIR/system/autostart.sh" /storage/.config/autostart.sh
cp "$SCRIPT_DIR/system/cec-standby.sh" /storage/.config/cec-standby.sh
cp "$SCRIPT_DIR/system/cec-wakeup.sh" /storage/.config/cec-wakeup.sh
cp "$SCRIPT_DIR/system/wifi-silent-agent.py" /storage/.config/wifi-silent-agent.py
cp "$SCRIPT_DIR/system/wifi-watchdog.sh" /storage/.config/wifi-watchdog.sh
cp "$SCRIPT_DIR/system/splash-video.sh" /storage/splash-video.sh
cp "$SCRIPT_DIR/system/connman/connman_main.conf.example" /storage/.config/connman_main.conf
cp "$SCRIPT_DIR/system/akasha-disable-official-updates.sh" /storage/.config/akasha-os/disable-official-updates.sh

cp "$SCRIPT_DIR/system/system.d/cec-tv.service" /storage/.config/system.d/cec-tv.service
cp "$SCRIPT_DIR/system/system.d/cec-tv.service.d/override.conf" /storage/.config/system.d/cec-tv.service.d/override.conf
cp "$SCRIPT_DIR/system/system.d/cec-wakeup.service" /storage/.config/system.d/cec-wakeup.service
cp "$SCRIPT_DIR/system/system.d/cec-wake-early.service" /storage/.config/system.d/cec-wake-early.service
cp "$SCRIPT_DIR/system/system.d/splash-video.service" /storage/.config/system.d/splash-video.service
cp "$SCRIPT_DIR/system/system.d/splash-poweroff.service" /storage/.config/system.d/splash-poweroff.service
cp "$SCRIPT_DIR/system/system.d/splash-reboot.service" /storage/.config/system.d/splash-reboot.service
cp "$SCRIPT_DIR/system/system.d/akasha-disable-official-updates.service" /storage/.config/system.d/akasha-disable-official-updates.service
cp "$SCRIPT_DIR/system/system.d/kodi.service.d/splash-restart.conf" /storage/.config/system.d/kodi.service.d/splash-restart.conf

chmod +x /storage/.config/autostart.sh \
          /storage/.config/cec-standby.sh \
          /storage/.config/cec-wakeup.sh \
          /storage/.config/akasha-os/disable-official-updates.sh \
          /storage/splash-video.sh

# ---------------------------------------------------------------------------
# 3. Docker alias cleanup (prevent double start after LibreELEC update)
# ---------------------------------------------------------------------------
log "[3/13] Cleaning Docker alias..."
rm -f /storage/.config/system.d/docker.service
rm -f /storage/.config/system.d/kodi.target.wants/docker.service

# ---------------------------------------------------------------------------
# 4. Kodi media + intro + splash scripts
# ---------------------------------------------------------------------------
log "[4/13] Installing Kodi media and splash scripts..."
mkdir -p /storage/.kodi/media
mkdir -p /storage/.kodi/scripts

cp "$SCRIPT_DIR/kodi/media/splash.png" /storage/.kodi/media/splash.png
cp "$SCRIPT_DIR/kodi/media/splash-intro.mp4" /storage/.kodi/media/splash-intro.mp4
cp "$SCRIPT_DIR/kodi/media/akasha-logo-circle.png" /storage/.kodi/media/akasha-logo-circle.png

# Pre-extract audio so the pre-Kodi boot splash can play sound via aplay.
# ffmpeg with direct ALSA output segfaults on LibreELEC, so we use aplay.
FFMPEG=/storage/ffmpeg
if [ -x "$FFMPEG" ] && [ -f /storage/.kodi/media/splash-intro.mp4 ]; then
    "$FFMPEG" -y -i /storage/.kodi/media/splash-intro.mp4 \
        -vn -ac 2 -ar 48000 /storage/.kodi/media/splash-intro.wav 2>/dev/null || true
fi

cp "$SCRIPT_DIR/kodi/scripts/show-splash.sh" /storage/.kodi/scripts/show-splash.sh
cp "$SCRIPT_DIR/kodi/scripts/show-splash-if-restart.sh" /storage/.kodi/scripts/show-splash-if-restart.sh
cp "$SCRIPT_DIR/kodi/scripts/generate-splash-messages.py" /storage/.kodi/scripts/generate-splash-messages.py
cp "$SCRIPT_DIR/scripts/update-akasha-os.py" /storage/.kodi/scripts/update-akasha-os.py
cp "$SCRIPT_DIR/kodi/scripts/akasha-guide.py" /storage/.kodi/scripts/akasha-guide.py
chmod +x /storage/.kodi/scripts/akasha-guide.py
cp "$SCRIPT_DIR/kodi/scripts/akasha-sleep.py" /storage/.kodi/scripts/akasha-sleep.py
chmod +x /storage/.kodi/scripts/akasha-sleep.py

chmod +x /storage/.kodi/scripts/show-splash.sh \
          /storage/.kodi/scripts/show-splash-if-restart.sh \
          /storage/.kodi/scripts/update-akasha-os.py

# ---------------------------------------------------------------------------
# 5. Splash addon (service.akasha.splash)
# ---------------------------------------------------------------------------
log "[5/13] Installing Akasha Splash addon..."
rm -rf /storage/.kodi/addons/service.akasha.splash
cp -r "$SCRIPT_DIR/kodi/addons/service.akasha.splash" /storage/.kodi/addons/

# ---------------------------------------------------------------------------
# 6. Akasha Settings addon
# ---------------------------------------------------------------------------
log "[6/13] Installing Akasha Settings addon..."
rm -rf /storage/.kodi/addons/script.akasha.settings
cp -r "$SCRIPT_DIR/kodi/addons/script.akasha.settings" /storage/.kodi/addons/

# ---------------------------------------------------------------------------
# 7. Akasha Overlay service
# ---------------------------------------------------------------------------
log "[7/13] Installing Akasha Overlay addon..."
rm -rf /storage/.kodi/addons/service.akasha.overlay
cp -r "$SCRIPT_DIR/kodi/addons/service.akasha.overlay" /storage/.kodi/addons/

log "  Installing Akasha Guide addon..."
rm -rf /storage/.kodi/addons/script.akasha.guide
cp -r "$SCRIPT_DIR/kodi/addons/script.akasha.guide" /storage/.kodi/addons/

# ---------------------------------------------------------------------------
# 8. Cloud Gaming addon + scripts
# ---------------------------------------------------------------------------
log "[8/13] Installing Cloud Gaming addon..."
rm -rf /storage/.kodi/addons/script.cloud.gaming
cp -r "$SCRIPT_DIR/kodi/addons/script.cloud.gaming" /storage/.kodi/addons/

mkdir -p /storage/.kodi/scripts/cloud-gaming
cp "$SCRIPT_DIR/kodi/scripts/cloud-gaming/Dockerfile" /storage/.kodi/scripts/cloud-gaming/
cp "$SCRIPT_DIR/kodi/scripts/cloud-gaming/entrypoint.sh" /storage/.kodi/scripts/cloud-gaming/
cp "$SCRIPT_DIR/kodi/scripts/cloud-gaming/launch.sh" /storage/.kodi/scripts/cloud-gaming/

# Enable Akasha addons in Kodi's database so services/programs start automatically
sqlite3 /storage/.kodi/userdata/Database/Addons33.db \
    "INSERT OR REPLACE INTO installed (addonID, enabled, installDate) VALUES
        ('service.akasha.splash', 1, datetime('now')),
        ('service.akasha.overlay', 1, datetime('now')),
        ('script.akasha.settings', 1, datetime('now')),
        ('script.akasha.guide', 1, datetime('now')),
        ('script.cloud.gaming', 1, datetime('now'))" 2>/dev/null || true
cp "$SCRIPT_DIR/kodi/scripts/cloud-gaming/guide_watchdog.py" /storage/.kodi/scripts/cloud-gaming/
chmod +x /storage/.kodi/scripts/cloud-gaming/launch.sh \
          /storage/.kodi/scripts/cloud-gaming/entrypoint.sh \
          /storage/.kodi/scripts/cloud-gaming/guide_watchdog.py

# Build Cloud Gaming Docker image if Docker is running
if [ -f /storage/.kodi/scripts/cloud-gaming/Dockerfile ] && \
   systemctl is-active --quiet service.system.docker 2>/dev/null; then
    log "  Building Cloud Gaming Docker image..."
    (cd /storage/.kodi/scripts/cloud-gaming && docker build -t akasha-chromium . 2>&1 | tail -5) || \
        log "  WARNING: Docker image build failed"
fi

# ---------------------------------------------------------------------------
# 8. Generate shutdown/reboot splash raw images
# ---------------------------------------------------------------------------
log "[9/13] Generating splash images..."
python3 /storage/.kodi/scripts/generate-splash-messages.py

# ---------------------------------------------------------------------------
# 9. Skin patches (Arctic Horizon 2)
# ---------------------------------------------------------------------------
log "[10/13] Applying Arctic Horizon 2 skin patches..."
SKIN_DIR="/storage/.kodi/addons/skin.arctic.horizon.2"
mkdir -p "$SKIN_DIR/shortcuts" "$SKIN_DIR/extras/icons"

if [ -d "$SKIN_DIR" ]; then
    cp "$SCRIPT_DIR/kodi/media/akasha-logo-circle.png" "$SKIN_DIR/extras/icons/akasha-logo-circle.png"
    cp "$SCRIPT_DIR/skin-patches/overrides.xml" "$SKIN_DIR/shortcuts/overrides.xml"
    cp "$SCRIPT_DIR/skin-patches/shortcuts/mainmenu.DATA.xml" "$SKIN_DIR/shortcuts/mainmenu.DATA.xml"
    cp "$SCRIPT_DIR/skin-patches/shortcuts/games.DATA.xml" "$SKIN_DIR/shortcuts/games.DATA.xml"
    cp "$SCRIPT_DIR/skin-patches/shortcuts/games-1.DATA.xml" "$SKIN_DIR/shortcuts/games-1.DATA.xml"
    cp "$SCRIPT_DIR/skin-patches/shortcuts/music.DATA.xml" "$SKIN_DIR/shortcuts/music.DATA.xml"

    # Patch startup logo / text
    python3 "$SCRIPT_DIR/skin-patches/patch_startup_logo.py" "$SKIN_DIR"

    # Patch DialogConfirm so the OK/Yes button is focused by default
    # (makes the A button close Dialog.ok / yesnocustom dialogs)
    python3 "$SCRIPT_DIR/skin-patches/patch_dialog_default_control.py" "$SKIN_DIR"

    # Force skinshortcuts rebuild
    rm -f /storage/.kodi/userdata/addon_data/script.skinshortcuts/skin.arctic.horizon.2.hash

    # Add Akasha system overlay (toggle from Akasha Settings)
    if [ -f "$SCRIPT_DIR/skin-patches/overlay/Custom_1199_Overlay.xml" ]; then
        cp "$SCRIPT_DIR/skin-patches/overlay/Custom_1199_Overlay.xml" "$SKIN_DIR/1080i/Custom_1199_Overlay.xml"
    fi
    # Remove obsolete guide skin files (guide is now a Python script addon)
    rm -f "$SKIN_DIR/1080i/Custom_1193_Guide.xml" "$SKIN_DIR/1080i/Custom_1197_Guide.xml"

    # Make native context-menu header say "Akasha", show the Akasha logo, and version label
    cp "$SCRIPT_DIR/kodi/media/akasha-title.png" "$SKIN_DIR/media/akasha-title.png"
    AKASHA_VERSION=$(python3 -c "import json; print(json.load(open('$SCRIPT_DIR/.release-please-manifest.json'))['.'])" 2>/dev/null || echo '')
    python3 "$SCRIPT_DIR/skin-patches/patch_contextmenu_title.py" "$SKIN_DIR" "$AKASHA_VERSION"
else
    log "WARNING: Arctic Horizon 2 skin not installed; skipping skin patches."
fi

# ---------------------------------------------------------------------------
# 10. Controller buttonmap
# ---------------------------------------------------------------------------
log "[11/13] Installing controller buttonmap..."
BUTTONMAP_DIR="/storage/.kodi/userdata/addon_data/peripheral.joystick/resources/buttonmaps/xml/linux"
if [ -f "$SCRIPT_DIR/kodi/userdata/addon_data/peripheral.joystick/resources/buttonmaps/xml/linux/Xbox_Wireless_Controller_15b_8a.xml" ]; then
    mkdir -p "$BUTTONMAP_DIR"
    cp "$SCRIPT_DIR/kodi/userdata/addon_data/peripheral.joystick/resources/buttonmaps/xml/linux/Xbox_Wireless_Controller_15b_8a.xml" "$BUTTONMAP_DIR/"
fi

# ---------------------------------------------------------------------------
# 11. Gamepad volume keymap
# ---------------------------------------------------------------------------
log "[12/13] Installing gamepad volume keymap..."
mkdir -p /storage/.kodi/userdata/keymaps
rm -f /storage/.kodi/userdata/keymaps/joystick.xml
if [ -f "$SCRIPT_DIR/kodi/userdata/keymaps/keymap.xml" ]; then
    cp "$SCRIPT_DIR/kodi/userdata/keymaps/keymap.xml" /storage/.kodi/userdata/keymaps/keymap.xml
fi
if [ -f "$SCRIPT_DIR/scripts/volume.py" ]; then
    cp "$SCRIPT_DIR/scripts/volume.py" /storage/.kodi/scripts/volume.py
    chmod +x /storage/.kodi/scripts/volume.py
fi

# ---------------------------------------------------------------------------
# 12. System tweaks
# ---------------------------------------------------------------------------
log "[13/13] Finalizing system tweaks..."

# Run the LibreELEC update blocker once right now, and enable the service
# so it also runs on every boot after a LibreELEC / Kodi update.
/storage/.config/akasha-os/disable-official-updates.sh 2>/dev/null || true

# Disable Kodi built-in splash (replaced by intro video)
if [ ! -f /storage/.kodi/userdata/advancedsettings.xml ]; then
    echo '<advancedsettings><splash>false</splash></advancedsettings>' > /storage/.kodi/userdata/advancedsettings.xml
elif ! grep -q '<splash>' /storage/.kodi/userdata/advancedsettings.xml; then
    sed -i 's|</advancedsettings>|<splash>false</splash></advancedsettings>|' /storage/.kodi/userdata/advancedsettings.xml
fi

# Disable automatic addon updates (notify only), so Akasha OS remains in control
python3 - <<'PY'
import re
path = "/storage/.kodi/userdata/guisettings.xml"
try:
    with open(path, "r", encoding="utf-8") as f:
        data = f.read()
except FileNotFoundError:
    exit(0)
# general.addonupdates: 0=auto, 1=notify, 2=never
# addons.updatemode: 0=official, 1=any, 2=none
for sid, val in [("general.addonupdates", "1"), ("addons.updatemode", "2"), ("audiooutput.volumesteps", "90")]:
    if 'id="{}"'.format(sid) not in data:
        data = data.replace("</settings>", '    <setting id="{}">{}</setting>\n</settings>'.format(sid, val))
    else:
        data = re.sub(r'id="{}"[^>]*>[^<]*<'.format(sid), 'id="{}" default="true">{}<'.format(sid, val), data)
with open(path, "w", encoding="utf-8") as f:
    f.write(data)
PY

# Disable LibreELEC auto updates
cat > /storage/.config/akasha-os/libreelec-update-policy.txt <<'EOF'
LibreELEC auto updates are managed by Akasha OS.
Do not enable LibreELEC built-in auto update.
EOF

# Hostname
echo 'Akasha OS' > /storage/.cache/hostname

# Enable / disable services
systemctl daemon-reload
systemctl enable cec-tv.service cec-wakeup.service cec-wake-early.service \
                 splash-video.service splash-poweroff.service splash-reboot.service \
                 akasha-disable-official-updates.service wifi-silent-agent.service 2>/dev/null || true
systemctl disable wifi-watchdog.service 2>/dev/null || true

log "=== Akasha OS install complete ==="