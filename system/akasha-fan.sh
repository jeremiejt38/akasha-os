#!/bin/sh
# Argon ONE fan curve daemon for Akasha OS.
# The case MCU lives on i2c-1 @ 0x1a and accepts a 0-100 duty write.
#
# Curve (anti-chatter revision): the Pi 4 idles at 46-48C under the
# performance governor, right at the old 48C start point -- the fan
# engaged, cooled below the 47C stop in seconds, and retriggered on
# the next poll (~3-30s bursts forever). Now:
#   - engages only above 55C *sustained* for START_HOLD polls (~16s),
#     so load transients never spin it up;
#   - stops only below 50C (5C hysteresis instead of 1C);
#   - once spinning, runs at least MIN_RUN polls (~60s) at MIN_PCT so
#     every engagement is a real cooling cycle, not a blip;
#   - 100% at 70C still applies instantly (no hold delay).
# MIN_PCT 20% is the lowest duty the Argon ONE blower spins reliably;
# below ~15% some units stall instead of turning.
# Writes are issued only when the duty changes (plus a periodic resend
# in case the MCU was power-cycled by a deep sleep or brown-out).
I2CSET=${AKASHA_FAN_I2CSET:-/storage/.kodi/addons/virtual.system-tools/bin/i2cset}
ADDR=0x1a
TEMP=${AKASHA_FAN_TEMP:-/sys/class/thermal/thermal_zone0/temp}
FAN_START=55000   # millidegrees: engage point (sustained) -> MIN_PCT
FAN_FULL=70000    # millidegrees: 100%
FAN_OFF=50000     # millidegrees: silence resumes below this
MIN_PCT=20
START_HOLD=8      # polls above FAN_START before engaging (~16s)
MIN_RUN=30        # polls of mandatory run once engaged (~60s)
POLL=${AKASHA_FAN_POLL:-2}
RESEND=150        # force a rewrite every RESEND*POLL = 5 min

[ -x "$I2CSET" ] || exit 0          # system-tools addon absent
[ -r "$TEMP" ] || exit 0

last=-1
tick=0
hot=0                             # consecutive polls above FAN_START
run=0                             # mandatory run-out countdown
while :; do
    t=$(cat "$TEMP" 2>/dev/null || echo 0)
    if [ "$t" -ge "$FAN_START" ]; then
        hot=$((hot + 1))
    else
        hot=0
    fi
    if [ "$t" -ge "$FAN_FULL" ]; then
        pct=100
        run=$MIN_RUN
    elif [ "$t" -ge "$FAN_START" ] \
            && { [ "$hot" -ge "$START_HOLD" ] || [ "$last" -ge "$MIN_PCT" ]; }; then
        # Sustained heat (or already spinning): follow the curve.
        pct=$((MIN_PCT + (t - FAN_START) * (100 - MIN_PCT) / (FAN_FULL - FAN_START)))
        run=$MIN_RUN
    elif [ "$run" -gt 0 ]; then
        pct=$MIN_PCT              # mandatory run-out at minimum duty
        run=$((run - 1))
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
