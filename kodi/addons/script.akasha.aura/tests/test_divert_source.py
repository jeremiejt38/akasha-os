"""Unit tests for divert_source.py — no xbmc dependency."""

import unittest

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
        resolver = lambda path: 'resolved:' + path
        items = divert_source.parse_metadata_list(raw, resolver)
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]['title'], 'Inception')
        self.assertEqual(items[0]['thumb_url'], 'resolved:/library/metadata/123/thumb/1')
        self.assertEqual(items[0]['art_url'], 'resolved:/library/metadata/123/art/1')

    def test_parse_metadata_list_missing_images_skip_resolver(self):
        raw = {'MediaContainer': {'Metadata': [{'title': 'No Art'}]}}
        calls = []
        resolver = lambda path: calls.append(path) or 'x'
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
        items = divert_source.parse_metadata_list(raw, lambda p: p)
        self.assertEqual(items[0]['season'], 9)
        self.assertEqual(items[0]['show_title'], 'Rick et Morty')

    def test_parse_sections_handles_non_dict_input(self):
        self.assertEqual(divert_source.parse_sections('not a dict'), [])
        self.assertEqual(divert_source.parse_genres(None), [])

    def test_parse_metadata_list_captures_section_id(self):
        raw = {'MediaContainer': {'Metadata': [{'title': 'Inception', 'librarySectionID': 1}]}}
        items = divert_source.parse_metadata_list(raw, lambda p: p)
        self.assertEqual(items[0]['section_id'], '1')

    def test_parse_metadata_list_missing_section_id_is_none(self):
        raw = {'MediaContainer': {'Metadata': [{'title': 'No Section'}]}}
        items = divert_source.parse_metadata_list(raw, lambda p: p)
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


if __name__ == '__main__':
    unittest.main()
