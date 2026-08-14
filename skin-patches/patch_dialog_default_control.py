#!/usr/bin/env python3
"""Patch Arctic Horizon 2 DialogConfirm.xml so the default focused control
is the "Yes" / OK button. This lets a gamepad "A" button close the
post-reboot success and changelog dialogs."""
import os
import re
import sys

SKIN_DIR = sys.argv[1] if len(sys.argv) > 1 else "/storage/.kodi/addons/skin.arctic.horizon.2"
DIALOG_CONFIRM = os.path.join(SKIN_DIR, "1080i", "DialogConfirm.xml")

if not os.path.exists(DIALOG_CONFIRM):
    print("DialogConfirm.xml not found, skipping")
    sys.exit(0)

with open(DIALOG_CONFIRM, "r") as f:
    data = f.read()

# Add defaultcontrol right after <window> if not already present
if re.search(r"<defaultcontrol", data, re.IGNORECASE):
    print("DialogConfirm.xml already has defaultcontrol")
    sys.exit(0)

data = re.sub(r"(<window>\s*)", r"\1\n    <defaultcontrol always=\"true\">11</defaultcontrol>", data, count=1)

with open(DIALOG_CONFIRM, "w") as f:
    f.write(data)

print("Patched DialogConfirm.xml defaultcontrol to button 11")