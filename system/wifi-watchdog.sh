#!/bin/bash
# wifi-watchdog.sh — Akasha OS WiFi auto-reconnect watchdog
#
# Monitors WiFi connectivity. If disconnected, removes the broken
# profile and recreates it with the stored passphrase. Logs every
# reconnection event to /storage/.config/wifi-watchdog.log.
#
# Runs as a systemd service (loop with sleep interval).

SSID="Bbox-3AEEFA4E-5GHz"
PASSPHRASE="k6Vr76JGnxPQZH7ZHc"
CONNMAN_SVC_ID="wifi_dca632af47bf_42626f782d33414545464134452d3547487a_managed_psk"
LOG="/storage/.config/wifi-watchdog.log"
CHECK_INTERVAL=10  # seconds between checks
MAX_RETRIES=5

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

write_connman_config() {
    # Write connman config with passphrase — atomic, so connman can
    # pick it up immediately when the service reappears after scan.
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

force_reconnect() {
    log_event "DISCONNECT detected — starting reconnection"

    local svc
    svc=$(get_wifi_service)

    # Step 1: Write config FIRST (before removing anything), so the
    # passphrase is ready as soon as connman re-discovers the network.
    write_connman_config
    log_event "Config pre-written with passphrase"

    # Step 2: Remove broken profile and immediately reconnect
    if [ -n "$svc" ]; then
        log_event "Removing broken profile: $svc"
        connmanctl disconnect "$svc" 2>/dev/null
        connmanctl remove "$svc" 2>/dev/null
        sleep 1
    fi

    # Step 3: Enable WiFi, scan, and reconnect fast
    connmanctl enable wifi 2>/dev/null
    connmanctl scan wifi 2>/dev/null
    sleep 2

    # Re-write config (remove may have cleaned it)
    write_connman_config

    # Find the service again after scan
    svc=$(get_wifi_service)
    if [ -z "$svc" ]; then
        # Second scan attempt
        connmanctl scan wifi 2>/dev/null
        sleep 2
        svc=$(get_wifi_service)
    fi
    if [ -z "$svc" ]; then
        log_event "ERROR: SSID '$SSID' not found after scan"
        return 1
    fi

    # Try to connect (fast retries)
    local retry=0
    while [ $retry -lt $MAX_RETRIES ]; do
        connmanctl connect "$svc" 2>/dev/null
        sleep 3

        if is_connected; then
            local ip
            ip=$(connmanctl services "$svc" 2>/dev/null | grep 'IPv4 =' | grep -oP 'Address=\K[0-9.]+')
            log_event "RECONNECTED successfully (IP: ${ip:-unknown}, attempt $((retry+1)))"
            return 0
        fi

        retry=$((retry + 1))
        log_event "Retry $retry/$MAX_RETRIES..."
        sleep 1
    done

    log_event "ERROR: Failed to reconnect after $MAX_RETRIES attempts"
    return 1
}

# --- Main loop ---
log_event "WiFi watchdog started"

# Initial wait for boot to settle
sleep 5

while true; do
    if ! is_connected; then
        force_reconnect
    fi
    sleep "$CHECK_INTERVAL"
done
