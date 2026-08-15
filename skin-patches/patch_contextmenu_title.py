#!/usr/bin/env python3
import sys
import os


def patch(path):
    if not os.path.isfile(path):
        print('DialogContextMenu.xml not found at {}'.format(path))
        return 1

    with open(path, 'r', encoding='utf-8') as f:
        data = f.read()

    # Only patch inside DialogContextMenu.xml. Replace the localized context menu
    # title with the simple "Menu" label for a cleaner look.
    old = '<param name="label" value="$LOCALIZE[10106]" />'
    new = '<param name="label" value="Menu" />'

    if old not in data:
        if new in data:
            print('Already patched.')
            return 0
        print('Pattern not found, aborting.')
        return 1

    data = data.replace(old, new, 1)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(data)
    print('Patched DialogContextMenu.xml header -> "Menu"')
    return 0


if __name__ == '__main__':
    sys.exit(patch(os.path.join(sys.argv[1], '1080i', 'DialogContextMenu.xml')))
