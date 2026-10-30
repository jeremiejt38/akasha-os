"""Baked UltraBlurColors field veil shared by the Aura window (hero) and
the detail page.

Reverse-engineered on official-live/17 + 53 + 18 (same items, same
server): Plex renders the RAW palette field -- measured pixels equal the
exact corner hexes at the corners (bottom-left == bottomLeft,
bottom-right == bottomRight, top-left == topLeft, ~full alpha) -- under a
fixed mask that stays opaque on the left ~45%/bottom and opens a
diagonal window toward the top-right where the fanart shows through.

Kodi cannot gradient-tint a texture, so the composite RGBA is generated
once per palette (PIL is present in the Kodi runtime) and cached in the
addon profile; the skin loads it through an $INFO texture property.
"""

import os

import xbmc

_FIELD_VEIL_DIR = 'fields'
_FIELD_VEIL_CAP = 24
_MASK_VERSION = 'v3'


def _blur_hex(value):
    """Normalise an UltraBlurColors corner ('rrggbb' or '#rrggbb') to
    'RRGGBB' for setColorDiffuse, '' when absent."""
    s = str(value or '').lstrip('#')[-6:]
    return s.upper() if len(s) == 6 else ''


def bake_field_veil(profile_dir, blur):
    """Bake the Plex field veil PNG for a palette; returns its path, or
    '' when the palette is incomplete or PIL is unavailable -- callers
    then keep their plain-scrim fallback.
    """
    hexes = [_blur_hex((blur or {}).get(k)) for k in
             ('topLeft', 'topRight', 'bottomLeft', 'bottomRight')]
    if not all(hexes):
        return ''
    # The mask revision rides in the filename: Kodi's texture cache
    # keys on the path, so a mask tweak must produce a new file.
    name = 'field-{}-{}.png'.format(
        _MASK_VERSION, ''.join(h.lower() for h in hexes))
    base = os.path.join(profile_dir, _FIELD_VEIL_DIR)
    path = os.path.join(base, name)
    if os.path.exists(path):
        return path
    try:
        from PIL import Image
        corners = Image.new('RGB', (2, 2))
        corners.putpixel(
            (0, 0), tuple(int(hexes[0][i:i + 2], 16) for i in (0, 2, 4)))
        corners.putpixel(
            (1, 0), tuple(int(hexes[1][i:i + 2], 16) for i in (0, 2, 4)))
        corners.putpixel(
            (0, 1), tuple(int(hexes[2][i:i + 2], 16) for i in (0, 2, 4)))
        corners.putpixel(
            (1, 1), tuple(int(hexes[3][i:i + 2], 16) for i in (0, 2, 4)))
        rgb = corners.resize((480, 270), Image.BILINEAR)
        # Scrim mask fitted on official 17/18 (identical on home and
        # detail): an elliptical sector centred on the top-right corner.
        # alpha = 0 inside (fanart fully visible), ramp to 1 outside.
        # Measured anchors: open from u~0.80 at v=0; right edge alpha
        # ~0.3 at v=0.28, ~1.0 by v~0.5.
        mw, mh = 96, 54
        alpha = Image.new('L', (mw, mh))
        alpha.putdata([
            int(round(255 * max(0.0, min(1.0,
                ((((x / (mw - 1) - 1.0) / 0.50) ** 2 +
                  ((y / (mh - 1)) / 0.48) ** 2) ** 0.5 - 0.40) / 0.62))))
            for y in range(mh) for x in range(mw)])
        veil = rgb.copy()
        veil.putalpha(alpha.resize((480, 270), Image.BILINEAR))
        if not os.path.isdir(base):
            os.makedirs(base, exist_ok=True)
        veil.save(path)
        # Cap the cache: one tiny PNG per palette, oldest evicted.
        try:
            files = sorted(
                (os.path.join(base, f) for f in os.listdir(base)
                 if f.startswith('field-')),
                key=os.path.getmtime)
            for stale in files[:-_FIELD_VEIL_CAP]:
                os.unlink(stale)
        except OSError:
            pass
        return path
    except Exception as e:
        xbmc.log('Akasha Aura: field veil bake failed: {}'.format(e),
                 xbmc.LOGERROR)
        return ''
