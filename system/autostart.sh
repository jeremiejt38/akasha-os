#!/bin/bash
# Attendre que le WiFi soit prêt et forcer la reconnexion si échec
sleep 10
WIFI_SERVICE=$(connmanctl services 2>/dev/null | grep 'Bbox-3AEEFA4E-5GHz' | awk '{print $NF}')
if [ -n "$WIFI_SERVICE" ]; then
    STATUS=$(connmanctl services $WIFI_SERVICE 2>/dev/null | grep 'State' | awk '{print $3}')
    if [ "$STATUS" != "ready" ] && [ "$STATUS" != "online" ]; then
        connmanctl connect $WIFI_SERVICE 2>/dev/null
    fi
fi
