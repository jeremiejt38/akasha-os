#!/bin/bash
# Envoie CEC Standby à la TV avant extinction
cec-ctl -d0 --from 4 --report-physical-addr phys-addr=1.0.0.0,prim-devtype=4 --raw-msg 2>/dev/null
sleep 0.5
cec-ctl -d0 --from 4 --device-vendor-id vendor-id=0x000c03 --raw-msg 2>/dev/null
sleep 0.5
cec-ctl -d0 --from 4 --to 0 --standby --raw-msg 2>/dev/null
sleep 1
