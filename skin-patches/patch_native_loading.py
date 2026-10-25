#!/usr/bin/env python3
"""Patch Arctic Horizon 2 navigation windows with the Akasha loading screen.

Akasha OS is an appliance: the native Kodi menu windows (Home, media
libraries, weather, programs...) are never meant to be lived in, but they
still flash for a frame or two during transitions — most visibly when Aura
hands off to video playback and Home paints underneath before fullscreen
video takes over.

Rather than chasing every leak, this patch puts a permanent, fully opaque
loading screen *on top* of each navigation window: the startup background
and Akasha logo (the same skin includes used by the boot veil), a
"Chargement…" label, and an organic wave that drifts horizontally at the
bottom of the screen. The window keeps working underneath — focus and
actions still function — but the user only ever sees the loading screen.

The wave texture is three exact 960 px sine periods, so sliding the layer
one full period on a loop animates it with no visible jump. Two layers
with different speeds, directions and opacities give the organic feel.
"""

import os
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SRC_TEXTURE = os.path.join(HERE, 'loading', 'akasha-wave.png')

# Kodi navigation/menu windows that should never be lived in. Files that
# do not exist in the skin are simply skipped.
WINDOWS = (
    'Home.xml',
    'MyVideoNav.xml',
    'MyMusicNav.xml',
    'MyPrograms.xml',
    'MyPics.xml',
    'MyWeather.xml',
    'MyGames.xml',
    'MyPlaylists.xml',
    'MyFileNav.xml',
)

MARKER = 'AkashaLoadingOverlay'

# Inserted right before the closing </controls> tag so the overlay sits on
# top of every other control in the window. Kept separate from the
# </controls></window> tail because skins may add comments or blank lines
# between them.
OVERLAY = '''
        <!-- Akasha loading overlay: permanent opaque cover over the native
             menu. These windows are transitions surfaces only on Akasha OS;
             whenever one is on top (boot, playback handoff, stray
             navigation) the user sees the loading screen instead of the
             Kodi menu. Reuses the startup background + logo includes from
             the skin so it matches the boot veil. -->
        <control type="group">
            <include>Background_StartUp</include>
            <include>Object_StartUp_Logo</include>
            <control type="label">
                <centertop>610</centertop>
                <height>40</height>
                <aligny>center</aligny>
                <align>center</align>
                <textcolor>main_logo</textcolor>
                <label>$ADDON[script.akasha.aura 33180]</label>
            </control>
            <!-- Organic wave: 3 exact 960px periods, slide one period on a
                 loop = continuous drift with no jump. Two layers, different
                 speed/direction/opacity. -->
            <control type="image">
                <left>0</left>
                <top>880</top>
                <width>2880</width>
                <height>200</height>
                <texture colordiffuse="59FFFFFF">akasha-wave.png</texture>
                <aspectratio>stretch</aspectratio>
                <animation effect="slide" start="0,0" end="-960,0" time="9000" loop="true" tween="linear" condition="true">Conditional</animation>
            </control>
            <control type="image">
                <left>-960</left>
                <top>880</top>
                <width>2880</width>
                <height>200</height>
                <texture colordiffuse="2EFFFFFF">akasha-wave.png</texture>
                <aspectratio>stretch</aspectratio>
                <animation effect="slide" start="-960,0" end="0,0" time="14000" loop="true" tween="linear" condition="true">Conditional</animation>
            </control>
        </control>
'''


def patch(skin_dir):
    xml_dir = os.path.join(skin_dir, '1080i')
    media_dir = os.path.join(skin_dir, 'media')
    if not os.path.isdir(xml_dir):
        print('Skin 1080i dir not found: {}; skipping loading overlay'.format(xml_dir))
        return

    if os.path.isdir(media_dir) and os.path.exists(SRC_TEXTURE):
        shutil.copy2(SRC_TEXTURE, os.path.join(media_dir, 'akasha-wave.png'))

    patched = skipped = 0
    for name in WINDOWS:
        path = os.path.join(xml_dir, name)
        if not os.path.exists(path):
            continue
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()
        if MARKER in content or 'akasha-wave.png' in content:
            print('{} already has the loading overlay; skipping'.format(name))
            skipped += 1
            continue
        pos = content.rfind('</controls>')
        if pos == -1:
            print('{}: </controls> not found; NOT patched'.format(name))
            continue
        backup = path + '.ah2-orig'
        if not os.path.exists(backup):
            shutil.copy2(path, backup)
        content = content[:pos] + OVERLAY + content[pos:]
        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)
        patched += 1
    print('Akasha loading overlay applied to {} window(s), {} already patched'.format(
        patched, skipped))


if __name__ == '__main__':
    patch(sys.argv[1] if len(sys.argv) > 1 else '/storage/.kodi/addons/skin.arctic.horizon.2')
