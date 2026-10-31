#!/usr/bin/env python3
"""Install the Plex-style VideoOSD into Arctic Horizon 2.

Replaces the skin's VideoOSD.xml with the minimal Plex-parity layout from
skin-patches/plex-osd/ and copies its textures into the skin media dir.
The original file is backed up once as VideoOSD.xml.ah2-orig.
"""
import os
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, 'plex-osd')

WINDOWS = ('VideoOSD.xml', 'DialogSeekBar.xml')
TEXTURES = ('akasha-osd-scrim-top.png', 'akasha-osd-scrim-bottom.png',
            'akasha-circle.png', 'akasha-chev-down.png',
            'akasha-chapters.png',
            'osd-nib.png', 'osd-subs.png', 'osd-chev.png') + tuple(
            'osd-tag-{}.png'.format(r)
            for r in ('288', '480', '540', '576', '720', '900', '1080',
                      '1440', '2160', '4K'))


def patch(skin_dir):
    xml_dir = os.path.join(skin_dir, '1080i')
    media_dir = os.path.join(skin_dir, 'media')
    for window in WINDOWS:
        target = os.path.join(xml_dir, window)
        backup = target + '.ah2-orig'
        if not os.path.exists(target):
            print('{} not found; skipping Plex OSD patch'.format(window))
            continue
        if not os.path.exists(backup):
            shutil.copy2(target, backup)
        shutil.copy2(os.path.join(SRC, window), target)
    for texture in TEXTURES:
        src = os.path.join(SRC, texture)
        if os.path.exists(src):
            shutil.copy2(src, os.path.join(media_dir, texture))
    print('Plex-style OSD installed (backups: *.ah2-orig)')


if __name__ == '__main__':
    patch(sys.argv[1])
