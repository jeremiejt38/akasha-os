"""Akasha Ambient — photo credit extraction.

Pure stdlib (no `xbmc*`). The bundled Wikimedia Commons pack encodes the
author in the file name (`..._Photo_by_Giles_Laurent.jpg`); this module
turns any file name into a short displayable credit line, Google TV
Ambient Mode style. Returns an empty string when nothing can be derived.
"""
import os
import re

_BY_PATTERN = re.compile(r'_+photo_+by_+(.+)$', re.IGNORECASE)
_GENERIC_BY_PATTERN = re.compile(r'_+by_+(.+)$', re.IGNORECASE)
_LEADING_INDEX = re.compile(r'^\d+[_\- ]+')


def _humanize(name):
    text = re.sub(r'[_\-]+', ' ', name).strip()
    return re.sub(r'\s{2,}', ' ', text)


def _title_case(name):
    return ' '.join(
        word if word.startswith('(') else word.capitalize()
        for word in _humanize(name).split(' ')
    )


def credit_for(path):
    """Best-effort credit label for a photo file path.

    `039_Northern_lights_over_X_Photo_by_Giles_Laurent.jpg`
        -> 'Northern lights over X · Giles Laurent'
    `Sunset_by_A._Photographer.jpg` -> 'Sunset · A. Photographer'
    `random_photo.jpg`              -> 'Random photo' (title only)
    """
    base = os.path.splitext(os.path.basename(path or ''))[0]
    if not base:
        return ''
    base = _LEADING_INDEX.sub('', base)

    match = _BY_PATTERN.search(base)
    if match is None:
        match = _GENERIC_BY_PATTERN.search(base)
    if match is not None:
        title = _humanize(base[:match.start()])
        author = _title_case(match.group(1))
        return '{} · {}'.format(title, author) if title else author

    return _title_case(base)


def frame_credit(paths):
    """Single credit line for a displayed frame (1 photo or a portrait pair)."""
    labels = [credit_for(p) for p in paths]
    labels = [l for l in labels if l]
    if len(labels) > 1 and labels[0] == labels[1]:
        labels = labels[:1]
    return '  |  '.join(labels)
