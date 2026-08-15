#!/usr/bin/env python3
"""Patch Arctic Horizon 2 Includes_Dimensions.xml so the native context menu
box (Dimension_Context) is tall enough for the Akasha Guide menu, which has
more items (7) than a typical Kodi context menu. This include is shared by
all native context menus in Kodi, so the extra height applies everywhere,
but simply leaves more empty space at the bottom for menus with fewer items.
"""
import os
import re
import sys

SKIN_DIR = sys.argv[1] if len(sys.argv) > 1 else "/storage/.kodi/addons/skin.arctic.horizon.2"
NEW_HEIGHT = "820"


def patch(path):
    dims_xml = os.path.join(path, "1080i", "Includes_Dimensions.xml")
    if not os.path.isfile(dims_xml):
        print("Includes_Dimensions.xml not found at {}".format(dims_xml))
        return 1

    with open(dims_xml, "r", encoding="utf-8") as f:
        data = f.read()

    pattern = re.compile(
        r'(<include name="Dimension_Context">.*?<height>)\d+(\.\d+)?(</height>)',
        re.DOTALL,
    )

    if not pattern.search(data):
        print("Dimension_Context include not found, aborting")
        return 1

    match = pattern.search(data)
    if match.group(0).split('<height>')[1].split('</height>')[0] == NEW_HEIGHT:
        print("Includes_Dimensions.xml already patched.")
        return 0

    new_data = pattern.sub(r"\g<1>{}\g<3>".format(NEW_HEIGHT), data, count=1)

    with open(dims_xml, "w", encoding="utf-8") as f:
        f.write(new_data)
    print("Patched Dimension_Context height -> {}".format(NEW_HEIGHT))
    return 0


if __name__ == "__main__":
    sys.exit(patch(SKIN_DIR))
