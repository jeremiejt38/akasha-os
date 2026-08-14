#!/bin/sh
# Display a splash image on the Linux framebuffer as fast as possible.
# Uses a pre-converted raw rgb565 file if available, otherwise falls back to ffmpeg.
IMAGE="${1:-/storage/.kodi/media/splash.png}"
STANDBY="${2:-0}"
FFMPEG=/storage/ffmpeg
FB=/dev/fb0

RAW=""
if [ -f "$IMAGE" ]; then
    # Look for a pre-converted raw framebuffer dump next to the PNG
    case "$IMAGE" in
        *.png) RAW="${IMAGE%.png}.raw" ;;
    esac
fi

if [ -n "$RAW" ] && [ -f "$RAW" ]; then
    # Direct write is nearly instantaneous (1920x1080 rgb565le, 16bpp)
    cat "$RAW" > "$FB"
elif [ -f "$IMAGE" ] && [ -x "$FFMPEG" ]; then
    # Fallback to ffmpeg for legacy/no-raw deployments
    $FFMPEG -hide_banner -loglevel quiet -i "$IMAGE" \
        -vf "scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2" \
        -pix_fmt rgb565le -f fbdev "$FB" 2>/dev/null
fi

# Keep image on screen for a moment so it is visible during transition
sleep 2

# For poweroff, turn the TV off via CEC as the very last UI-visible action
if [ "$STANDBY" = "1" ] && [ -x /storage/.config/cec-standby.sh ]; then
    /storage/.config/cec-standby.sh
fi
