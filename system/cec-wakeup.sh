#!/bin/sh
# CEC TV Wake on boot or after Kodi restart
# Wait for the CEC device to appear (up to ~15s)
for i in $(seq 1 30); do
    if [ -e /dev/cec0 ]; then
        break
    fi
    sleep 0.5
done

# Configure the adapter so the TV accepts our messages
cec-ctl -d0 --phys-addr 1.0.0.0 --osd-name Akasha --vendor-id 0x000c03 --playback --allow-unreg-fallback 2>/dev/null
sleep 0.5

cec-ctl -d0 --from 4 --report-physical-addr phys-addr=1.0.0.0,prim-devtype=4 --raw-msg 2>/dev/null
sleep 0.5
cec-ctl -d0 --from 4 --device-vendor-id vendor-id=0x000c03 --raw-msg 2>/dev/null
sleep 0.5
cec-ctl -d0 --from 4 --to 0 --image-view-on --raw-msg 2>/dev/null
sleep 0.5
cec-ctl -d0 --from 4 --active-source phys-addr=1.0.0.0 --raw-msg 2>/dev/null
