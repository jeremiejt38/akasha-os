FROM arm32v7/debian:bookworm-slim

RUN apt-get update && apt-get install -y --no-install-recommends     chromium     chromium-sandbox     libgl1-mesa-dri     libegl1-mesa     libgles2-mesa     xorg     xdotool     matchbox-window-manager     dbus-x11     pulseaudio     alsa-utils     libasound2     fonts-liberation     ca-certificates     && rm -rf /var/lib/apt/lists/*

# Script d'entrée qui lance X + Chromium
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]
