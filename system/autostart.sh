#!/bin/bash
# Désactiver le power save du WiFi (cause de déconnexions sur RPi 4)
sleep 10
if [ -e /sys/class/net/wlan0 ]; then
    iw dev wlan0 set power_save off 2>/dev/null || true
fi

# Marqueur de boot pour l'analyseur de performances : le service Kodi
# démarre plus tard, ce point fixe le début de la fenêtre d'analyse.
mkdir -p /storage/.config/akasha-os/perf
echo "{\"ts\":$(date +%s),\"type\":\"boot\"}" >> /storage/.config/akasha-os/perf/metrics.jsonl
