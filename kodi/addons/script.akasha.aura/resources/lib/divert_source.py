"""Akasha Aura — pure parsers for raw Plex JSON coming from the connector.

`akasha-os-connector` proxies raw Plex Media Server JSON responses (cached),
so these mirror the shape-normalising logic already in plex_client.py, but
resolve image URLs via a caller-supplied resolver (typically
`ConnectorClient.image_url`) instead of embedding the Plex admin token
directly — the whole point of routing through the connector.

No dependency on xbmc*, testable with plain `python3 -m unittest`.
"""

import i18n


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
            'title': item.get('title') or i18n.tr(33076),
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


# English -> French display names for the genres Plex commonly returns
# (its metadata agents -- TMDb/TheTVDB -- report genre names in whatever
# language the *source* database uses, English by default regardless of
# Kodi/Akasha's own interface language). Covers the standard TMDb/Plex
# genre vocabulary; anything not listed here is shown as-is rather than
# raising, since new/uncommon genres do turn up in real libraries.
GENRE_TRANSLATIONS_FR = {
    'Action': 'Action',
    'Action/Adventure': 'Action/Aventure',
    'Adventure': 'Aventure',
    'Animation': 'Animation',
    'Anime': 'Anime',
    'Biography': 'Biographie',
    'Children': 'Enfants',
    'Comedy': 'Comedie',
    'Crime': 'Crime',
    'Documentary': 'Documentaire',
    'Drama': 'Drame',
    'Family': 'Famille',
    'Fantasy': 'Fantastique',
    'Film-Noir': 'Film noir',
    'Food': 'Cuisine',
    'History': 'Histoire',
    'Horror': 'Horreur',
    'Indie': 'Independant',
    'Kids': 'Enfants',
    'Martial Arts': 'Arts martiaux',
    'Mini-Series': 'Mini-serie',
    'Music': 'Musique',
    'Musical': 'Comedie musicale',
    'Mystery': 'Mystere',
    'News': 'Actualites',
    'Podcast': 'Podcast',
    'Reality': 'Tele-realite',
    'Reality-TV': 'Tele-realite',
    'Romance': 'Romance',
    'Sci-Fi & Fantasy': 'Science-fiction et fantastique',
    'Science Fiction': 'Science-fiction',
    'Short': 'Court-metrage',
    'Soap': 'Feuilleton',
    'Sport': 'Sport',
    'Stoner Movie': 'Film Stoner',
    'Suspense': 'Suspense',
    'Talk': 'Talk-show',
    'Talk Show': 'Talk-show',
    'Thriller': 'Thriller',
    'TV Movie': 'Telefilm',
    'War': 'Guerre',
    'War & Politics': 'Guerre et politique',
    'Western': 'Western',
}


def translate_genre_fr(name):
    """Best-effort English -> French genre display name, see
    GENRE_TRANSLATIONS_FR. Falls back to the original name unchanged when
    not in the table, rather than hiding/erroring on unfamiliar genres."""
    return GENRE_TRANSLATIONS_FR.get(name, name)


def display_genre(name):
    """Genre label in the UI language: Plex serves English genre names,
    which only need translating when the interface runs in French."""
    import i18n
    if i18n._lang() == 'en':
        return name
    return translate_genre_fr(name)


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


def _tags(raw_item, key):
    """Return tag names from a Plex `Genre`/`Director`/`Writer`/`Role` array."""
    return [str(tag['tag']) for tag in raw_item.get(key) or [] if tag.get('tag')]


def _image_of_type(raw_item, image_type):
    """Return the `url` of the first `Image` entry of the given type."""
    for image in raw_item.get('Image') or []:
        if image.get('type') == image_type and image.get('url'):
            return image['url']
    return ''


def _first_media(raw_item):
    medias = raw_item.get('Media') or []
    return medias[0] if medias and isinstance(medias[0], dict) else {}


