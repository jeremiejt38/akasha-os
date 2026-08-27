#!/bin/bash
# wifi-watchdog.sh — Akasha OS WiFi auto-reconnect watchdog
#
# Monitors WiFi connectivity. If disconnected, ensures the connman
# config has the correct passphrase and attempts to reconnect.
# NEVER removes/deletes profiles — only writes the passphrase and
# calls connect.
#
# Logs every reconnection event to /storage/.config/wifi-watchdog.log.
# Runs as a systemd service (loop with sleep interval).

SSID="Bbox-3AEEFA4E-5GHz"
PASSPHRASE="$(awk -F= '/^Passphrase=/{print substr($0, index($0, "=") + 1); exit}' /storage/.cache/connman/wifi.config 2>/dev/null)"
CONNMAN_SVC_ID="wifi_dca632af47bf_42626f782d33414545464134452d3547487a_managed_psk"
LOG="/storage/.config/wifi-watchdog.log"
CHECK_INTERVAL=10  # seconds between checks
MAX_RETRIES=5
RECONNECT_COOLDOWN=60  # seconds to wait after a reconnect before checking again

log_event() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') $1" >> "$LOG"
}

get_wifi_service() {
    connmanctl services 2>/dev/null | grep "$SSID" | awk '{print $NF}'
}

get_service_state() {
    local svc="$1"
    connmanctl services "$svc" 2>/dev/null | grep '  State' | head -1 | awk '{print $3}'
}

is_connected() {
    local svc
    svc=$(get_wifi_service)
    if [ -z "$svc" ]; then
        return 1
    fi
    local state
    state=$(get_service_state "$svc")
    [ "$state" = "ready" ] || [ "$state" = "online" ]
}

is_ethernet_connected() {
    [ "$(cat /sys/class/net/eth0/carrier 2>/dev/null)" = "1" ]
}

ensure_passphrase() {
    [ -n "$PASSPHRASE" ] || return 1
    # Ensure the connman config exists with the correct passphrase.
    # Does NOT remove anything — only creates/overwrites the settings file.
    local svc_dir="/storage/.cache/connman/${CONNMAN_SVC_ID}"
    mkdir -p "$svc_dir"
    cat > "${svc_dir}/settings" << EOF
[${CONNMAN_SVC_ID}]
Name=${SSID}
SSID=42626f782d33414545464134452d3547487a
Frequency=0
Favorite=true
AutoConnect=true
Modified=$(date -u '+%Y-%m-%dT%H:%M:%SZ')
Passphrase=${PASSPHRASE}
IPv4.method=dhcp
IPv6.method=off
IPv6.privacy=prefered
EOF
}

try_reconnect() {
    log_event "DISCONNECT detected — attempting reconnection"

    # Step 1: Make sure the passphrase is in the config
    if ! ensure_passphrase; then
        log_event "ERROR: No passphrase found in connman provisioning"
        return 1
    fi
    log_event "Passphrase ensured in connman config"

    # Step 2: Enable WiFi and scan (non-destructive)
    connmanctl enable wifi 2>/dev/null
    connmanctl scan wifi 2>/dev/null
    sleep 3

    # Step 3: Find the service
    local svc
    svc=$(get_wifi_service)
    if [ -z "$svc" ]; then
        connmanctl scan wifi 2>/dev/null
        sleep 3
        svc=$(get_wifi_service)
    fi
    if [ -z "$svc" ]; then
        log_event "ERROR: SSID '$SSID' not found after scan"
        return 1
    fi

    # Step 4: Try to connect (with patience between retries)
    local retry=0
    while [ $retry -lt $MAX_RETRIES ]; do
        connmanctl connect "$svc" 2>/dev/null
        sleep 5

        if is_connected; then
            local ip
            ip=$(connmanctl services "$svc" 2>/dev/null | grep 'IPv4 =' | grep -oP 'Address=\K[0-9.]+')
            log_event "RECONNECTED successfully (IP: ${ip:-unknown}, attempt $((retry+1)))"
            return 0
        fi

        retry=$((retry + 1))
        log_event "Retry $retry/$MAX_RETRIES..."
        sleep 5
    done

    log_event "ERROR: Failed to reconnect after $MAX_RETRIES attempts"
    return 1
}

# --- Main loop ---
log_event "WiFi watchdog started"

# Initial wait for boot to settle
sleep 15

while true; do
    if ! is_ethernet_connected && ! is_connected; then
        try_reconnect
        # Cooldown after reconnect attempt to avoid fighting with Kodi
        sleep "$RECONNECT_COOLDOWN"
    fi
    sleep "$CHECK_INTERVAL"
done
