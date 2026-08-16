#!/usr/bin/env python3
"""Download a default pack of public-domain Earth images from NASA EPIC.

Called by scripts/install.sh during deployment. Uses only stdlib so it can be
exercised on the build host and on LibreELEC without extra dependencies.

EPIC (Earth Polychromatic Imaging Camera) images are produced by NASA/NOAA and
are in the public domain. This script fetches the most recent natural-colour
image set and downloads a configurable number of 2048x2048 PNG frames into the
given output folder.
"""
import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.request

EPIC_INDEX_URL = 'https://epic.gsfc.nasa.gov/api/natural'
EPIC_IMAGE_URL = 'https://epic.gsfc.nasa.gov/archive/natural/{date}/png/{filename}.png'
DEFAULT_COUNT = 12


def _fetch_json(url, timeout=30):
    with urllib.request.urlopen(url, timeout=timeout) as response:
        return json.loads(response.read().decode('utf-8'))


def _parse_date(image_date):
    """Extract YYYY/MM/DD from the 'date' field returned by EPIC."""
    match = re.match(r'(\d{4})-(\d{2})-(\d{2})', image_date)
    if not match:
        raise ValueError('Cannot parse EPIC date: {}'.format(image_date))
    return '{}/{}/{}'.format(match.group(1), match.group(2), match.group(3))


def _download(url, dest, timeout=60):
    with urllib.request.urlopen(url, timeout=timeout) as response:
        with open(dest, 'wb') as f:
            f.write(response.read())


def fetch_epic_photos(out_dir, count=DEFAULT_COUNT, timeout=30):
    """Download up to `count` recent EPIC photos into `out_dir`.

    Returns the number of images actually downloaded, or 0 if none.
    """
    if count <= 0:
        return 0

    try:
        os.makedirs(out_dir, exist_ok=True)
        entries = _fetch_json(EPIC_INDEX_URL, timeout=timeout)
    except (OSError, urllib.error.URLError, json.JSONDecodeError, ValueError) as e:
        print('ambient-download-photos: failed to fetch EPIC index: {}'.format(e),
              file=sys.stderr)
        return 0

    if not entries:
        print('ambient-download-photos: EPIC index is empty', file=sys.stderr)
        return 0

    first_date = entries[0].get('date')
    if not first_date:
        print('ambient-download-photos: EPIC entry missing date', file=sys.stderr)
        return 0

    date_path = _parse_date(first_date)

    # EPIC publishes multiple frames per day (every ~1 hour). Pick evenly
    # spaced images to get varied lighting/continents.
    selected = []
    total = len(entries)
    if total <= count:
        selected = entries
    else:
        step = total / float(count)
        for i in range(count):
            idx = int(round(i * step))
            if idx >= total:
                idx = total - 1
            selected.append(entries[idx])

    downloaded = 0
    for item in selected:
        filename = item.get('image')
        if not filename:
            continue
        url = EPIC_IMAGE_URL.format(date=date_path, filename=filename)
        dest = os.path.join(out_dir, '{}.png'.format(filename))
        if os.path.exists(dest):
            downloaded += 1
            continue
        try:
            _download(url, dest, timeout=timeout)
            downloaded += 1
            print('Downloaded: {}'.format(dest))
        except (OSError, urllib.error.URLError) as e:
            print('ambient-download-photos: failed to download {}: {}'.format(url, e),
                  file=sys.stderr)

    return downloaded


def main():
    parser = argparse.ArgumentParser(
        description='Download public-domain Earth photos from NASA EPIC.',
    )
    parser.add_argument('out_dir', help='Directory to write PNG images into.')
    parser.add_argument(
        '-n', '--count', type=int, default=DEFAULT_COUNT,
        help='Number of images to download (default: {}).'.format(DEFAULT_COUNT),
    )
    parser.add_argument(
        '-t', '--timeout', type=int, default=30,
        help='HTTP timeout in seconds (default: 30).',
    )
    args = parser.parse_args()

    downloaded = fetch_epic_photos(args.out_dir, count=args.count, timeout=args.timeout)
    if downloaded > 0:
        print('Downloaded {} EPIC photo(s) to {}'.format(downloaded, args.out_dir))
        return 0
    print('No EPIC photos downloaded; leaving folder unchanged.', file=sys.stderr)
    return 1


if __name__ == '__main__':
    sys.exit(main())
