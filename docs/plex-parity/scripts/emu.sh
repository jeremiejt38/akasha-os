#!/usr/bin/env bash
# Emulator helper: capture, navigate, dump UI on the Android TV emulator.
# Usage:
#   emu.sh cap <screen> <state_action>   → PNG + uiautomator XML → reference/<screen>/ + INDEX.md line
#   emu.sh key <keyevent>                → send key (DPAD_UP/DOWN/LEFT/RIGHT/CENTER/BACK/HOME/MENU)
#   emu.sh tap <x> <y>
#   emu.sh text "foo"
#   emu.sh rec <name> <seconds>          → screenrecord → reference/_video/<name>.mp4
#   emu.sh focus                         → print current focused window/app
set -euo pipefail

ADB="${ANDROID_HOME:-$HOME/Android/Sdk}/platform-tools/adb -s emulator-5554"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
INDEX="$ROOT/INDEX.md"

cmd="${1:-}"; shift || true
case "$cmd" in
  cap)
    screen="${1:?screen dir}"; label="${2:?state_action label}"
    dir="$ROOT/reference/$screen"; mkdir -p "$dir"
    n=$(find "$dir" -name '*.png' | wc -l); n=$(printf "%03d" $((n+1)))
    ts=$(date +%H%M%S)
    png="$dir/${label}_${n}.png"; xml="$dir/${label}_${n}.xml"
    $ADB exec-out screencap -p > "$png"
    $ADB shell uiautomator dump /sdcard/ui_dump.xml >/dev/null 2>&1 || true
    $ADB exec-out cat /sdcard/ui_dump.xml > "$xml" 2>/dev/null || true
    focus=$($ADB shell dumpsys window 2>/dev/null | grep -oE 'mCurrentFocus=Window\{[^ ]+ [^ ]+' | head -1 | sed 's/.* //' || true)
    echo "| \`reference/$screen/${label}_${n}.png\` | $screen | $label | $ts | focus=$focus |" >> "$INDEX"
    echo "captured: $png"
    ;;
  key)  $ADB shell input keyevent "$1" ;;
  tap)  $ADB shell input tap "$1" "$2" ;;
  text) $ADB shell input text "${1// /%s}" ;;
  rec)
    name="${1:?name}"; secs="${2:-15}"; mkdir -p "$ROOT/reference/_video"
    $ADB shell "screenrecord --time-limit $secs /sdcard/$name.mp4" && \
    $ADB pull "/sdcard/$name.mp4" "$ROOT/reference/_video/$name.mp4" && \
    $ADB shell rm "/sdcard/$name.mp4"
    echo "video: $ROOT/reference/_video/$name.mp4"
    ;;
  focus)
    $ADB shell dumpsys window | grep -iE "currentFocus|mFocusedApp" | head -3
    ;;
  *) echo "unknown cmd: $cmd" >&2; exit 2 ;;
esac
