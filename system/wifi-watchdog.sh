#!/bin/bash
# wifi-watchdog.sh — Akasha OS WiFi auto-reconnect watchdog
#
# Monitors WiFi connectivity. If Ethernet is down AND the configured
# (connman "Favorite") WiFi network is not connected, attempts to
# reconnect to it. Network-agnostic: the service is discovered
# dynamically from connman's settings, nothing is hardcoded.
#
# NEVER removes/deletes profiles — at most it appends a missing
# Passphrase line (recovered from wifi.config) to an existing profile.
#
# Logs every reconnection event to /storage/.config/wifi-watchdog.log.
# Runs as a systemd service (loop with sleep interval).

CONNMAN_DIR="/storage/.cache/connman"
WIFI_CONFIG="$CONNMAN_DIR/wifi.config"
LOG="/storage/.config/wifi-watchdog.log"
CHECK_INTERVAL=10  # seconds between checks
MAX_RETRIES=5
RECONNECT_COOLDOWN=60  # seconds to wait after a reconnect before checking again

log_event() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') $1" >> "$LOG"
}

# Prints the connman service id of the Favorite WiFi profile (the one the
# user actually configured), falling back to any known wifi_* service.
get_favorite_wifi_service() {
    local d
    for d in "$CONNMAN_DIR"/wifi_*; do
        [ -f "$d/settings" ] || continue
        if grep -q 'Favorite=true' "$d/settings" 2>/dev/null; then
            basename "$d"
            return 0
        fi
    done
    connmanctl services 2>/dev/null | awk '/wifi_.*managed/ {print $NF; exit}'
    return 1
}

service_name() {
    grep -m1 '^Name=' "$CONNMAN_DIR/$1/settings" 2>/dev/null | cut -d= -f2-
}

get_service_state() {
    connmanctl services "$1" 2>/dev/null | grep '  State' | head -1 | awk '{print $3}'
}

is_connected() {
    local svc="$1"
    [ -n "$svc" ] || return 1
    local state
    state=$(get_service_state "$svc")
    [ "$state" = "ready" ] || [ "$state" = "online" ]
}

is_ethernet_connected() {
    [ "$(cat /sys/class/net/eth0/carrier 2>/dev/null)" = "1" ]
}

# If the favorite profile lost its Passphrase, restore it from wifi.config.
ensure_passphrase() {
    local svc="$1"
    local settings="$CONNMAN_DIR/$svc/settings"
    [ -f "$settings" ] || return 0
    grep -q '^Passphrase=' "$settings" && return 0
    local pass
    pass="$(awk -F= '/^Passphrase=/{print substr($0, index($0, "=") + 1); exit}' "$WIFI_CONFIG" 2>/dev/null)"
    [ -n "$pass" ] || return 1
    echo "Passphrase=$pass" >> "$settings"
    log_event "Passphrase restored into $svc from wifi.config"
}

try_reconnect() {
    local svc
    svc=$(get_favorite_wifi_service)
    if [ -z "$svc" ]; then
        log_event "ERROR: no WiFi service known to connman"
        return 1
    fi
    local name
    name="$(service_name "$svc")"
    log_event "DISCONNECT detected — attempting reconnection to '${name:-$svc}'"

    ensure_passphrase "$svc"

    connmanctl enable wifi 2>/dev/null
    connmanctl scan wifi 2>/dev/null
    sleep 3

    local retry=0
    while [ $retry -lt $MAX_RETRIES ]; do
        timeout 20 connmanctl connect "$svc" 2>/dev/null
        sleep 5

        if is_connected "$svc"; then
            local ip
            ip=$(connmanctl services "$svc" 2>/dev/null | grep 'IPv4 =' | grep -o 'Address=[0-9.]*' | cut -d= -f2)
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
    if ! is_ethernet_connected && ! is_connected "$(get_favorite_wifi_service)"; then
        try_reconnect
        # Cooldown after reconnect attempt to avoid fighting with Kodi
        sleep "$RECONNECT_COOLDOWN"
    fi
    sleep "$CHECK_INTERVAL"
done
