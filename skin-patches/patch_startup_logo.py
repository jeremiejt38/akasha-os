#!/usr/bin/env python3
"""Patch Arctic Horizon 2 startup logo to use Akasha OS branding."""

import os
import sys

SKIN_DIR = "/storage/.kodi/addons/skin.arctic.horizon.2"
XML_PATH = os.path.join(SKIN_DIR, "1080i", "Includes_Objects.xml")

if not os.path.exists(XML_PATH):
    print(f"Skin XML not found: {XML_PATH}")
    sys.exit(0)

OLD_BLOCK = '''    <include name="Object_StartUp_Logo">
        <control type="grouplist">
            <height>128</height>
            <centertop>400</centertop>
            <orientation>vertical</orientation>
            <align>center</align>
            <control type="image">
                <width>96</width>
                <height>96</height>
                <centerleft>50%</centerleft>
                <aspectratio>keep</aspectratio>
                <texture colordiffuse="$VAR[ColorHighlight]">special://skin/extras/icons/kodi.png</texture>
            </control>
            <control type="label">
                <height>32</height>
                <textcolor>main_fg_100</textcolor>
                <label>KODI</label>
                <font>font_logo_large</font>
                <align>center</align>
            </control>
        </control>
        <control type="label">
            <height>80</height>
            <centertop>49%</centertop>
            <aligny>center</aligny>
            <align>center</align>
            <font>font_info_black</font>
            <textcolor>$VAR[ColorHighlight]</textcolor>
            <label>[COLOR=main_logo]Arctic[/COLOR] Horizon 2</label>
        </control>'''

NEW_BLOCK = '''    <include name="Object_StartUp_Logo">
        <control type="grouplist">
            <height>160</height>
            <centertop>280</centertop>
            <orientation>vertical</orientation>
            <align>center</align>
            <control type="image">
                <width>140</width>
                <height>140</height>
                <centerleft>50%</centerleft>
                <aspectratio>keep</aspectratio>
                <texture colordiffuse="FFFFFFFF">special://skin/extras/icons/akasha-logo-circle.png</texture>
            </control>
        </control>
        <control type="label">
            <height>80</height>
            <centertop>40%</centertop>
            <aligny>center</aligny>
            <align>center</align>
            <font>font_info_black</font>
            <textcolor>$VAR[ColorHighlight]</textcolor>
            <label>[COLOR=main_logo]Akasha OS[/COLOR]</label>
        </control>'''

with open(XML_PATH, "r", encoding="utf-8") as f:
    content = f.read()

if OLD_BLOCK not in content:
    print("Startup logo block not found or already patched.")
else:
    content = content.replace(OLD_BLOCK, NEW_BLOCK)
    with open(XML_PATH, "w", encoding="utf-8") as f:
        f.write(content)
    print("Startup logo patched to Akasha OS.")
