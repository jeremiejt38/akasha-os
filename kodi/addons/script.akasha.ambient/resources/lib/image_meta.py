"""Akasha Ambient — image dimension probing.

Pure stdlib (no `xbmc*`, no PIL): reads just enough of each file's header
to get its pixel dimensions, so the slideshow can decide whether a photo
is portrait (pairable side-by-side, Google TV Ambient style) or landscape.
Unknown/unsupported formats return None and are treated as landscape.
"""
import os
import struct

_PNG_SIG = b'\x89PNG\r\n\x1a\n'
_GIF_SIGS = (b'GIF87a', b'GIF89a')
_JPEG_SOI = b'\xff\xd8'
# JPEG Start-Of-Frame markers that carry dimensions (all but SOI/EOI/RST/APPn).
_JPEG_SOF_MARKERS = frozenset(
    list(range(0xC0, 0xC4)) + list(range(0xC5, 0xC8)) +
    list(range(0xC9, 0xCC)) + list(range(0xCD, 0xD0))
)


def _png_size(f):
    sig = f.read(8)
    if sig != _PNG_SIG:
        return None
    header = f.read(16)
    # IHDR chunk: 4-byte length + 'IHDR' + 4-byte width + 4-byte height.
    if len(header) < 16 or header[4:8] != b'IHDR':
        return None
    width, height = struct.unpack('>II', header[8:16])
    return (width, height) if width and height else None


def _gif_size(f):
    sig = f.read(6)
    if sig not in _GIF_SIGS:
        return None
    dims = f.read(4)
    if len(dims) < 4:
        return None
    width, height = struct.unpack('<HH', dims)
    return (width, height) if width and height else None


def _bmp_size(f):
    sig = f.read(2)
    if sig != b'BM':
        return None
    f.seek(18)
    dims = f.read(8)
    if len(dims) < 8:
        return None
    width, height = struct.unpack('<ii', dims)
    return (abs(width), abs(height)) if width and height else None


def _jpeg_size(f):
    if f.read(2) != _JPEG_SOI:
        return None
    while True:
        # Scan for the next marker prefix byte.
        byte = f.read(1)
        while byte and byte != b'\xff':
            byte = f.read(1)
        if not byte:
            return None
        marker = f.read(1)
        if not marker:
            return None
        code = marker[0]
        if code in (0xD8, 0xD9) or 0xD0 <= code <= 0xD7:
            # Standalone markers without a length field: keep scanning.
            continue
        seg_len_raw = f.read(2)
        if len(seg_len_raw) < 2:
            return None
        seg_len = struct.unpack('>H', seg_len_raw)[0]
        if code in _JPEG_SOF_MARKERS:
            data = f.read(5)
            if len(data) < 5:
                return None
            height, width = struct.unpack('>HH', data[1:5])
            return (width, height) if width and height else None
        # Skip the rest of this segment (length includes its own 2 bytes).
        if seg_len < 2:
            return None
        f.seek(seg_len - 2, os.SEEK_CUR)


def image_size(path):
    """Return (width, height) in pixels for `path`, or None if unknown."""
    try:
        with open(path, 'rb') as f:
            head = f.read(2)
            f.seek(0)
            if head == _JPEG_SOI:
                return _jpeg_size(f)
            if head == _PNG_SIG[:2]:
                return _png_size(f)
            if head in (b'GI', b'BM'):
                return _gif_size(f) if head == b'GI' else _bmp_size(f)
            return None
    except OSError:
        return None


def is_portrait(path):
    """True if the image is taller than it is wide; False when unknown."""
    size = image_size(path)
    return bool(size and size[1] > size[0])
