#!/usr/bin/env python3
import os
import re
import sys


def patch(path, version=''):
    xml_path = os.path.join(path, '1080i', 'DialogContextMenu.xml')
    if not os.path.isfile(xml_path):
        print('DialogContextMenu.xml not found at {}'.format(xml_path))
        return 1

    with open(xml_path, 'r', encoding='utf-8') as f:
        data = f.read()

    # Header group: title on the left, Akasha logo on the right.
    header = '''                <control type="group">
                    <height>120</height>
                    <control type="label">
                        <left>40</left>
                        <top>0</top>
                        <width>300</width>
                        <height>120</height>
                        <font>font_main_bold</font>
                        <label>Akasha</label>
                        <aligny>center</aligny>
                        <textcolor>dialog_fg_70</textcolor>
                    </control>
                    <control type="image">
                        <right>30</right>
                        <centertop>50%</centertop>
                        <width>64</width>
                        <height>64</height>
                        <aspectratio>keep</aspectratio>
                        <texture colordiffuse="FFFFFFFF">special://skin/extras/icons/akasha-logo-circle.png</texture>
                    </control>
                    <control type="image">
                        <bottom>20</bottom>
                        <height>1</height>
                        <left>40</left>
                        <right>30</right>
                        <texture colordiffuse="dialog_fg_12">common/white.png</texture>
                    </control>
                </control>'''

    # Replace any existing custom header group (Akasha + any logo/image).
    old_header = r'''                <control type="group">
                    <height>120</height>
                    <control type="label">
                        <left>40</left>
                        <top>0</top>
                        <width>300</width>
                        <height>120</height>
                        <font>font_main_bold</font>
                        <label>Akasha</label>
                        <aligny>center</aligny>
                        <textcolor>dialog_fg_70</textcolor>
                    </control>
                    <control type="image">
                        <right>30</right>
                        <centertop>50%</centertop>
                        <width>.*?</width>
                        <height>.*?</height>
                        <aspectratio>keep</aspectratio>
                        <texture colordiffuse="FFFFFFFF">.*?</texture>
                    </control>
                    <control type="image">
                        <bottom>20</bottom>
                        <height>1</height>
                        <left>40</left>
                        <right>30</right>
                        <texture colordiffuse="dialog_fg_12">common/white.png</texture>
                    </control>
                </control>'''
    new_data, count = re.subn(old_header, header, data, count=1, flags=re.DOTALL)

    if count == 0:
        # Fallback: original Object_MenuHeader include.
        old_inc = r'<include content="Object_MenuHeader">.*?</include>\s*(<!-- Akasha logo -->\s*<control type="image">.*?</control>)?'
        new_data, count = re.subn(old_inc, header, data, count=1, flags=re.DOTALL)

    if count != 1:
        if '<label>Akasha</label>' in data and 'special://skin/extras/icons/akasha-logo-circle.png' in data:
            print('Already patched with correct logo.')
            new_data = data
        else:
            print('Header block not found, aborting.')
            return 1

    # Make room for the version label by reducing the menu grouplist bottom.
    old_grouplist = '''                    <control type="grouplist" id="996">
                        <top>200</top>
                        <bottom>40</bottom>
                        <orientation>vertical</orientation>
                        <itemgap>0</itemgap>'''
    new_grouplist = '''                    <control type="grouplist" id="996">
                        <top>200</top>
                        <bottom>70</bottom>
                        <orientation>vertical</orientation>
                        <itemgap>0</itemgap>'''
    if old_grouplist in new_data:
        new_data = new_data.replace(old_grouplist, new_grouplist, 1)

    # Remove any previous version label (right=20, width=300, height=30, font10).
    new_data = re.sub(
        r'\s*<control type="label">\s*<right>20</right>\s*(?:<top>\d+</top>|<bottom>\d+</bottom>)\s*<width>300</width>\s*<height>30</height>\s*<font>font10</font>\s*<label>[^<]*</label>\s*<align>right</align>\s*<textcolor>55FFFFFF</textcolor>\s*</control>',
        '', new_data, flags=re.DOTALL
    )

    if version:
        version_label = '''                    <control type="label">
                        <right>20</right>
                        <bottom>110</bottom>
                        <width>300</width>
                        <height>30</height>
                        <font>font10</font>
                        <label>v{}</label>
                        <align>right</align>
                        <textcolor>55FFFFFF</textcolor>
                    </control>'''.format(version)

        new_data = new_data.replace(
            '''                    </control>
                    <control type="image">
                        <top>-24</top>''',
            '''                    </control>
{}
                    <control type="image">
                        <top>-24</top>'''.format(version_label), 1
        )

    with open(xml_path, 'w', encoding='utf-8') as f:
        f.write(new_data)
    print('Patched DialogContextMenu.xml header -> "Akasha" + Akasha logo, version label: {}'.format(version))
    return 0


if __name__ == '__main__':
    version = sys.argv[2] if len(sys.argv) > 2 else ''
    sys.exit(patch(sys.argv[1], version))
