#!/bin/sh
# Argon ONE fan curve daemon for Akasha OS.
# The case MCU lives on i2c-1 @ 0x1a and accepts a 0-100 duty write.
# Curve: stopped below 48C, 30% at 48C, linear to 100% at 70C, with a
# 1C hysteresis band so the fan cannot chatter at the start edge.
# Writes are issued only when the duty changes (plus a periodic resend
# in case the MCU was power-cycled by a deep sleep or brown-out).
I2CSET=${AKASHA_FAN_I2CSET:-/storage/.kodi/addons/virtual.system-tools/bin/i2cset}
ADDR=0x1a
TEMP=${AKASHA_FAN_TEMP:-/sys/class/thermal/thermal_zone0/temp}
FAN_START=48000   # millidegrees: first cooling point -> 30%
FAN_FULL=70000    # millidegrees: 100%
FAN_OFF=47000     # millidegrees: silence resumes below this
MIN_PCT=30
POLL=2
RESEND=150        # force a rewrite every RESEND*POLL = 5 min

[ -x "$I2CSET" ] || exit 0          # system-tools addon absent
[ -r "$TEMP" ] || exit 0

last=-1
tick=0
while :; do
    t=$(cat "$TEMP" 2>/dev/null || echo 0)
    if [ "$t" -ge "$FAN_FULL" ]; then
        pct=100
    elif [ "$t" -ge "$FAN_START" ]; then
        pct=$((MIN_PCT + (t - FAN_START) * (100 - MIN_PCT) / (FAN_FULL - FAN_START)))
    elif [ "$t" -lt "$FAN_OFF" ]; then
        pct=0
    elif [ "$last" -lt 0 ]; then
        pct=0                     # hysteresis band, cold start: stay off
    else
        pct=$last                 # hysteresis band: hold current duty
    fi
    if [ "$pct" != "$last" ] || [ "$tick" -ge "$RESEND" ]; then
        "$I2CSET" -y 1 "$ADDR" "$pct" >/dev/null 2>&1
        last=$pct
        tick=0
    fi
    tick=$((tick + 1))
    sleep "$POLL"
done
