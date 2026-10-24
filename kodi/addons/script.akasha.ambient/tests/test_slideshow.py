import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'resources', 'lib'))

import slideshow  # noqa: E402


class PhotoCyclerTests(unittest.TestCase):
    def test_none_when_no_photos(self):
        cycler = slideshow.PhotoCycler([])
        self.assertIsNone(cycler.next_photo())

    def test_single_photo_repeats_itself(self):
        cycler = slideshow.PhotoCycler(['/photos/a.jpg'])
        for _ in range(3):
            self.assertEqual(cycler.next_photo(), '/photos/a.jpg')

    def test_covers_every_photo_before_repeating_a_cycle(self):
        paths = ['/photos/%d.jpg' % i for i in range(10)]
        cycler = slideshow.PhotoCycler(paths)
        first_cycle = [cycler.next_photo() for _ in paths]
        self.assertEqual(sorted(first_cycle), sorted(paths))

    def test_never_repeats_back_to_back_across_cycles(self):
        paths = ['/photos/%d.jpg' % i for i in range(50)]
        cycler = slideshow.PhotoCycler(paths)
        previous = None
        for _ in range(200):
            photo = cycler.next_photo()
            self.assertNotEqual(photo, previous)
            previous = photo

    def test_input_list_is_not_mutated(self):
        paths = ['/photos/a.jpg', '/photos/b.jpg', '/photos/c.jpg']
        original = list(paths)
        cycler = slideshow.PhotoCycler(paths)
        for _ in range(10):
            cycler.next_photo()
        self.assertEqual(paths, original)


class KenBurnsVariantTests(unittest.TestCase):
    def test_variants_stay_within_known_set(self):
        cycler = slideshow.PhotoCycler(['/photos/a.jpg'])
        for _ in range(40):
            self.assertIn(cycler.next_variant(), slideshow.KB_VARIANTS)

    def test_variants_are_actually_varied(self):
        cycler = slideshow.PhotoCycler(['/photos/a.jpg'])
        seen = {cycler.next_variant() for _ in range(60)}
        self.assertTrue(len(seen) > 1)


if __name__ == '__main__':
    unittest.main()
