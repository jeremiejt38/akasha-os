#!/usr/bin/env python3
"""Download a default pack of landscape videos from Wikimedia Commons.

Called by scripts/install.sh during deployment. Uses only stdlib so it can be
exercised on the build host and on LibreELEC without extra dependencies.

The selected videos are freely licensed (CC-BY / CC0 / public domain) and
hosted on Wikimedia Commons. They are fetched by title, resolved through the
MediaWiki API, and written to the given output folder.
"""
import argparse
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request

COMMONS_API = 'https://commons.wikimedia.org/w/api.php'
USER_AGENT = 'AkashaOS/0.15 (+https://github.com/jeremiejt38/akasha-os)'
MANIFEST_NAME = '.akasha-ambient-videos'

# Curated static-camera landscape videos available on Wikimedia Commons in
# 1920x1080. All are freely licensed (CC-BY / CC0 / public domain). The scenes
# are chosen for subtle, looping natural motion (waves, flowing water) rather
# than camera movement, similar to Google TV / Apple TV ambient modes.
DEFAULT_TITLES = [
    'File:Ocean waves at Lækjavik beach, Iceland.webm',
    'File:Waves-1013354, Dingle Peninsula, Co. Kerry, Ireland.webm',
    'File:Yudaki - tochigi - 2021 Oct 29.webm',
    'File:Triberger Wasserfälle (Triberg im Schwarzwald).webm',
    'File:Godachinmalki waterfalls video.webm',
    'File:Partnachklamm.ogv',
    'File:River flowing.webm',
]


def _api_request(params):
    query = urllib.parse.urlencode(params)
    url = '{}?{}'.format(COMMONS_API, query)
    req = urllib.request.Request(url, headers={'User-Agent': USER_AGENT})
    with urllib.request.urlopen(req, timeout=60) as response:
        return json.loads(response.read().decode('utf-8'))


def _fetch_imageinfo(titles):
    """Return a mapping title -> imageinfo dict for the given Commons titles."""
    params = {
        'action': 'query',
        'titles': '|'.join(titles),
        'prop': 'imageinfo',
        'iiprop': 'url|size|mime',
        'format': 'json',
        'origin': '*',
    }
    data = _api_request(params)
    info = {}
    for page in data.get('query', {}).get('pages', {}).values():
        title = page.get('title')
        if title and 'imageinfo' in page:
            info[title] = page['imageinfo'][0]
    return info


def _download(url, dest, timeout=120):
    req = urllib.request.Request(url, headers={'User-Agent': USER_AGENT})
    with urllib.request.urlopen(req, timeout=timeout) as response:
        with open(dest, 'wb') as f:
            f.write(response.read())


def _is_landscape_ii(ii, min_width=1280, min_height=720):
    """True if the imageinfo describes a landscape video we want to keep."""
    width = ii.get('width') or 0
    height = ii.get('height') or 0
    mime = ii.get('mime') or ''
    if width <= 0 or height <= 0:
        return False
    if width < min_width or height < min_height:
        return False
    if width < height:
        return False  # skip portrait
    if not (mime.startswith('video/') or mime in ('application/ogg', 'application/octet-stream')):
        return False
    return True


def _safe_filename(title, url):
    """Derive a local filename from the Commons title or URL."""
    # Prefer the URL basename, but fall back to the title slug.
    basename = os.path.basename(urllib.parse.urlparse(url).path)
    if basename and '.' in basename:
        return urllib.parse.unquote(basename)
    # Strip namespace prefix and sanitize.
    name = title
    if name.startswith('File:'):
        name = name[5:]
    name = name.replace(' ', '_')
    for ch in ['/', '\\', '<', '>', ':', '"', '|', '?', '*']:
        name = name.replace(ch, '_')
    if not name.lower().endswith(('.webm', '.ogv', '.mp4', '.mkv')):
        name += '.webm'
    return urllib.parse.unquote(name)


def _load_manifest(out_dir):
    """Return the set of filenames previously downloaded by this script."""
    path = os.path.join(out_dir, MANIFEST_NAME)
    if not os.path.exists(path):
        return set()
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return {line.strip() for line in f if line.strip()}
    except OSError:
        return set()


