#!/usr/bin/env python3
"""Patch Arctic Horizon 2 Custom_1199_Overlay.xml to add Akasha system overlay."""
import os
import re
import sys

SNIPPET = """\n        <!-- Akasha system overlay (enabled via Skin.HasSetting(akasha_overlay)) -->
        <include content="Object_Control" condition="Skin.HasSetting(akasha_overlay)">
            <param name="control">group</param>
            <control type="grouplist">
                <right>40</right>
                <top>40</top>
                <orientation>vertical</orientation>
                <include content="Overlay_InfoLabel">
                    <label>CPU: $INFO[System.CpuUsage] | RAM: $INFO[System.Memory(used)]/$INFO[System.TotalMemory]</label>
                    <textcolor>yellowgreen</textcolor>
                </include>
                <include content="Overlay_InfoLabel">
                    <label>Temp: $INFO[System.CPUTemperature] | Gov: $INFO[Skin.String(akasha_overlay_governor)]</label>
                    <textcolor>yellowgreen</textcolor>
                </include>
                <include content="Overlay_InfoLabel">
                    <label>Freq: $INFO[Skin.String(akasha_overlay_freq)] | Load: $INFO[Skin.String(akasha_overlay_load)]</label>
                    <textcolor>yellowgreen</textcolor>
                </include>
                <include content="Overlay_InfoLabel">
                    <label>Fan: $INFO[Skin.String(akasha_overlay_fan)] | Uptime: $INFO[Skin.String(akasha_overlay_uptime)]</label>
                    <textcolor>yellowgreen</textcolor>
                </include>
            </control>
        </include>
"""


def patch(skin_dir):
    path = os.path.join(skin_dir, '1080i', 'Custom_1199_Overlay.xml')
    if not os.path.exists(path):
        print('Custom_1199_Overlay.xml not found; skipping overlay patch')
        return

    with open(path, 'r', encoding='utf-8') as f:
        data = f.read()

    # Ensure the overlay window is visible when our setting is enabled
    new_data, n = re.subn(
        r'<visible>Skin\.HasSetting\(DebugInfo\)</visible>',
        '<visible>Skin.HasSetting(DebugInfo) | Skin.HasSetting(akasha_overlay)</visible>',
        data,
        count=1,
    )
    if n == 0:
        print('Could not find window visibility tag to patch overlay')
        return

    if 'akasha_overlay' not in new_data:
        # Insert before the closing </controls> of the root window
        new_data = re.sub(r'(\s+)(</controls>)', r'\1' + SNIPPET + r'\1\2', new_data, count=1)
        if new_data == data:
            print('Could not find </controls> tag to patch overlay')
            return

    with open(path, 'w', encoding='utf-8') as f:
        f.write(new_data)
    print('Patched Custom_1199_Overlay.xml with Akasha overlay')


if __name__ == '__main__':
    patch(sys.argv[1] if len(sys.argv) > 1 else '/storage/.kodi/addons/skin.arctic.horizon.2')
