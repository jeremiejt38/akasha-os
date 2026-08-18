"""Unit tests for games_shortcuts.py — no xbmc dependency."""

import os
import tempfile
import unittest

import games_shortcuts


class TestGamesShortcuts(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.skin_patches = os.path.join(self.tmpdir, 'skin-patches', 'shortcuts')
        os.makedirs(self.skin_patches)
        self.data_file = os.path.join(self.skin_patches, 'games.DATA.xml')
        with open(self.data_file, 'w', encoding='utf-8') as f:
            f.write("""<?xml version='1.0' encoding='UTF-8'?>
<shortcuts>
    <shortcut>
        <label>Steam Link</label>
        <label2>Steam depuis PC</label2>
        <action>RunAddon(plugin.program.steamlink)</action>
    </shortcut>
    <shortcut>
        <label>Moonlight</label>
        <action>RunAddon(plugin.program.moonlight-qt)</action>
    </shortcut>
</shortcuts>
""")

    def test_load_shortcuts_returns_list(self):
        items = games_shortcuts.load_shortcuts(self.tmpdir)
        self.assertEqual(len(items), 2)
        self.assertEqual(items[0]['label'], 'Steam Link')
        self.assertEqual(items[0]['action'], 'RunAddon(plugin.program.steamlink)')
        self.assertEqual(items[1]['label'], 'Moonlight')

    def test_missing_file_returns_empty(self):
        items = games_shortcuts.load_shortcuts('/nonexistent')
        self.assertEqual(items, [])

    def test_malformed_xml_returns_empty(self):
        with open(self.data_file, 'w', encoding='utf-8') as f:
            f.write('<shortcuts><shortcut>')
        items = games_shortcuts.load_shortcuts(self.tmpdir)
        self.assertEqual(items, [])


if __name__ == '__main__':
    unittest.main()
