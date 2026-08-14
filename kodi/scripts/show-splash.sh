#!/bin/sh
# Display a PNG splash image on the Linux framebuffer
IMAGE="${1:-/storage/.kodi/media/splash.png}"
STANDBY="${2:-0}"
FFMPEG=/storage/ffmpeg
FB=/dev/fb0

if [ ! -f "$IMAGE" ] || [ ! -f "$FFMPEG" ]; then
    exit 0
fi

# Scale to 1920x1080 rgb565le and push to framebuffer
$FFMPEG -hide_banner -loglevel quiet -i "$IMAGE" \
    -vf "scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2" \
    -pix_fmt rgb565le -f fbdev "$FB" 2>/dev/null

# Keep image on screen for a moment so it is visible during transition
sleep 2

# For poweroff, turn the TV off via CEC as the very last UI-visible action
if [ "$STANDBY" = "1" ] && [ -x /storage/.config/cec-standby.sh ]; then
    /storage/.config/cec-standby.sh
fi
