"""Loopback art proxy -- card images with truly transparent corners.

Kodi can only clip an image by baking the alpha into the texture itself:
the `*-corners.png` overlays used to paint an opaque fill over the JPEG's
square corners, which reads as a dark box whenever the backdrop behind a
card is light (the detail field veil). This proxy fetches the upstream
Plex image, rounds its corners with PIL and serves the result as a PNG
with a real alpha channel, cached on disk so each card pays the cost once.

`wrap()` is the single entry point used by the image resolvers; it falls
back to the original URL when the proxy cannot start, so cards degrade to
the old corner-cover look instead of breaking.
"""
import base64
import hashlib
import io
import os
import threading
import urllib.parse
import urllib.request

try:
    import xbmc
    import xbmcvfs
except ImportError:  # unit-test env: no Kodi runtime
    xbmc = None
    xbmcvfs = None

PORT = 8194
MASK_VERSION = 1
FETCH_TIMEOUT = 15
# PNGs are small (cards never exceed ~640px) but a whole library of
# posters adds up -- bound the cache and purge oldest first.
MAX_CACHE_FILES = 2400
PURGE_BATCH = 300

_port = None
_start_lock = threading.Lock()
_cache_dir = None
_locks = {}
_locks_lock = threading.Lock()


def _dir():
    global _cache_dir
    if _cache_dir is None:
        if xbmcvfs is not None:
            base = xbmcvfs.translatePath(
                'special://profile/addon_data/script.akasha.aura/')
        else:
            import tempfile
            base = tempfile.gettempdir()
        _cache_dir = os.path.join(base, 'artcache')
        try:
            os.makedirs(_cache_dir, exist_ok=True)
        except OSError:
            pass
    return _cache_dir


def ensure_started():
    """Start the loopback server once; return its port or None."""
    global _port
    if _port:
        return _port
    with _start_lock:
        if _port:
            return _port
        from http.server import BaseHTTPRequestHandler, \
            ThreadingHTTPServer

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                if self.path.split('?')[0] != '/art':
                    self.send_error(404)
                    return
                try:
                    params = urllib.parse.parse_qs(
                        urllib.parse.urlparse(self.path).query)
                    url = base64.urlsafe_b64decode(
                        params['u'][0].encode()).decode()
                    radius = int(params['r'][0])
                    width = int(params.get('w', ['0'])[0])
                    height = int(params.get('h', ['0'])[0])
                    png = _render(url, radius, width, height)
                    if png is None:
                        self.send_error(502)
                        return
                    self.send_response(200)
                    self.send_header('Content-Type', 'image/png')
                    self.send_header('Content-Length', str(len(png)))
                    self.send_header('Cache-Control', 'max-age=86400')
                    self.end_headers()
                    self.wfile.write(png)
                except Exception:
                    self.send_error(502)

            def log_message(self, *args):
                pass

        for bind_port in (PORT, 0):
            try:
                server = ThreadingHTTPServer(('127.0.0.1', bind_port),
                                             Handler)
                break
            except OSError:
                server = None
        if server is None:
            return None
        server.daemon_threads = True
        _port = server.server_address[1]
        threading.Thread(target=server.serve_forever,
                         kwargs={'poll_interval': 1}, daemon=True).start()
        return _port


def unwrap(url):
    """Reverse wrap(): the original upstream URL, or `url` unchanged."""
    if not url or '127.0.0.1' not in url or '/art?' not in url:
        return url
    try:
        params = urllib.parse.parse_qs(
            urllib.parse.urlparse(url).query)
        return base64.urlsafe_b64decode(params['u'][0].encode()).decode()
    except Exception:
        return url


def wrap(url, radius, width=None, height=None):
    """Return the proxy URL serving `url` with `radius`px rounded corners.

    `width`/`height` request a downscale before rounding (matches the card
    geometry when the source has no server-side sizing). Falls back to the
    original URL when the proxy is unavailable or inputs are empty."""
    if not url or not radius:
        return url
    port = ensure_started()
    if not port:
        return url
    params = {'u': base64.urlsafe_b64encode(url.encode()).decode(),
              'r': str(int(radius))}
    if width and height:
        params['w'], params['h'] = str(int(width)), str(int(height))
    return 'http://127.0.0.1:{}/art?{}'.format(
        port, urllib.parse.urlencode(params))


def _file_lock(path):
    with _locks_lock:
        lock = _locks.get(path)
        if lock is None:
            lock = _locks[path] = threading.Lock()
        return lock


def _render(url, radius, width, height):
    """Cached PNG bytes for (url, radius, size); None on fetch/failure."""
    key = 'v{}-{}.png'.format(
        MASK_VERSION,
        hashlib.sha256(
            '{}|{}|{}x{}'.format(url, radius, width, height)
            .encode()).hexdigest())
    path = os.path.join(_dir(), key)
    try:
        with open(path, 'rb') as f:
            return f.read()
    except OSError:
        pass
    with _file_lock(path):
        try:
            with open(path, 'rb') as f:
                return f.read()
        except OSError:
            pass
        try:
            data = _fetch(url)
            png = _round(data, radius, width, height)
        except Exception as e:
            if xbmc is not None:
                # Path only: the query can carry Plex/bearer tokens.
                safe = url.split('?')[0].split('|')[0][:80]
                xbmc.log('Akasha Aura art proxy: {} failed: {}'.format(
                    safe, e), xbmc.LOGWARNING)
            return None
        tmp = path + '.tmp'
        try:
            with open(tmp, 'wb') as f:
                f.write(png)
            os.replace(tmp, path)
        except OSError:
            pass
        _maybe_purge()
        return png


def _fetch(url):
    """Download `url`; honour Kodi's `url|Header=Value` option syntax so
    connector URLs keep their Authorization header."""
    headers = {'User-Agent': 'AkashaOSAura/1.0'}
    if '|' in url:
        url, _, opt = url.partition('|')
        for kv in opt.split('|'):
            k, _, v = kv.partition('=')
            if k:
                headers[k] = urllib.parse.unquote(v)
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=FETCH_TIMEOUT) as resp:
        return resp.read()


def _round(data, radius, width, height):
    """RGBA PNG bytes with anti-aliased `radius`px rounded corners."""
    from PIL import Image, ImageDraw
    im = Image.open(io.BytesIO(data)).convert('RGBA')
    if width and height and (im.width > width or im.height > height):
        im = im.resize((width, height), Image.LANCZOS)
    w, h = im.size
    radius = min(int(radius), w // 2, h // 2)
    if radius <= 0:
        out = io.BytesIO()
        im.save(out, 'PNG')
        return out.getvalue()
    # 4x supersampled mask keeps the corner edge smooth at card sizes.
    scale = 4
    mask = Image.new('L', (w * scale, h * scale), 0)
    d = ImageDraw.Draw(mask)
    d.rounded_rectangle((0, 0, w * scale - 1, h * scale - 1),
                        radius=radius * scale, fill=255)
    mask = mask.resize((w, h), Image.LANCZOS)
    im.putalpha(mask)
    out = io.BytesIO()
    im.save(out, 'PNG')
    return out.getvalue()


def _maybe_purge():
    """Bound the disk cache: drop the oldest files past the cap."""
    try:
        names = os.listdir(_dir())
    except OSError:
        return
    if len(names) <= MAX_CACHE_FILES:
        return
    entries = []
    for name in names:
        p = os.path.join(_dir(), name)
        try:
            entries.append((os.path.getmtime(p), p))
        except OSError:
            pass
    entries.sort()
    for _, p in entries[:PURGE_BATCH]:
        try:
            os.remove(p)
        except OSError:
            pass
