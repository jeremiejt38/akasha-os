#!/bin/bash
# Envoie CEC Standby à la TV avant extinction
# Configure CEC adapter as a playback device so the TV accepts our messages
cec-ctl -d0 --phys-addr 1.0.0.0 --osd-name Akasha --vendor-id 0x000c03 --playback --allow-unreg-fallback 2>/dev/null
sleep 0.5
# Claim/announce source on the CEC bus
cec-ctl -d0 --from 4 --report-physical-addr phys-addr=1.0.0.0,prim-devtype=4 --raw-msg 2>/dev/null
sleep 0.5
cec-ctl -d0 --from 4 --device-vendor-id vendor-id=0x000c03 --raw-msg 2>/dev/null
sleep 0.5
# Ensure we are the active source, then ask the TV to standby
cec-ctl -d0 --from 4 --active-source phys-addr=1.0.0.0 --raw-msg 2>/dev/null
sleep 0.5
cec-ctl -d0 --from 4 --to 0 --standby --raw-msg 2>/dev/null
# Let the TV process the standby before cutting power
sleep 4
