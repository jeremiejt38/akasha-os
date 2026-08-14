#!/bin/sh
# Akasha OS — Boot splash video (video + audio + hold last frame)
VIDEO=/storage/.kodi/media/splash-intro.mp4
FFMPEG=/storage/ffmpeg
FB=/dev/fb0
AUDIO_DEV=hdmi:CARD=vc4hdmi0,DEV=0
LAST_FRAME=/storage/.config/splash.jpg
LOG=/storage/splash-video.log

exec >$LOG 2>&1
set -x

echo "=== Akasha OS splash video start: $(date) ==="

if [ ! -f "$VIDEO" ] || [ ! -f "$FFMPEG" ]; then
    echo "Missing video or ffmpeg"; exit 0
fi

# Wait for ALSA HDMI audio device (up to 10s)
for i in 1 2 3 4 5 6 7 8 9 10; do
    if aplay -l 2>/dev/null | grep -q vc4hdmi0; then
        echo "ALSA vc4hdmi0 ready"; break
    fi
    sleep 1
done

# Wait for DRM/HDMI to be ready (up to 15s) so the video is actually visible
for i in $(seq 1 30); do
    if [ -r /sys/class/drm/card0-HDMI-A-1/status ] && \
       [ -r /sys/class/drm/card0-HDMI-A-1/enabled ]; then
        status=$(cat /sys/class/drm/card0-HDMI-A-1/status 2>/dev/null)
        enabled=$(cat /sys/class/drm/card0-HDMI-A-1/enabled 2>/dev/null)
        if [ "$status" = "connected" ] && [ "$enabled" = "enabled" ]; then
            echo "DRM HDMI ready (status=$status enabled=$enabled)"; break
        fi
        echo "DRM not ready yet (status=$status enabled=$enabled)"
    fi
    sleep 0.5
done

# Small extra wait for the TV/PHY to fully display
sleep 2

echo "Framebuffer info:"
cat /sys/class/graphics/fb0/virtual_size /sys/class/graphics/fb0/bits_per_pixel 2>/dev/null || true

# Play video on framebuffer + audio on HDMI
$FFMPEG -re -i "$VIDEO" \
    -vf "scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2" \
    -pix_fmt rgb565le -f fbdev "$FB" \
    -f alsa "$AUDIO_DEV" \
    -loglevel warning

# If audio failed, retry video-only
if [ $? -ne 0 ]; then
    echo "Audio path failed, retrying video-only"; sleep 1
    $FFMPEG -re -i "$VIDEO" \
        -vf "scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2" \
        -pix_fmt rgb565le -f fbdev "$FB" \
        -an -loglevel warning
fi

# Display last frame (static image) and hold until Kodi takes over
if [ -f "$LAST_FRAME" ]; then
    echo "Displaying last frame"; sleep 1
    $FFMPEG -i "$LAST_FRAME" \
        -vf "scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2" \
        -pix_fmt rgb565le -f fbdev "$FB" \
        -loglevel warning
fi

echo "=== Akasha OS splash video end: $(date) ==="
