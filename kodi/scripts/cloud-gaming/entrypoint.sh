#!/bin/bash
# Lancer un serveur X minimal
Xorg :0 -nolisten tcp &
sleep 2
export DISPLAY=:0

# Window manager minimal
matchbox-window-manager -use_titlebar no &
sleep 1

# Lancer Chromium avec les arguments passés
exec 
