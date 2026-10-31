"""Unit tests for field_veil.veil_color -- the bilinear palette sample
used to tint the opaque corner-cover masks (poster-corners, cast-mask)
so they merge into the baked field veil instead of reading as black
wedges on a non-flat background.
"""

import sys
import types
import unittest

for mod in ('xbmc', 'xbmcgui', 'xbmcaddon', 'xbmcvfs'):
    if mod not in sys.modules:
        sys.modules[mod] = types.ModuleType(mod)

import field_veil  # noqa: E402

_BLUR = {
    'topLeft': '102030',
    'topRight': '405060',
    'bottomLeft': '708090',
    'bottomRight': 'A0B0C0',
}


class TestVeilColor(unittest.TestCase):

    def test_corners_return_palette_hexes(self):
        self.assertEqual(field_veil.veil_color(_BLUR, 0.0, 0.0), '102030')
        self.assertEqual(field_veil.veil_color(_BLUR, 1.0, 0.0), '405060')
        self.assertEqual(field_veil.veil_color(_BLUR, 0.0, 1.0), '708090')
        self.assertEqual(field_veil.veil_color(_BLUR, 1.0, 1.0), 'A0B0C0')

    def test_center_is_mean_of_corners(self):
        # bilinear centre = average of the four corners
        got = field_veil.veil_color(_BLUR, 0.5, 0.5)
        exp = ''.join('{:02X}'.format(round(
            sum(int(h[i:i + 2], 16)
                for h in ('102030', '405060', '708090', 'A0B0C0')) / 4))
            for i in (0, 2, 4))
        self.assertEqual(got, exp)

    def test_mid_column_interpolates_vertically(self):
        # u=0 -> left edge: blend between topLeft and bottomLeft only
        got = field_veil.veil_color(_BLUR, 0.0, 0.5)
        self.assertEqual(got, '405060')  # mean of 102030 and 708090

    def test_incomplete_palette_returns_empty(self):
        self.assertEqual(field_veil.veil_color({}, 0.5, 0.8), '')
        self.assertEqual(field_veil.veil_color(None, 0.5, 0.8), '')
        self.assertEqual(
            field_veil.veil_color({'topLeft': '102030'}, 0.5, 0.8), '')

    def test_hash_prefixed_hexes_accepted(self):
        blur = {k: '#' + v for k, v in _BLUR.items()}
        self.assertEqual(field_veil.veil_color(blur, 0.0, 0.0), '102030')

    def test_position_clamped(self):
        self.assertEqual(field_veil.veil_color(_BLUR, -1.0, 2.0), '708090')


if __name__ == '__main__':
    unittest.main()
