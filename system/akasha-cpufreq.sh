#!/bin/sh
# cpufreq tuning for the Akasha OS appliance.
# Governor `performance`: the UI must react on the FIRST input, not after a
# sampling window detects a burst -- an ondemand ramp (even at 200 ms)
# leaves the first presses on the low clocks. Measured on the Pi 4: 60 s
# pinned at 2 GHz idle sits at ~45 C, below the fan's 48 C threshold, so
# the always-on rail costs nothing in thermals or noise at rest, and under
# real load the governor would have boosted to 2 GHz anyway.
echo performance > /sys/devices/system/cpu/cpu0/cpufreq/scaling_governor 2>/dev/null
