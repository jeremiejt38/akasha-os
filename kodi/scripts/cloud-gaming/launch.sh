#!/bin/bash
# Cloud Gaming Launcher - Lance Chromium en kiosk mode
# Usage: launch.sh <url> [nom]
URL="${1:-https://play.geforcenow.com}"
NAME="${2:-Cloud Gaming}"
CONTAINER_NAME="cloud-gaming-session"

# Arrêter Kodi pour libérer la RAM
systemctl stop kodi
sleep 2

# Watchdog manette : maintenir le bouton Guide/Xbox 5s force la sortie
# (utile quand il n'y a pas de clavier pour faire Alt+F4)
python3 /storage/.kodi/scripts/cloud-gaming/guide_watchdog.py "$CONTAINER_NAME" &
WATCHDOG_PID=$!

# Lancer Chromium dans Docker
docker run --rm -it --name "$CONTAINER_NAME"   --privileged   --network host   -v /tmp:/tmp   -v /dev:/dev   -v /run/udev:/run/udev   -v /storage/.config/cloud-gaming:/data   -e DISPLAY=:0   -e XDG_RUNTIME_DIR=/tmp   akasha-chromium   chromium-browser     --no-sandbox     --kiosk     --start-fullscreen     --disable-infobars     --disable-session-crashed-bubble     --noerrdialogs     --user-data-dir=/data     --enable-features=VaapiVideoDecoder     --use-gl=egl     --enable-gpu-rasterization     --window-size=1920,1080     ""

# Le watchdog n'est plus utile une fois Chromium fermé
kill "$WATCHDOG_PID" 2>/dev/null

# Relancer Kodi
systemctl start kodi
