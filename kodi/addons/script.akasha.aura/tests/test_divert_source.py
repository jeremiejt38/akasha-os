"""Unit tests for divert_source.py — no xbmc dependency."""

import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'resources', 'lib'))

import divert_source


class TestDivertSource(unittest.TestCase):
    def test_parse_sections_filters_video_types(self):
        raw = {
            'MediaContainer': {
                'Directory': [
                    {'key': '1', 'title': 'Films', 'type': 'movie'},
                    {'key': '2', 'title': 'Musique', 'type': 'artist'},
                    {'key': '3', 'title': 'Series', 'type': 'show'},
                ]
            }
        }
        sections = divert_source.parse_sections(raw)
        self.assertEqual(len(sections), 2)
        self.assertEqual(sections[0], {'key': '1', 'title': 'Films', 'type': 'movie'})
        self.assertEqual(sections[1]['title'], 'Series')

    def test_parse_genres(self):
        raw = {'MediaContainer': {'Directory': [{'title': 'Action'}, {'title': 'Comedie'}, {}]}}
        self.assertEqual(divert_source.parse_genres(raw), ['Action', 'Comedie'])

    def test_parse_metadata_list_resolves_images(self):
        raw = {
            'MediaContainer': {
                'Metadata': [
                    {
                        'title': 'Inception',
                        'type': 'movie',
                        'ratingKey': '123',
                        'thumb': '/library/metadata/123/thumb/1',
                        'art': '/library/metadata/123/art/1',
                        'year': 2010,
                    }
                ]
            }
        }
        resolver = lambda path, w=None, h=None: 'resolved:' + path
        items = divert_source.parse_metadata_list(raw, resolver)
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]['title'], 'Inception')
        self.assertEqual(items[0]['thumb_url'], 'resolved:/library/metadata/123/thumb/1')
        self.assertEqual(items[0]['art_url'], 'resolved:/library/metadata/123/art/1')

    def test_parse_metadata_list_missing_images_skip_resolver(self):
        raw = {'MediaContainer': {'Metadata': [{'title': 'No Art'}]}}
        calls = []
        resolver = lambda path, w=None, h=None: calls.append(path) or 'x'
        items = divert_source.parse_metadata_list(raw, resolver)
        self.assertEqual(items[0]['thumb_url'], '')
        self.assertEqual(items[0]['art_url'], '')
        self.assertEqual(calls, [])

    def test_parse_total_size_prefers_total_size_field(self):
        raw = {'MediaContainer': {'size': 30, 'totalSize': 771}}
        self.assertEqual(divert_source.parse_total_size(raw), 771)

    def test_parse_total_size_falls_back_to_size(self):
        raw = {'MediaContainer': {'size': 12}}
        self.assertEqual(divert_source.parse_total_size(raw), 12)

    def test_parse_total_size_missing_returns_none(self):
        self.assertIsNone(divert_source.parse_total_size({'MediaContainer': {}}))
        self.assertIsNone(divert_source.parse_total_size('not a dict'))

    def test_item_subtitle_episode(self):
        item = {'season': 16, 'index': 6}
        self.assertEqual(divert_source.item_subtitle(item), 'S16 - E6')

    def test_item_subtitle_movie_falls_back_to_year(self):
        item = {'season': None, 'index': None, 'year': 2010}
        self.assertEqual(divert_source.item_subtitle(item), '2010')

    def test_item_subtitle_missing_data_returns_empty(self):
        self.assertEqual(divert_source.item_subtitle({}), '')

    def test_video_label_empty_without_media(self):
        item = divert_source.build_video_item(
            {'title': 'Lupin', 'type': 'season'},
            lambda p, w=None, h=None: p)
        self.assertEqual(item['video_label'], '')

    def test_video_label_sd_with_real_media(self):
        item = divert_source.build_video_item(
            {'title': 'Ep', 'type': 'episode',
             'Media': [{'videoResolution': 'sd', 'Part': [{'key': '/x'}]}]},
            lambda p, w=None, h=None: p)
        self.assertEqual(item['video_label'], 'SD')

    def test_parse_metadata_list_captures_episode_fields(self):
        raw = {
            'MediaContainer': {
                'Metadata': [
                    {
                        'title': 'Une vie revee',
                        'parentIndex': 9,
                        'index': 10,
                        'grandparentTitle': 'Rick et Morty',
                    }
                ]
            }
        }
        items = divert_source.parse_metadata_list(raw, lambda p, w=None, h=None: p)
        self.assertEqual(items[0]['season'], 9)
        self.assertEqual(items[0]['show_title'], 'Rick et Morty')

    def test_parse_sections_handles_non_dict_input(self):
        self.assertEqual(divert_source.parse_sections('not a dict'), [])
        self.assertEqual(divert_source.parse_genres(None), [])

    def test_parse_metadata_list_captures_section_id(self):
        raw = {'MediaContainer': {'Metadata': [{'title': 'Inception', 'librarySectionID': 1}]}}
        items = divert_source.parse_metadata_list(raw, lambda p, w=None, h=None: p)
        self.assertEqual(items[0]['section_id'], '1')

    def test_parse_metadata_list_missing_section_id_is_none(self):
        raw = {'MediaContainer': {'Metadata': [{'title': 'No Section'}]}}
        items = divert_source.parse_metadata_list(raw, lambda p, w=None, h=None: p)
        self.assertIsNone(items[0]['section_id'])

    def test_filter_by_section_keeps_matching_items(self):
        items = [{'title': 'A', 'section_id': '1'}, {'title': 'B', 'section_id': '2'}]
        self.assertEqual(divert_source.filter_by_section(items, '1'), [items[0]])

    def test_filter_by_section_none_key_returns_all(self):
        items = [{'title': 'A', 'section_id': '1'}]
        self.assertEqual(divert_source.filter_by_section(items, None), items)

    def test_translate_genre_fr_known(self):
        self.assertEqual(divert_source.translate_genre_fr('Horror'), 'Horreur')
        self.assertEqual(divert_source.translate_genre_fr('Science Fiction'), 'Science-fiction')
        self.assertEqual(divert_source.translate_genre_fr('Comedy'), 'Comedie')
        self.assertEqual(divert_source.translate_genre_fr('Children'), 'Enfants')
        self.assertEqual(divert_source.translate_genre_fr('Martial Arts'), 'Arts martiaux')
        self.assertEqual(divert_source.translate_genre_fr('Mini-Series'), 'Mini-serie')

    def test_translate_genre_fr_unknown_passthrough(self):
        self.assertEqual(divert_source.translate_genre_fr('Zorblax'), 'Zorblax')

    def test_filter_by_section_no_match_returns_empty(self):
        items = [{'title': 'A', 'section_id': '1'}]
        self.assertEqual(divert_source.filter_by_section(items, '99'), [])

    def test_episode_uses_show_poster_and_fanart(self):
        raw = {
            'MediaContainer': {
                'Metadata': [
                    {
                        'title': 'Pilot', 'type': 'episode',
                        'thumb': '/ep/thumb', 'grandparentThumb': '/show/thumb',
                        'grandparentArt': '/show/art',
                    }
                ]
            }
        }
        items = divert_source.parse_metadata_list(raw, lambda p, w=None, h=None: 'r:' + p)
        self.assertEqual(items[0]['poster_url'], 'r:/show/thumb')
        self.assertEqual(items[0]['fanart_url'], 'r:/show/art')
        self.assertEqual(items[0]['landscape_url'], 'r:/ep/thumb')

    def test_movie_prefers_own_thumb_and_art(self):
        raw = {'MediaContainer': {'Metadata': [
            {'title': 'M', 'type': 'movie', 'thumb': '/m/thumb', 'art': '/m/art'}]}}
        items = divert_source.parse_metadata_list(raw, lambda p, w=None, h=None: 'r:' + p)
        self.assertEqual(items[0]['poster_url'], 'r:/m/thumb')
        self.assertEqual(items[0]['fanart_url'], 'r:/m/art')

    def test_progress_from_view_offset(self):
        raw = {'MediaContainer': {'Metadata': [
            {'title': 'M', 'duration': 1200000, 'viewOffset': 300000}]}}
        items = divert_source.parse_metadata_list(raw, lambda p, w=None, h=None: p)
        self.assertAlmostEqual(items[0]['progress'], 0.25)
        self.assertEqual(items[0]['duration_ms'], 1200000)
        self.assertEqual(items[0]['view_offset_ms'], 300000)

    def test_progress_absent_without_view_offset(self):
        raw = {'MediaContainer': {'Metadata': [{'title': 'M', 'duration': 1200000}]}}
        items = divert_source.parse_metadata_list(raw, lambda p, w=None, h=None: p)
        self.assertIsNone(items[0]['progress'])

    def test_content_rating_strips_locale_prefix(self):
        raw = {'MediaContainer': {'Metadata': [{'title': 'M', 'contentRating': 'fr/10'}]}}
        items = divert_source.parse_metadata_list(raw, lambda p, w=None, h=None: p)
        self.assertEqual(items[0]['content_rating'], '10')

    def test_ratings_genres_cast_and_crew(self):
        raw = {
            'MediaContainer': {
                'Metadata': [
                    {
                        'title': 'M', 'rating': 7.8, 'audienceRating': 8.4,
                        'audienceRatingImage': 'themoviedb://image.rating',
                        'Genre': [{'tag': 'Action'}, {'tag': 'Sci-Fi'}],
                        'Director': [{'tag': 'Dir Ector'}],
                        'Writer': [{'tag': 'Wri Ter'}],
                        'Role': [
                            {'tag': 'Actor One', 'role': 'Hero',
                             'thumb': '/role/1', 'filter': 'actor=11550'},
                            {'tag': 'Actor Two'},
                            {},
                        ],
                        'studio': 'Studio X',
                    }
                ]
            }
        }
        items = divert_source.parse_metadata_list(raw, lambda p, w=None, h=None: 'r:' + p)
        item = items[0]
        self.assertEqual(item['rating'], 7.8)
        self.assertEqual(item['audience_rating'], 8.4)
        self.assertEqual(item['genres'], ['Action', 'Sci-Fi'])
        self.assertEqual(item['directors'], ['Dir Ector'])
        self.assertEqual(item['writers'], ['Wri Ter'])
        self.assertEqual(item['studio'], 'Studio X')
        self.assertEqual(len(item['cast']), 2)
        self.assertEqual(item['cast'][0],
                         {'name': 'Actor One', 'role': 'Hero',
                          'thumb_url': 'r:/role/1',
                          'person_filter': 'actor=11550'})
        self.assertEqual(item['cast'][1]['thumb_url'], '')
        self.assertEqual(item['cast'][1]['person_filter'], '')

    def test_clear_logo_extracted(self):
        raw = {'MediaContainer': {'Metadata': [
            {'title': 'M', 'Image': [
                {'type': 'coverPoster', 'url': '/poster'},
                {'type': 'clearLogo', 'url': '/logo'},
            ]}]}}
        items = divert_source.parse_metadata_list(raw, lambda p, w=None, h=None: 'r:' + p)
        self.assertEqual(items[0]['logo_url'], 'r:/logo')

    def test_media_labels(self):
        raw = {
            'MediaContainer': {
                'Metadata': [
                    {
                        'title': 'M',
                        'Media': [{
                            'videoResolution': '4k', 'videoCodec': 'hevc',
                            'Part': [{'key': '/part/1', 'Stream': [
                                {'streamType': 1, 'codec': 'hevc', 'colorTrc': 'smpte2084'},
                                {'streamType': 2, 'codec': 'eac3', 'channels': 6,
                                 'language': 'French'},
                                {'streamType': 3, 'codec': 'srt', 'language': 'French'},
                            ]}],
                        }],
                    }
                ]
            }
        }
        items = divert_source.parse_metadata_list(raw, lambda p, w=None, h=None: p)
        item = items[0]
        self.assertEqual(item['video_label'], '4K HDR10 HEVC')
        self.assertEqual(item['audio_label'], 'French EAC3 5.1')
        self.assertEqual(item['subtitle_label'], 'French SRT')
        self.assertEqual(item['part_key'], '/part/1')

    def test_watched_flag_from_view_count(self):
        raw = {'MediaContainer': {'Metadata': [
            {'title': 'A', 'viewCount': 1}, {'title': 'B'}]}}
        items = divert_source.parse_metadata_list(raw, lambda p, w=None, h=None: p)
        self.assertTrue(items[0]['watched'])
        self.assertFalse(items[1]['watched'])

    def test_non_dict_item_does_not_raise(self):
        raw = {'MediaContainer': {'Metadata': [None, {'title': 'Ok'}]}}
        items = divert_source.parse_metadata_list(raw, lambda p, w=None, h=None: p)
        self.assertEqual(len(items), 2)
        self.assertEqual(items[0]['title'], 'Sans titre')

    def test_blur_colors_normalised(self):
        raw = {'MediaContainer': {'Metadata': [
            {'title': 'A', 'UltraBlurColors': {'topLeft': '5f3b2a'}},
            {'title': 'B'}]}}
        items = divert_source.parse_metadata_list(raw, lambda p, w=None, h=None: p)
        self.assertEqual(items[0]['blur_colors'], {'topLeft': '5f3b2a'})
        self.assertEqual(items[1]['blur_colors'], {})


if __name__ == '__main__':
    unittest.main()
