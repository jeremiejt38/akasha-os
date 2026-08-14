#!/bin/bash
# Désactiver le power save du WiFi (cause de déconnexions sur RPi 4)
sleep 10
if [ -e /sys/class/net/wlan0 ]; then
    iw dev wlan0 set power_save off 2>/dev/null || true
fi