def _streams(raw_item, stream_type):
    media = _first_media(raw_item)
    parts = media.get('Part') or []
    streams = (parts[0].get('Stream') or []) if parts else []
    return [s for s in streams if s.get('streamType') == stream_type]


def _video_label(raw_item):
    """Plex-style media badge, e.g. '4K HDR10', 'HD', 'SD'.

    Empty when the item carries no Media at all (shows, seasons,
    collections) -- a bare 'SD' badge on a series page is meaningless."""
    media = _first_media(raw_item)
    if not media:
        return ''
    resolution = str(media.get('videoResolution') or '').lower()
    if resolution in ('4k', '2160', '2160p'):
        base = '4K'
    elif resolution in ('1080', '1080p'):
        base = '1080p'
    elif resolution in ('720', '720p'):
        base = '720p'
    else:
        base = resolution.upper() if resolution else 'SD'
    hdr = ''
    for stream in _streams(raw_item, 1):
        trc = str(stream.get('colorTrc') or stream.get('colourTrc') or '').lower()
        if stream.get('DOVIPresent') or stream.get('doviPresent'):
            hdr = 'DV'
            break
        if 'smpte2084' in trc or 'bt2020' in trc:
            hdr = 'HDR10'
            break
        if 'arib-std-b67' in trc or 'hlg' in trc:
            hdr = 'HLG'
            break
    codec = str(media.get('videoCodec') or '').upper()
    parts = [base]
    if hdr:
        parts.append(hdr)
    if codec:
        parts.append(codec)
    return ' '.join(parts)


def _audio_label(raw_item):
    """Plex-style audio badge, e.g. 'French EAC3 5.1'."""
    for stream in _streams(raw_item, 2):
        language = stream.get('language') or stream.get('languageTag') or ''
        codec = str(stream.get('codec') or '').upper()
        channels = stream.get('channels')
        layout = {2: '2.0', 6: '5.1', 8: '7.1'}.get(channels, str(channels) if channels else '')
        label = ' '.join(p for p in (language, codec, layout) if p)
        if label:
            return label
    return ''


def _subtitle_label(raw_item):
    """Short subtitle summary, e.g. 'French SRT' (first sub) or '3 sous-titres'."""
    subs = _streams(raw_item, 3)
    if not subs:
        return ''
    first = subs[0]
    language = first.get('language') or first.get('languageTag') or ''
    codec = str(first.get('codec') or first.get('format') or '').upper()
    label = ' '.join(p for p in (language, codec) if p)
    return label or '{} sous-titres'.format(len(subs))


def _content_rating_display(raw_item):
    """Strip the locale prefix from contentRating ('fr/10' -> '10')."""
    rating = str(raw_item.get('contentRating') or '')
    if '/' in rating:
        rating = rating.rsplit('/', 1)[-1]
    return rating


