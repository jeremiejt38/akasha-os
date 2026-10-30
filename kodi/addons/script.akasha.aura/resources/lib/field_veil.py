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
_MASK_VERSION = 'v10'


def _blur_hex(value):
    """Normalise an UltraBlurColors corner ('rrggbb' or '#rrggbb') to
    'RRGGBB' for setColorDiffuse, '' when absent."""
    s = str(value or '').lstrip('#')[-6:]
    return s.upper() if len(s) == 6 else ''


def veil_color(blur, u, v):
    """Bilinear sample of the UltraBlurColors palette field at
    normalised position (u, v) -- same interpolation PIL applies to
    the baked veil. Returns 'RRGGBB', or '' when the palette is
    incomplete.

    Used to tint the opaque corner-cover masks (poster-corners,
    cast-mask) so they merge into the veil band they sit on instead of
    showing the fixed dark colour they had when the background was
    flat.
    """
    hexes = [_blur_hex((blur or {}).get(k)) for k in
             ('topLeft', 'topRight', 'bottomLeft', 'bottomRight')]
    if not all(hexes):
        return ''
    u = max(0.0, min(1.0, u))
    v = max(0.0, min(1.0, v))
    (tl, tr, bl, br) = (tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))
                        for h in hexes)
    out = []
    for c in range(3):
        top = tl[c] * (1 - u) + tr[c] * u
        bot = bl[c] * (1 - u) + br[c] * u
        out.append(int(round(top * (1 - v) + bot * v)))
    return '{:02X}{:02X}{:02X}'.format(*out)


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
        # corners.resize() would clamp into flat quarter-columns: PIL
        # bilinear sampling outside the source centre range repeats the
        # edge, so build the true 4-corner bilinear field explicitly.
        fw, fh = 120, 68
        (tl, tr, bl, br) = (tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))
                            for h in hexes)
        flat = Image.new('RGB', (fw, fh))
        flat.putdata([
            tuple(int(round(
                tl[c] * (1 - u) * (1 - v) + tr[c] * u * (1 - v)
                + bl[c] * (1 - u) * v + br[c] * u * v))
                for c in range(3))
            for y in range(fh) for x in range(fw)
            for u, v in ((x / (fw - 1), y / (fh - 1)),)])
        rgb = flat.resize((480, 270), Image.BILINEAR)
        # Scrim mask fitted on official 17/18/32 (identical on home and
        # detail): the fanart shows through as a faint bleed (~0.1 of
        # the art over u~0.15..0.5, dimly visible figures) plus a steep
        # ramp to full exposure at u~0.75, all dying out toward the
        # bottom (v~0.05..0.7). alpha = 1 - art coverage.
        mw, mh = 96, 54

        def _smooth(t):
            t = max(0.0, min(1.0, t))
            return t * t * (3.0 - 2.0 * t)

        def _alpha(x, y):
            u = x / (mw - 1)
            v = y / (mh - 1)
            horiz = (0.10 * _smooth((u - 0.15) / 0.25)
                     + _smooth((u - 0.48) / 0.28))
            cover = min(1.0, horiz) * (1.0 - _smooth((v - 0.05) / 0.70))
            return int(round(255 * (1.0 - cover)))

        alpha = Image.new('L', (mw, mh))
        alpha.putdata([_alpha(x, y)
                       for y in range(mh) for x in range(mw)])
        # Plex's field is not flat palette: the interior carries a broad
        # luminance dip (~0.6-0.7 of the raw palette behind the hero
        # text column, v~0.05..0.75) plus an extra top scrim, while the
        # palette corners and the very bottom stay pure -- profile
        # measured on official-live/32 & 18 clean-field pixels. Applied
        # to RGB so the fanart texture stays out of the flat band.
        def _shade(x, y):
            u = x / (mw - 1)
            v = y / (mh - 1)
            horiz = (_smooth((u - 0.02) / 0.10)
                     * (1.0 - 0.22 * _smooth((u - 0.40) / 0.15)))
            plateau = (0.55 * _smooth(v / 0.08)
                       + 0.45 * _smooth((v - 0.05) / 0.30)) \
                * (1.0 - _smooth((v - 0.53) / 0.30))
            top = 0.40 * (1.0 - _smooth(v / 0.12))
            depth = horiz * (0.38 * plateau + top)
            return int(round(255 * (1.0 - depth)))

        shade = Image.new('L', (mw, mh))
        shade.putdata([_shade(x, y)
                       for y in range(mh) for x in range(mw)])
        from PIL import ImageChops
        rgb = ImageChops.multiply(rgb, shade.resize(
            (480, 270), Image.BILINEAR).convert('RGB'))
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
