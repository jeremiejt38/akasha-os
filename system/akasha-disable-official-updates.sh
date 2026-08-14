#!/bin/sh
# Disable LibreELEC built-in auto/manaul update mechanism.
# Run as a systemd one-shot before Kodi so the LibreELEC Settings addon
# sees an empty/disabled update channel.

set -e

# Touch the kernel/update-module flag that LibreELEC checks for.
# This is the most reliable way to prevent the update service from
# downloading or flashing anything.
touch /dev/.update_disabled

# Best-effort: write an empty/fake update configuration to LibreELEC settings
# so the UI does not show or suggest an official update.
LE_SETTINGS=/storage/.kodi/userdata/addon_data/service.libreelec.settings/oe_settings.xml

if [ -f "$LE_SETTINGS" ]; then
    # Ensure the <libreelec> block exists and contains update=manual
    # Use a Python one-liner to avoid sed/XML issues.
    python3 - <<'PY'
import xml.etree.ElementTree as ET
import os

path = "/storage/.kodi/userdata/addon_data/service.libreelec.settings/oe_settings.xml"
if not os.path.exists(path):
    exit(0)

try:
    tree = ET.parse(path)
except ET.ParseError:
    exit(0)

root = tree.getroot()
libreelec = root.find("settings/libreelec")
if libreelec is None:
    settings = root.find("settings")
    if settings is None:
        settings = ET.SubElement(root, "settings")
    libreelec = settings.find("libreelec")
    if libreelec is None:
        libreelec = ET.SubElement(settings, "libreelec")

# Set values that tell LibreELEC to not check/download updates.
def set_text(tag, text):
    el = libreelec.find(tag)
    if el is None:
        el = ET.SubElement(libreelec, tag)
    el.text = text

set_text("AutoUpdate", "manual")
set_text("UpdateNotify", "false")
set_text("Channel", "CustomChannel1")
set_text("CustomChannel1", "http://127.0.0.1/akasha-os-updates")

tree.write(path, encoding="UTF-8", xml_declaration=True)
PY
fi