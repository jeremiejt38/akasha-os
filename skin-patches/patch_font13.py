#!/usr/bin/env python3
"""Patch Arctic Horizon 2 Font.xml so font13 (used by Kodi's native context
menu -- e.g. the Akasha Guide menu -- and other unstyled dialogs) uses
Montserrat Regular instead of RobotoCondensed-Regular, for visual coherence
with the "Akasha OS" wordmark (a thin/geometric font)."""
import os
import re
import shutil
import sys

SKIN_DIR = sys.argv[1] if len(sys.argv) > 1 else "/storage/.kodi/addons/skin.arctic.horizon.2"
FONT_XML = os.path.join(SKIN_DIR, "1080i", "Font.xml")
FONT_NAME = "Montserrat-Regular.ttf"


def _copy_font(path):
    src = os.path.join(os.path.dirname(os.path.dirname(sys.argv[0])), 'kodi', 'media', 'fonts', FONT_NAME)
    if not os.path.isfile(src):
        src = os.path.join(path, 'fonts', FONT_NAME)
    dst = os.path.join(path, 'fonts', FONT_NAME)
    if os.path.isfile(src) and src != dst:
        shutil.copy(src, dst)
        return True
    return os.path.isfile(dst)


def patch(path):
    font_xml = os.path.join(path, "1080i", "Font.xml")
    if not os.path.isfile(font_xml):
        print("Font.xml not found at {}".format(font_xml))
        return 1

    if not _copy_font(path):
        print("Montserrat-Regular.ttf not found, aborting")
        return 1

    with open(font_xml, "r", encoding="utf-8") as f:
        data = f.read()

    if "Montserrat-Regular.ttf" in data:
        print("Font.xml already patched with Montserrat.")
        return 0

    pattern = re.compile(
        r"(<font>\s*<name>font13</name>\s*<filename>)[^<]+(</filename>)"
    )
    new_data, count = pattern.subn(r"\g<1>{}\g<2>".format(FONT_NAME), data)

    if count == 0:
        print("font13 definition not found, aborting")
        return 1

    with open(font_xml, "w", encoding="utf-8") as f:
        f.write(new_data)
    print("Patched Font.xml: font13 -> {} ({} occurrence(s))".format(FONT_NAME, count))
    return 0


if __name__ == "__main__":
    sys.exit(patch(SKIN_DIR))
