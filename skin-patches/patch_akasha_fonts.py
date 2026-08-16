#!/usr/bin/env python3
"""Register the Montserrat font (used by the Akasha Guide custom XML window,
guide.style=2) in the Arctic Horizon 2 skin's Font.xml.

Kodi 21 (Omega) does not yet support addon-scoped fonts for
WindowXMLDialog (that landed later, see xbmc/xbmc#28583): a script addon's
<font> tag can only reference a name the *active skin* defines. So instead
of bundling the .ttf with script.akasha.guide, we install it into the
skin's own fonts/ folder and register it under a namespaced font name
(font_akasha_guide) in the skin's single "Default" fontset, following the
"namespace with the addon name" convention recommended by the Kodi
community for exactly this situation.
"""
import os
import re
import shutil
import sys

FONT_NAME = 'font_akasha_guide'
FONT_FILE = 'Montserrat-Regular.ttf'
FONT_SIZE = 26


def _copy_font(path):
    src = os.path.join(os.path.dirname(os.path.dirname(sys.argv[0])), 'kodi', 'media', FONT_FILE)
    if not os.path.isfile(src):
        src = os.path.join(path, 'fonts', FONT_FILE)
    dst = os.path.join(path, 'fonts', FONT_FILE)
    if os.path.isfile(src) and src != dst:
        shutil.copy(src, dst)
        return True
    return os.path.isfile(dst)


def patch(path):
    xml_path = os.path.join(path, '1080i', 'Font.xml')
    if not os.path.isfile(xml_path):
        print('Font.xml not found at {}'.format(xml_path))
        return 1

    _copy_font(path)

    with open(xml_path, 'r', encoding='utf-8') as f:
        data = f.read()

    if '<name>{}</name>'.format(FONT_NAME) in data:
        print('Already patched with {}.'.format(FONT_NAME))
        return 0

    font_block = '''        <font>
            <name>{name}</name>
            <filename>{filename}</filename>
            <size>{size}</size>
        </font>
    </fontset>'''.format(name=FONT_NAME, filename=FONT_FILE, size=FONT_SIZE)

    new_data, count = re.subn(r'    </fontset>', font_block, data, count=1)
    if count != 1:
        print('Could not find </fontset> to patch in Font.xml, aborting.')
        return 1

    with open(xml_path, 'w', encoding='utf-8') as f:
        f.write(new_data)
    print('Patched Font.xml -> added {} ({} @ {}px)'.format(FONT_NAME, FONT_FILE, FONT_SIZE))
    return 0


if __name__ == '__main__':
    sys.exit(patch(sys.argv[1]))