def build_video_item(raw_item, image_resolver):
    """Normalise one raw Plex `Metadata` entry into a display dict.

    `image_resolver(plex_path, width=None, height=None) -> url` builds a
    displayable URL for a Plex image path (e.g. `ConnectorClient.image_url`,
    or `server+path?token=` for the direct Plex client). Resolvers that
    support it (direct Plex) downscale server-side; the others ignore the
    size hints. Carries every field the Plex-style UI needs:
    posters, fanart, progress, ratings, cast, media badges.
    """
    if not isinstance(raw_item, dict):
        raw_item = {}
    item_type = raw_item.get('type') or 'video'
    thumb = raw_item.get('thumb') or ''
    art = raw_item.get('art') or ''
    grandparent_thumb = raw_item.get('grandparentThumb') or ''
    grandparent_art = raw_item.get('grandparentArt') or ''
    logo = _image_of_type(raw_item, 'clearLogo')
    section_id = raw_item.get('librarySectionID')

    # Plex TV cards show the *show* poster for episodes (2:3), the item's own
    # thumb for movies/shows/seasons; fanart falls back to the show's art.
    poster = grandparent_thumb if item_type == 'episode' and grandparent_thumb else thumb
    fanart = art or grandparent_art

    duration_ms = raw_item.get('duration')
    view_offset_ms = raw_item.get('viewOffset')
    progress = None
    if duration_ms and view_offset_ms:
        progress = min(1.0, max(0.0, float(view_offset_ms) / float(duration_ms)))

    media = _first_media(raw_item)
    part_key = ''
    parts = media.get('Part') or []
    if parts:
        part_key = parts[0].get('key') or ''

    view_count = raw_item.get('viewCount') or 0
    return {
        'title': raw_item.get('title') or 'Sans titre',
        'type': item_type,
        'rating_key': raw_item.get('ratingKey'),
        'parent_rating_key': raw_item.get('parentRatingKey'),
        'grandparent_rating_key': raw_item.get('grandparentRatingKey'),
        'index': raw_item.get('index'),
        'season': raw_item.get('parentIndex'),
        'show_title': raw_item.get('grandparentTitle') or '',
        'year': raw_item.get('year'),
        'originally_available_at': raw_item.get('originallyAvailableAt'),
        'tagline': raw_item.get('tagline') or '',
        'summary': raw_item.get('summary') or '',
        'content_rating': _content_rating_display(raw_item),
        'rating': raw_item.get('rating'),
        'audience_rating': raw_item.get('audienceRating'),
        'rating_image': raw_item.get('ratingImage') or '',
        'audience_rating_image': raw_item.get('audienceRatingImage') or '',
        'genres': _tags(raw_item, 'Genre'),
        'directors': _tags(raw_item, 'Director'),
        'writers': _tags(raw_item, 'Writer'),
        'cast': [
            {
                'name': str(role.get('tag')),
                'role': str(role.get('role') or ''),
                'thumb_url': image_resolver(role['thumb'], 160, 160) if role.get('thumb') else '',
                # 'actor=11550' -- server-side tag filter for the person's
                # filmography page (see PlexClient.person_filmography).
                'person_filter': str(role.get('filter') or ''),
            }
            for role in raw_item.get('Role') or []
            if role.get('tag')
        ],
        'studio': raw_item.get('studio') or '',
        'duration_ms': duration_ms,
        'view_offset_ms': view_offset_ms,
        'progress': progress,
        'view_count': view_count,
        'watched': bool(view_count),
        'thumb_url': image_resolver(thumb, 640, 360) if thumb else '',
        'art_url': image_resolver(art, 1920, 1080) if art else '',
        'poster_url': image_resolver(poster, 320, 480) if poster else '',
        'fanart_url': image_resolver(fanart, 1920, 1080) if fanart else '',
        # clearLogos are transparent PNGs -- Plex's photo transcoder emits
        # JPEG only, so logos keep the direct URL to preserve alpha.
        'logo_url': image_resolver(logo) if logo else '',
        'landscape_url': image_resolver(thumb, 640, 360) if (thumb and item_type == 'episode') else '',
        'video_label': _video_label(raw_item),
        'audio_label': _audio_label(raw_item),
        'subtitle_label': _subtitle_label(raw_item),
        'part_key': part_key,
        'section_id': str(section_id) if section_id is not None else None,
    }


def parse_metadata_list(raw_json, image_resolver):
    """Return normalised video dicts from a raw Metadata-bearing payload.

    `image_resolver(plex_path) -> url` builds a displayable URL for a Plex
    image path (e.g. `ConnectorClient.image_url`).
    """
    mc = _media_container(raw_json)
    return [build_video_item(item, image_resolver)
            for item in mc.get('Metadata', [])]


def filter_by_section(items, section_key):
    """Return only the items whose section_id matches section_key.

    Used to scope an otherwise global list (e.g. /library/onDeck, which has
    no per-section endpoint) to a single library on the client side. Returns
    `items` unchanged if `section_key` is falsy.
    """
    if not section_key:
        return items
    section_key = str(section_key)
    return [item for item in items if item.get('section_id') == section_key]
