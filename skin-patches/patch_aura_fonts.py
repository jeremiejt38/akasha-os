#!/usr/bin/env python3
"""Register the Plex-like Inter fonts used by the Akasha Aura custom XML
windows in the Arctic Horizon 2 skin's Font.xml.

Same mechanism as patch_akasha_fonts.py (see its docstring): Kodi 21 does
not support addon-scoped fonts for WindowXMLDialog, so Aura references
namespaced font names (font_aura_*) registered in the skin's "Default"
fontset. The Inter Unicode faces already ship with the resource.font
addon, so the <filename> entries point at resource:// paths — nothing to
copy.

Plex Android TV uses a wide grotesque (Plex Sans, Inter-like); the skin's
stock RobotoCondensed faces are visibly narrower — this alias set is what
makes Aura's tabs/chips/captions match Plex's type metrics.
"""
import os
import re
import sys

FONTS = [
    ('font_aura_mini',                  'Inter-Unicode-Regular.ttf', 26),
    ('font_aura_mini_bold',             'Inter-Unicode-Bold.ttf',   28),
    ('font_aura_tiny',                  'Inter-Unicode-Regular.ttf', 22),
    ('font_aura_tiny_bold',             'Inter-Unicode-Bold.ttf',   24),
    ('font_aura_midi',                  'Inter-Unicode-Regular.ttf', 35),
    ('font_aura_hint',                  'Inter-Unicode-Regular.ttf', 16),
    ('font_aura_hint_bold',             'Inter-Unicode-Bold.ttf',   18),
    ('font_aura_head_bold',             'Inter-Unicode-Bold.ttf',   42),
    ('font_aura_main_bold',             'Inter-Unicode-Bold.ttf',   32),
    ('font_aura_info_black_doublerow',  'Inter-Unicode-Bold.ttf',   56),
]
FONT_FILES = sorted({f[1] for f in FONTS})
RESOURCE_ADDON = '/storage/.kodi/addons/resource.font.robotocjksc/resources'


def _copy_fonts(path):
    import shutil
    ok = True
    for name in FONT_FILES:
        src = os.path.join(RESOURCE_ADDON, name)
        dst = os.path.join(path, 'fonts', name)
        if not os.path.isfile(dst):
            if not os.path.isfile(src):
                print('Missing font source {}'.format(src))
                ok = False
                continue
            shutil.copy(src, dst)
    return ok


def patch(path):
    xml_path = os.path.join(path, '1080i', 'Font.xml')
    if not os.path.isfile(xml_path):
        print('Font.xml not found at {}'.format(xml_path))
        return 1

    _copy_fonts(path)

    with open(xml_path, 'r', encoding='utf-8') as f:
        data = f.read()

    # Normalize stale resource:// filenames on previously registered faces
    for name, filename, _size in FONTS:
        data = re.sub(
            r'(<name>' + re.escape(name) + r'</name>\s*<filename>)[^<]+(</filename>)',
            r'\g<1>' + filename + r'\g<2>', data)

    missing = [f for f in FONTS if '<name>{}</name>'.format(f[0]) not in data]
    if not missing:
        with open(xml_path, 'w', encoding='utf-8') as f:
            f.write(data)
        print('Already patched with font_aura_* (filenames normalized).')
        return 0

    block = ''.join(
        '        <font>\n'
        '            <name>{name}</name>\n'
        '            <filename>{filename}</filename>\n'
        '            <size>{size}</size>\n'
        '        </font>\n'.format(name=name, filename=filename, size=size)
        for name, filename, size in missing
    )

    new_data, count = re.subn(r'    </fontset>', block + '    </fontset>', data, count=1)
    if count != 1:
        print('Could not find </fontset> to patch in Font.xml, aborting.')
        return 1

    with open(xml_path, 'w', encoding='utf-8') as f:
        f.write(new_data)
    print('Patched Font.xml -> added {} font_aura_* faces'.format(len(missing)))
    return 0


if __name__ == '__main__':
    sys.exit(patch(sys.argv[1]))
