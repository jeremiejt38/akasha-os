#!/usr/bin/env python3
"""Burst-capture DRM scanout, raw cropped frames, low memory.

Usage: drm_film.py <seconds> <outdir>
Frames: outdir/f_%04d.raw  (1920 x 520 x 4 BGRX, crop y=300..820)
"""
import ctypes, mmap, os, sys, time
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

DRM_IOCTL_SET_CLIENT_CAP = _IOW(0x0d, ctypes.sizeof(set_client_cap))
DRM_IOCTL_MODE_GETPLANERESOURCES = _IOWR(0xB5, ctypes.sizeof(get_plane_res))
DRM_IOCTL_MODE_GETPLANE = _IOWR(0xB6, ctypes.sizeof(get_plane))
DRM_IOCTL_MODE_GETFB2 = _IOWR(0xCE, ctypes.sizeof(fb_cmd2))
DRM_IOCTL_PRIME_HANDLE_TO_FD = _IOWR(0x2D, ctypes.sizeof(prime_handle))

Y0, Y1 = 300, 820   # crop zone: row titles + posters

def grab(fd):
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
        mm = mmap.mmap(ph.fd, fb.pitches[0] * fb.height,
                       mmap.MAP_SHARED, mmap.PROT_READ)
        data = mm[Y0 * fb.pitches[0]: Y1 * fb.pitches[0]]
        mm.close(); os.close(ph.fd)
        return fb.width, Y1 - Y0, fb.pitches[0], data
    return None

def main():
    secs = float(sys.argv[1]); outdir = sys.argv[2]
    os.makedirs(outdir, exist_ok=True)
    fd = os.open('/dev/dri/card0', os.O_RDWR)
    cap = set_client_cap(); cap.capability = 2; cap.value = 1
    try:
        ioctl(fd, DRM_IOCTL_SET_CLIENT_CAP, cap)
    except OSError:
        pass
    frames = []
    times = open(os.path.join(outdir, 'times.txt'), 'w')
    t0 = time.monotonic()
    deadline = t0 + secs
    n = i = 0
    while time.monotonic() < deadline:
        ts = time.monotonic()
        g = grab(fd)
        if g is not None:
            if n % 3 == 0:          # ~18fps at ~55fps grab speed
                with open(os.path.join(outdir, 'f_%04d.raw' % i), 'wb') as f:
                    f.write(g[3])
                times.write('%d %.3f\n' % (i, ts - t0))
                i += 1
            n += 1
    os.close(fd)
    times.close()
    print('frames=%d w=%d h=%d pitch=%d' % (i, g[0], g[1], g[2]))

main()
