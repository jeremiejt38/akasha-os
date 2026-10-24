#!/usr/bin/env python3
"""Frame-rate + motion profiler via DRM scanout.

Grabs at max speed, stores per-frame: timestamp, content hash (subsampled),
and the y-position of the poster-band top edge (row-mean luminance edge
detect). No pixel data kept -> tiny memory. Output: prof.txt lines
`t hash yedge meandiff`.
"""
import ctypes, hashlib, mmap, os, sys, time
libc = ctypes.CDLL('libc.so.6', use_errno=True)

def ioctl(fd, req, arg):
    r = libc.ioctl(fd, ctypes.c_ulong(req), ctypes.byref(arg))
    if r < 0:
        raise OSError(ctypes.get_errno(), os.strerror(ctypes.get_errno()))

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

DRM_IOCTL_SET_CLIENT_CAP = _IOW(0x0d, 16)
DRM_IOCTL_MODE_GETPLANERESOURCES = _IOWR(0xB5, 16)
DRM_IOCTL_MODE_GETPLANE = _IOWR(0xB6, 56)
DRM_IOCTL_MODE_GETFB2 = _IOWR(0xCE, 104)
DRM_IOCTL_PRIME_HANDLE_TO_FD = _IOWR(0x2D, 12)

# Sample band: poster strip, subsampled rows for speed
Y0, Y1, X0, X1 = 60, 900, 130, 1500
ROW_STRIDE = 8          # every 8th row
COL_STRIDE = 6          # every 6th px (24 bytes)

def grab(fd):
    pr = get_plane_res()
    try:
        ioctl(fd, DRM_IOCTL_MODE_GETPLANERESOURCES, pr)
    except OSError:
        return None
    if not pr.count_planes:
        return None
    arr = (ctypes.c_uint32 * pr.count_planes)()
    pr.plane_id_ptr = ctypes.addressof(arr)
    ioctl(fd, DRM_IOCTL_MODE_GETPLANERESOURCES, pr)
    for pid in arr:
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
        return fb.pitches[0], data
    return None

def analyze(pitch, data):
    """Subsampled hash + vertical edge position + mean luma."""
    h = hashlib.md5()
    rows = []
    nbytes = len(data)
    for r in range(0, (Y1 - Y0), ROW_STRIDE):
        base = r * pitch + X0 * 4
        seg = data[base: base + (X1 - X0) * 4]
        sub = seg[0: len(seg): COL_STRIDE * 4]
        h.update(sub)
        # mean of B channel approx luma
        rows.append(sum(sub[0::4]) / max(1, len(sub[0::4])))
    # edge: first row from top whose mean exceeds threshold
    thresh = 40
    yedge = -1
    for i, m in enumerate(rows):
        if m > thresh:
            yedge = Y0 + i * ROW_STRIDE
            break
    return h.hexdigest()[:10], yedge

def main():
    secs = float(sys.argv[1]); out = sys.argv[2]
    fd = os.open('/dev/dri/card0', os.O_RDWR)
    cap = set_client_cap(); cap.capability = 2; cap.value = 1
    try:
        ioctl(fd, DRM_IOCTL_SET_CLIENT_CAP, cap)
    except OSError:
        pass
    f = open(out, 'w')
    t0 = time.monotonic(); deadline = t0 + secs
    n = 0
    while time.monotonic() < deadline:
        ts = time.monotonic()
        g = grab(fd)
        if g is None:
            continue
        hh, ye = analyze(*g)
        f.write('%.4f %s %d\n' % (ts - t0, hh, ye))
        n += 1
    f.close(); os.close(fd)
    print('grabs=%d' % n)

main()
