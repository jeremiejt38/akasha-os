#!/usr/bin/env python3
"""Download the default pack of landscape photos from Wikimedia Commons.

Called by scripts/install.sh during deployment. Uses only stdlib so it can be
exercised on the build host and on LibreELEC without extra dependencies.

The selected photos are all Wikimedia Commons "Featured pictures" (reviewed
for quality and freely licensed: CC-BY / CC-BY-SA / public domain), landscape
orientation, high resolution, static scenery (mountains, deserts, canyons,
lakes, aurorae) -- the same kind of curated "wow" pack used by Google TV /
Apple TV ambient modes. They are fetched by title, resolved through the
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
USER_AGENT = 'AkashaOS/0.20 (+https://github.com/jeremiejt38/akasha-os)'
MANIFEST_NAME = '.akasha-ambient-photos'

# Curated landscape photos from Wikimedia Commons' "Featured pictures"
# category: reviewed for quality, freely licensed, landscape orientation,
# high resolution, varied scenery so the slideshow doesn't feel repetitive.
DEFAULT_TITLES = [
    'File:039 Northern lights over Mývatn (Iceland) Photo by Giles Laurent.jpg',
    'File:084 Sun setting in the Namib desert Photo by Giles Laurent.jpg',
    'File:Aurora and perseids.jpg',
    'File:Dombay, Dzhuguturlyuchat massif and glacier, Caucasus Mountains, Karachay-Cherkessia.jpg',
    'File:Feuersteinferner und Feuersteine II.jpg',
    'File:Lower Antelope Canyon November 2018 017.jpg',
    'File:Ergaki, Mountain lake Skazka, Rock formations, Sayan Mountains, Russia.jpg',
    'File:Angelus Hut in the winter, Nelson Lakes National Park, New Zealand.jpg',
    'File:Olkhon Island, Capes, cliffs at sunset, Lake Baikal, Russia.jpg',
    'File:Lake Sylvester during the sunrise, Kahurangi, New Zealand.jpg',
    'File:Li Phi falls at sunset with orange sky and a fishing boat in Don Khon Si Phan Don Laos.jpg',
    'File:Gentau Pic du Midi Ossau.jpg',
    'File:Colorful sky with orange clouds reflecting in the water of a paddy field, at sunset, Vang Vieng, Laos.jpg',
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
    """True if the imageinfo describes a landscape photo we want to keep."""
    width = ii.get('width') or 0
    height = ii.get('height') or 0
    mime = ii.get('mime') or ''
    if width <= 0 or height <= 0:
        return False
    if width < min_width or height < min_height:
        return False
    if width < height:
        return False  # skip portrait
    if not mime.startswith('image/'):
        return False
    return True


def _safe_filename(title, url):
    """Derive a local filename from the Commons title or URL."""
    basename = os.path.basename(urllib.parse.urlparse(url).path)
    if basename and '.' in basename:
        return urllib.parse.unquote(basename)
    name = title
    if name.startswith('File:'):
        name = name[5:]
    name = name.replace(' ', '_')
    for ch in ['/', '\\', '<', '>', ':', '"', '|', '?', '*']:
        name = name.replace(ch, '_')
    if not name.lower().endswith(('.jpg', '.jpeg', '.png')):
        name += '.jpg'
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
        print('ambient-download-photos: failed to write manifest: {}'.format(e),
              file=sys.stderr)


def fetch_landscape_photos(out_dir, titles=DEFAULT_TITLES, timeout=120):
    """Download the configured photos into `out_dir`.

    Returns the number of photos actually downloaded. Files already present
    are skipped so re-runs are fast. Photos from a previous default pack are
    removed so the default content can be updated between releases without
    leaving stale files (user-added photos elsewhere in the folder are left
    untouched since they are not part of the manifest).
    """
    if not titles:
        return 0

    os.makedirs(out_dir, exist_ok=True)

    try:
        infos = _fetch_imageinfo(titles)
    except (OSError, urllib.error.URLError, json.JSONDecodeError) as e:
        print('ambient-download-photos: failed to query Commons API: {}'.format(e),
              file=sys.stderr)
        return 0

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
            print('Removing stale default photo: {}'.format(full))
            try:
                os.remove(full)
            except OSError:
                pass

    downloaded = 0
    current_filenames = set()
    for title in titles:
        ii = infos.get(title)
        if not ii:
            print('ambient-download-photos: no info for {}'.format(title), file=sys.stderr)
            continue
        if not _is_landscape_ii(ii):
            print('ambient-download-photos: skipping {} ({}x{} {})'.format(
                title, ii.get('width'), ii.get('height'), ii.get('mime')),
                file=sys.stderr)
            continue

        url = ii.get('url')
        if not url:
            print('ambient-download-photos: no URL for {}'.format(title), file=sys.stderr)
            continue

        dest = os.path.join(out_dir, _safe_filename(title, url))
        current_filenames.add(os.path.basename(dest))
        if os.path.exists(dest):
            size = os.path.getsize(dest)
            if size == ii.get('size'):
                downloaded += 1
                print('Already present: {}'.format(dest))
                continue
            print('ambient-download-photos: re-downloading {} (size mismatch)'.format(dest),
                  file=sys.stderr)

        try:
            print('Downloading {} -> {}'.format(title, dest))
            _download(url, dest, timeout=timeout)
            downloaded += 1
            print('Downloaded: {}'.format(dest))
        except (OSError, urllib.error.URLError) as e:
            print('ambient-download-photos: failed to download {}: {}'.format(url, e),
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
        description='Download freely licensed landscape photos from Wikimedia Commons.',
    )
    parser.add_argument('out_dir', help='Directory to write photos into.')
    parser.add_argument(
        '-t', '--timeout', type=int, default=120,
        help='HTTP timeout in seconds (default: 120).',
    )
    args = parser.parse_args()

    downloaded = fetch_landscape_photos(args.out_dir, timeout=args.timeout)
    if downloaded > 0:
        print('Downloaded {} photo(s) to {}'.format(downloaded, args.out_dir))
        return 0
    print('No Commons photos downloaded; leaving folder unchanged.', file=sys.stderr)
    return 1


if __name__ == '__main__':
    sys.exit(main())
