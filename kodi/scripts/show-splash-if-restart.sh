#!/bin/sh
# ExecStartPre helper: only show the reboot splash if Kodi is being restarted
# (not at cold boot). The Akasha settings addon creates this flag.
FLAG=/tmp/.kodi-restart
if [ -f "$FLAG" ]; then
    rm -f "$FLAG"
    exec /storage/.kodi/scripts/show-splash.sh /storage/.kodi/media/splash-reboot.png
fi
