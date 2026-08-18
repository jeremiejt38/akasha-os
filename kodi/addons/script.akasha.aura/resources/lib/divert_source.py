"""Akasha Aura — pure parsers for raw Plex JSON coming from the connector.

`akasha-os-connector` proxies raw Plex Media Server JSON responses (cached),
so these mirror the shape-normalising logic already in plex_client.py, but
resolve image URLs via a caller-supplied resolver (typically
`ConnectorClient.image_url`) instead of embedding the Plex admin token
directly — the whole point of routing through the connector.

No dependency on xbmc*, testable with plain `python3 -m unittest`.
"""


def _media_container(data):
    if not isinstance(data, dict):
        return {}
    return data.get('MediaContainer', data)


def parse_sections(raw_json, section_types=('movie', 'show')):
    """Return video library sections from a raw `/library/sections` payload."""
    mc = _media_container(raw_json)
    return [
        {
            'key': str(item.get('key')),
            'title': item.get('title') or 'Section',
            'type': item.get('type'),
        }
        for item in mc.get('Directory', [])
        if item.get('type') in section_types
    ]


def parse_genres(raw_json):
    """Return genre names from a raw `/library/sections/{key}/genre` payload.

    Plex's `/library/sections/{key}/genre` endpoint returns each genre as a
    `Directory` entry with a `title` field (not `tag`, which is used for
    per-item genre tags on movies/shows themselves, a different response
    shape) -- confirmed against a real server on 2026-08-18.
    """
    mc = _media_container(raw_json)
    return [str(item.get('title')) for item in mc.get('Directory', []) if item.get('title')]


def parse_total_size(raw_json):
    """Return the total item count of a paginated Plex payload, or None.

    Plex includes `totalSize` (falling back to `size` for non-paginated
    responses) in every `MediaContainer`, at no extra request cost -- so the
    real total can be shown immediately alongside the first page, without a
    separate "count" round-trip (see docs/aura/decisions.md, plan a3f9c2e1).
    """
    mc = _media_container(raw_json)
    total = mc.get('totalSize', mc.get('size'))
    return int(total) if total is not None else None


def item_subtitle(item):
    """Return a short second line for a video item (episode tag, or year).

    Mirrors the Plex web/app pattern: "S{season} - E{episode}" for TV
    episodes, the release year for movies/shows, or nothing if neither is
    available.
    """
    season = item.get('season')
    index = item.get('index')
    if season is not None and index is not None:
        return 'S{} - E{}'.format(season, index)
    year = item.get('year')
    if year:
        return str(year)
    return ''


def parse_metadata_list(raw_json, image_resolver):
    """Return normalised video dicts from a raw Metadata-bearing payload.

    `image_resolver(plex_path) -> url` builds a displayable URL for a Plex
    image path (e.g. `ConnectorClient.image_url`).
    """
    mc = _media_container(raw_json)
    items = []
    for item in mc.get('Metadata', []):
        thumb = item.get('thumb') or ''
        art = item.get('art') or ''
        items.append({
            'title': item.get('title') or 'Sans titre',
            'type': item.get('type') or 'video',
            'rating_key': item.get('ratingKey'),
            'parent_rating_key': item.get('parentRatingKey'),
            'index': item.get('index'),
            'season': item.get('parentIndex'),
            'show_title': item.get('grandparentTitle') or '',
            'year': item.get('year'),
            'originally_available_at': item.get('originallyAvailableAt'),
            'summary': item.get('summary') or '',
            'thumb_url': image_resolver(thumb) if thumb else '',
            'art_url': image_resolver(art) if art else '',
        })
    return items
