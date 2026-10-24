#!/usr/bin/env python3
"""DRM framebuffer grabber for LibreELEC/Pi4 — reads the KMS scanout buffer
via ioctls (plane-based, works with atomic commits). ~10-20fps.

Usage: drm_grab.py <out.raw>   — dumps raw scanout + prints geometry to stderr
"""
import ctypes, mmap, os, struct, sys
libc = ctypes.CDLL('libc.so.6', use_errno=True)

def ioctl(fd, req, arg):
    r = libc.ioctl(fd, ctypes.c_ulong(req), ctypes.byref(arg))
    if r < 0:
        e = ctypes.get_errno()
        raise OSError(e, os.strerror(e))

def _IOWR(nr, size):
    return 0xC0000000 | (size << 16) | (ord('d') << 8) | nr
def _IOW(nr, size):
    return 0x40000000 | (size << 16) | (ord('d') << 8) | nr

class set_client_cap(ctypes.Structure):
    _fields_ = [("capability", ctypes.c_uint64), ("value", ctypes.c_uint64)]

class get_plane_res(ctypes.Structure):
    _fields_ = [("plane_id_ptr", ctypes.c_uint64), ("count_planes", ctypes.c_uint32)]

class get_plane(ctypes.Structure):
    _fields_ = [("plane_id", ctypes.c_uint32), ("crtc_id", ctypes.c_uint32),
                ("fb_id", ctypes.c_uint32), ("possible_crtcs", ctypes.c_uint32),
                ("gamma_size", ctypes.c_uint32), ("count_format_types", ctypes.c_uint32),
                ("format_type_ptr", ctypes.c_uint64)]

class fb_cmd2(ctypes.Structure):
    _fields_ = [("fb_id", ctypes.c_uint32), ("width", ctypes.c_uint32),
                ("height", ctypes.c_uint32), ("pixel_format", ctypes.c_uint32),
                ("flags", ctypes.c_uint32), ("handles", ctypes.c_uint32 * 4),
                ("pitches", ctypes.c_uint32 * 4), ("offsets", ctypes.c_uint32 * 4),
                ("modifier", ctypes.c_uint64 * 4)]

class prime_handle(ctypes.Structure):
    _fields_ = [("handle", ctypes.c_uint32), ("flags", ctypes.c_uint32),
                ("fd", ctypes.c_int32)]

class card_res(ctypes.Structure):
    _fields_ = [("fb_id_ptr", ctypes.c_uint64), ("crtc_id_ptr", ctypes.c_uint64),
                ("connector_id_ptr", ctypes.c_uint64), ("encoder_id_ptr", ctypes.c_uint64),
                ("count_fbs", ctypes.c_uint32), ("count_crtcs", ctypes.c_uint32),
                ("count_connectors", ctypes.c_uint32), ("count_encoders", ctypes.c_uint32),
                ("min_width", ctypes.c_uint32), ("max_width", ctypes.c_uint32),
                ("min_height", ctypes.c_uint32), ("max_height", ctypes.c_uint32)]

class mode_crtc(ctypes.Structure):
    _fields_ = [("set_connectors_ptr", ctypes.c_uint64), ("count_connectors", ctypes.c_uint32),
                ("crtc_id", ctypes.c_uint32), ("fb_id", ctypes.c_uint32),
                ("x", ctypes.c_uint32), ("y", ctypes.c_uint32),
                ("gamma_size", ctypes.c_uint32), ("mode_valid", ctypes.c_uint32),
                ("mode", ctypes.c_byte * 152)]

DRM_IOCTL_SET_CLIENT_CAP    = _IOW(0x0d, ctypes.sizeof(set_client_cap))
DRM_IOCTL_MODE_GETRESOURCES = _IOWR(0xA0, ctypes.sizeof(card_res))
DRM_IOCTL_MODE_GETCRTC      = _IOWR(0xA1, ctypes.sizeof(mode_crtc))
DRM_IOCTL_MODE_GETPLANERESOURCES = _IOWR(0xB5, ctypes.sizeof(get_plane_res))
DRM_IOCTL_MODE_GETPLANE     = _IOWR(0xB6, ctypes.sizeof(get_plane))
DRM_IOCTL_MODE_GETFB2       = _IOWR(0xCE, ctypes.sizeof(fb_cmd2))
DRM_IOCTL_PRIME_HANDLE_TO_FD = _IOWR(0x2D, ctypes.sizeof(prime_handle))

def fourcc(v):
    return ''.join(chr((v >> (8*i)) & 0xFF) for i in range(4))

def grab(fd):
    """Return (width, height, pitch, fmt, modifier, raw_bytes) of the plane
    currently scanning out, or None."""
    pres = get_plane_res()
    ioctl(fd, DRM_IOCTL_MODE_GETPLANERESOURCES, pres)
    ids = (ctypes.c_uint32 * pres.count_planes)()
    pres.plane_id_ptr = ctypes.addressof(ids)
    ioctl(fd, DRM_IOCTL_MODE_GETPLANERESOURCES, pres)
    for pid in ids:
        p = get_plane(); p.plane_id = pid
        ioctl(fd, DRM_IOCTL_MODE_GETPLANE, p)
        if not p.fb_id:
            continue
        fb = fb_cmd2(); fb.fb_id = p.fb_id
        try:
            ioctl(fd, DRM_IOCTL_MODE_GETFB2, fb)
        except OSError:
            continue
        ph = prime_handle(); ph.handle = fb.handles[0]
        try:
            ioctl(fd, DRM_IOCTL_PRIME_HANDLE_TO_FD, ph)
        except OSError:
            continue
        size = fb.pitches[0] * fb.height
        mm = mmap.mmap(ph.fd, size, mmap.MAP_SHARED, mmap.PROT_READ)
        data = mm[:]
        mm.close(); os.close(ph.fd)
        return (fb.width, fb.height, fb.pitches[0],
                fourcc(fb.pixel_format), fb.modifier[0], data)
    return None

def main():
    out = sys.argv[1]
    fd = os.open('/dev/dri/card0', os.O_RDWR)
    cap = set_client_cap(); cap.capability = 2; cap.value = 1  # UNIVERSAL_PLANES
    try:
        ioctl(fd, DRM_IOCTL_SET_CLIENT_CAP, cap)
    except OSError:
        pass
    g = grab(fd)
    os.close(fd)
    if g is None:
        sys.exit('no active plane fb')
    w, h, pitch, fmt, mod, data = g
    print('w=%d h=%d pitch=%d fmt=%s mod=%x' % (w, h, pitch, fmt, mod),
          file=sys.stderr)
    with open(out, 'wb') as f:
        f.write(data)

main()
