#!/usr/bin/env bash
# Akasha OS (Pi) helper: capture via PixelCamera HTTP endpoint + navigate via kodi-send.
# "Camera" note: the physical Pixel cam was replaced upstream by the Kodi-screenshot
# endpoint (atlas/pixelcamera). akasha-camera/ mirrors akasha-direct/ — same source.
# Usage:
#   pi.sh cap <screen> <state_action>  → PNG → akasha-direct/<screen>/ + akasha-camera/<screen>/ + INDEX.md
#   pi.sh key <action>                 → kodi-send action (Left/Right/Up/Down/Select/Back/...)
#   pi.sh ssh "<cmd>"                  → raw ssh on the Pi
set -euo pipefail

PI="${PI_HOST:-root@192.168.3.77}"
CAM="${PI_CAM:-http://192.168.3.77:8088/frame.jpg}"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
INDEX="$ROOT/INDEX.md"

cmd="${1:-}"; shift || true
case "$cmd" in
  cap)
    screen="${1:?screen dir}"; label="${2:?state_action label}"
    for base in akasha-direct akasha-camera; do
      dir="$ROOT/$base/$screen"; mkdir -p "$dir"
      n=$(find "$dir" -name '*.png' | wc -l); n=$(printf "%03d" $((n+1)))
      ts=$(date +%H%M%S)
      curl -s -m 20 "$CAM" -o "$dir/${label}_${n}.png"
    done
    echo "| \`akasha-direct/$screen/${label}_${n}.png\` | $screen | $label | $ts | pi |" >> "$INDEX"
    echo "captured: $dir/${label}_${n}.png"
    ;;
  key) ssh -o ConnectTimeout=5 "$PI" "kodi-send --action=\"$1\"" ;;
  ssh) ssh -o ConnectTimeout=5 "$PI" "$*" ;;
  *) echo "unknown cmd: $cmd" >&2; exit 2 ;;
esac