def _save_manifest(out_dir, filenames):
    """Write the manifest of filenames downloaded by this run."""
    path = os.path.join(out_dir, MANIFEST_NAME)
    try:
        with open(path, 'w', encoding='utf-8') as f:
            for name in sorted(filenames):
                f.write('{0}\n'.format(name))
    except OSError as e:
        print('ambient-download-videos: failed to write manifest: {}'.format(e),
              file=sys.stderr)


def fetch_landscape_videos(out_dir, titles=DEFAULT_TITLES, timeout=120):
    """Download the configured videos into `out_dir`.

    Returns the number of videos actually downloaded. Files already present are
    skipped so re-runs are fast. Videos from a previous default pack are
    removed so the default content can be updated between releases without
    leaving stale files.
    """
    if not titles:
        return 0

    os.makedirs(out_dir, exist_ok=True)

    try:
        infos = _fetch_imageinfo(titles)
    except (OSError, urllib.error.URLError, json.JSONDecodeError) as e:
        print('ambient-download-videos: failed to query Commons API: {}'.format(e),
              file=sys.stderr)
        return 0

    # Determine the target filenames first so we only remove stale default
    # videos while preserving user-added content and avoiding unnecessary
    # re-downloads.
    target_filenames = set()
    for title in titles:
        ii = infos.get(title)
        if not ii or not _is_landscape_ii(ii):
            continue
        url = ii.get('url')
        if not url:
            continue
        target_filenames.add(_safe_filename(title, url))

    previous = _load_manifest(out_dir)
    for name in previous:
        if name in target_filenames:
            continue
        full = os.path.join(out_dir, name)
        if os.path.exists(full):
            print('Removing stale default video: {}'.format(full))
            try:
                os.remove(full)
            except OSError:
                pass

    downloaded = 0
    current_filenames = set()
    for title in titles:
        ii = infos.get(title)
        if not ii:
            print('ambient-download-videos: no info for {}'.format(title), file=sys.stderr)
            continue
        if not _is_landscape_ii(ii):
            print('ambient-download-videos: skipping {} ({}x{} {})'.format(
                title, ii.get('width'), ii.get('height'), ii.get('mime')),
                file=sys.stderr)
            continue

        url = ii.get('url')
        if not url:
            print('ambient-download-videos: no URL for {}'.format(title), file=sys.stderr)
            continue

        dest = os.path.join(out_dir, _safe_filename(title, url))
        current_filenames.add(os.path.basename(dest))
        if os.path.exists(dest):
            size = os.path.getsize(dest)
            if size == ii.get('size'):
                downloaded += 1
                print('Already present: {}'.format(dest))
                continue
            print('ambient-download-videos: re-downloading {} (size mismatch)'.format(dest),
                  file=sys.stderr)

        try:
            print('Downloading {} -> {}'.format(title, dest))
            _download(url, dest, timeout=timeout)
            downloaded += 1
            print('Downloaded: {}'.format(dest))
        except (OSError, urllib.error.URLError) as e:
            print('ambient-download-videos: failed to download {}: {}'.format(url, e),
                  file=sys.stderr)
            current_filenames.discard(os.path.basename(dest))
            if os.path.exists(dest):
                try:
                    os.remove(dest)
                except OSError:
                    pass

    _save_manifest(out_dir, current_filenames)
    return downloaded


def main():
    parser = argparse.ArgumentParser(
        description='Download freely licensed landscape videos from Wikimedia Commons.',
    )
    parser.add_argument('out_dir', help='Directory to write videos into.')
    parser.add_argument(
        '-t', '--timeout', type=int, default=120,
        help='HTTP timeout in seconds (default: 120).',
    )
    args = parser.parse_args()

    downloaded = fetch_landscape_videos(args.out_dir, timeout=args.timeout)
    if downloaded > 0:
        print('Downloaded {} video(s) to {}'.format(downloaded, args.out_dir))
        return 0
    print('No Commons videos downloaded; leaving folder unchanged.', file=sys.stderr)
    return 1


if __name__ == '__main__':
    sys.exit(main())
