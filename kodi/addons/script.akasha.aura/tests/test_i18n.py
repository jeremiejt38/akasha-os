"""Unit tests for i18n.py — the single source of truth for Aura strings."""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'resources', 'lib'))

import i18n  # noqa: E402


class StringTableTests(unittest.TestCase):
    def test_every_entry_has_both_languages(self):
        for msgid, pair in i18n.STRINGS.items():
            self.assertIsInstance(pair, tuple, msgid)
            self.assertEqual(len(pair), 2, msgid)
            fr, en = pair
            self.assertTrue(fr.strip(), 'empty french for {}'.format(msgid))
            self.assertTrue(en.strip(), 'empty english for {}'.format(msgid))

    def test_ids_stay_in_addon_range(self):
        for msgid in i18n.STRINGS:
            self.assertGreaterEqual(msgid, 32000)
            self.assertLessEqual(msgid, 39999)

    def test_ids_are_unique_keys(self):
        self.assertEqual(len(i18n.STRINGS), len(set(i18n.STRINGS)))


class FallbackTests(unittest.TestCase):
    def test_tr_falls_back_to_french_outside_kodi(self):
        self.assertEqual(i18n.tr(33001), 'Recherche')
        self.assertEqual(i18n.tr(33137), 'Continuer à regarder')

    def test_tr_unknown_id_returns_empty(self):
        self.assertEqual(i18n.tr(39999), '')

    def test_fmt_air_date_french(self):
        self.assertEqual(i18n.fmt_air_date('2025-10-19'), '19 oct. 2025')
        self.assertEqual(i18n.fmt_air_date(''), '')


class PoGenerationTests(unittest.TestCase):
    def test_en_file_uses_english_msgid_empty_msgstr(self):
        lines = list(i18n._po_lines('en_gb', 1))
        block = lines[lines.index('msgctxt "#33001"'):]
        self.assertEqual(block[1], 'msgid "Search"')
        self.assertEqual(block[2], 'msgstr ""')

    def test_fr_file_keeps_english_msgid_with_french_msgstr(self):
        lines = list(i18n._po_lines('fr_fr', 0))
        block = lines[lines.index('msgctxt "#33001"'):]
        self.assertEqual(block[1], 'msgid "Search"')
        self.assertEqual(block[2], 'msgstr "Recherche"')

    def test_newlines_are_escaped_in_output(self):
        # 33095 contains a real newline; it must appear escaped, never raw.
        self.assertIn('\n', i18n.STRINGS[33095][0])
        text = '\n'.join(i18n._po_lines('fr_fr', 0))
        self.assertIn('(La TV sera aussi éteinte via CEC)', text)
        self.assertNotIn('\n(La TV', text)

    def test_committed_po_files_are_in_sync_with_table(self):
        """strings.po are generated from STRINGS; committers must re-run
        `python3 resources/lib/i18n.py` after touching the table."""
        lib_dir = os.path.join(os.path.dirname(__file__), '..', 'resources')
        for lang, index in (('fr_fr', 0), ('en_gb', 1)):
            path = os.path.join(
                lib_dir, 'language', 'resource.language.{}'.format(lang),
                'strings.po')
            with open(path, encoding='utf-8') as f:
                committed = f.read()
            expected = '\n'.join(i18n._po_lines(lang, index))
            self.assertEqual(committed, expected,
                             '{} is stale — regenerate with i18n.py'
                             .format(path))

    def test_every_tr_call_uses_a_known_id(self):
        """Scan lib/*.py for i18n.tr(<id>) literals and require each id to
        exist in STRINGS -- catches typos and forgotten table entries."""
        import re
        lib_dir = os.path.join(
            os.path.dirname(__file__), '..', 'resources', 'lib')
        pattern = re.compile(r'\bi18n\.tr\((\d{5})\)')
        missing = []
        for name in os.listdir(lib_dir):
            if not name.endswith('.py'):
                continue
            path = os.path.join(lib_dir, name)
            with open(path, encoding='utf-8') as f:
                for lineno, line in enumerate(f, 1):
                    for msgid in pattern.findall(line):
                        if int(msgid) not in i18n.STRINGS:
                            missing.append('{}:{} -> {}'.format(
                                name, lineno, msgid))
        self.assertEqual(missing, [])


if __name__ == '__main__':
    unittest.main()
