#!/usr/bin/env python3
"""Patch Arctic Horizon 2 Home.xml with the Akasha boot veil.

Adds a fullscreen group on top of the native Home window that reproduces
the 1198 loading screen (background + Akasha logo + busy spinner). It
stays visible until script.akasha.aura sets Window.Property(Akasha.AuraReady)
when its window opens, so the native Kodi home is never visible between
the boot intro and Aura. service.akasha.aura force-clears the property
after a bounded wait if Aura never claims the screen (safety net).
"""

import os
import sys

SKIN_DIR = sys.argv[1] if len(sys.argv) > 1 \
    else "/storage/.kodi/addons/skin.arctic.horizon.2"
XML_PATH = os.path.join(SKIN_DIR, "1080i", "Home.xml")

VEIL = '''
        <!-- Akasha boot veil: mirrors the 1198 loading screen on top of
             Home until Aura opens, so the native home never flashes at
             startup. Aura sets Window.Property(Akasha.AuraReady) in
             onInit; service.akasha.aura force-clears it after a bounded
             wait as a safety net. -->
        <control type="group">
            <visible>String.IsEmpty(Window(Home).Property(Akasha.AuraReady))</visible>
            <animation effect="fade" start="100" end="0" time="300" reversible="false">Hidden</animation>
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
            <control type="group">
                <centertop>700</centertop>
                <height>80</height>
                <include content="Object_BusySpinner">
                    <param name="colordiffuse" value="main_fg" />
                    <param name="haslabel" value="false" />
                </include>
            </control>
        </control>
    </controls>
</window>'''

if not os.path.exists(XML_PATH):
    print("Skin Home.xml not found: {}".format(XML_PATH))
    sys.exit(0)

with open(XML_PATH, "r", encoding="utf-8") as f:
    content = f.read()

if "Akasha.AuraReady" in content:
    print("Home.xml already has the Akasha boot veil.")
elif "</controls>\n</window>" not in content:
    print("Home.xml tail not found; boot veil NOT applied.")
else:
    content = content.replace("</controls>\n</window>", VEIL)
    with open(XML_PATH, "w", encoding="utf-8") as f:
        f.write(content)
    print("Home.xml patched with the Akasha boot veil.")
