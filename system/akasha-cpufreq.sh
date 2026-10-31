#!/bin/sh
# cpufreq tuning for the Akasha OS appliance.
# Ondemand, but a 1 s sampling window at an 80% busy threshold: the 2 GHz
# rail only wakes on a demand that is both strong AND lasting, so UI
# blips, thumbnail decodes and short I/O flurries stay on the low clocks.
# Down-scaling keeps a ~3 s hysteresis (3 low-load windows) to avoid
# flapping when a video's decode/load pattern is bursty.
OD=/sys/devices/system/cpu/cpufreq/ondemand
[ -d "$OD" ] || exit 0

echo ondemand > /sys/devices/system/cpu/cpu0/cpufreq/scaling_governor 2>/dev/null
echo 80       > "$OD/up_threshold"
echo 1000000  > "$OD/sampling_rate"         # microseconds: 1 s window
echo 3        > "$OD/sampling_down_factor"  # ~3 s before relaxing
echo 1        > "$OD/io_is_busy"            # I/O wait counts as busy
