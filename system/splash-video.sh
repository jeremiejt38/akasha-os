#!/bin/sh
# Akasha OS — Boot splash video (pre-Kodi, on framebuffer)
# Plays splash-intro.mp4 on the framebuffer and the matching
# splash-intro.wav (pre-extracted during install) via aplay.
VIDEO=/storage/.kodi/media/splash-intro.mp4
WAV=/storage/.kodi/media/splash-intro.wav
FFMPEG=/storage/ffmpeg
FB=/dev/fb0
AUDIO_DEV=default:CARD=vc4hdmi0
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

# Start audio in the background if a pre-extracted WAV exists
AUDIO_PID=""
if [ -f "$WAV" ] && aplay -l 2>/dev/null | grep -q vc4hdmi0; then
    aplay -D "$AUDIO_DEV" "$WAV" &
    AUDIO_PID=$!
    echo "Audio playback started (pid=$AUDIO_PID)"
fi

# Play video on framebuffer (no audio - that is handled by aplay)
$FFMPEG -re -i "$VIDEO" \
    -vf "scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2" \
    -pix_fmt rgb565le -f fbdev "$FB" \
    -an -loglevel warning

# Stop audio once the video is finished
if [ -n "$AUDIO_PID" ]; then
    kill "$AUDIO_PID" 2>/dev/null || true
    wait "$AUDIO_PID" 2>/dev/null || true
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