"""Unit tests for service.akasha.splash helpers.

xbmc/xbmcgui/xbmcaddon are stubbed before importing service.py, whose
module level instantiates xbmcaddon.Addon() and xbmc.Monitor().
"""

import os
import sys
import types
import unittest
from unittest.mock import MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


class _StubModule(types.ModuleType):
    def __getattr__(self, name):
        mock = MagicMock(name=name)
        setattr(self, name, mock)
        return mock


def _install_stubs():
    for name in ('xbmc', 'xbmcgui', 'xbmcaddon'):
        sys.modules[name] = _StubModule(name)


_install_stubs()

import service  # noqa: E402


class FormatChangelogTests(unittest.TestCase):
    def test_headings_and_bullets(self):
        md = ('## [0.70.0](https://github.com/x/y/compare/v1...v2) (2026-10-26)\n\n'
              '### Features\n\n'
              '* add thing ([#12](https://github.com/x/y/pull/12)) '
              '([abc123](https://github.com/x/y/commit/abc123))\n'
              '* other thing\n')
        out = service.format_changelog(md)
        self.assertIn('0.70.0 (2026-10-26)', out)
        self.assertIn('Features', out)
        self.assertIn('• add thing (#12) (abc123)', out)
        self.assertIn('• other thing', out)
        self.assertNotIn('##', out)
        self.assertNotIn('http', out)

    def test_bold_and_full_changelog_footer(self):
        md = ('### Bug Fixes\n\n'
              '* fix something by @user in https://github.com/x/y/pull/5\n'
              '**Full Changelog**: https://github.com/x/y/compare/a...b\n')
        out = service.format_changelog(md)
        self.assertIn('• fix something', out)
        self.assertNotIn('by @', out)
        self.assertNotIn('Full Changelog', out)
        self.assertNotIn('**', out)

    def test_blank_runs_collapse(self):
        out = service.format_changelog('a\n\n\n\n\nb')
        self.assertEqual(out, 'a\n\nb')

    def test_empty(self):
        self.assertEqual(service.format_changelog(''), '')
        self.assertEqual(service.format_changelog(None), '')


if __name__ == '__main__':
    unittest.main()
