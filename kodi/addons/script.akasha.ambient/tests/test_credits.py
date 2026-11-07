import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'resources', 'lib'))

import credits  # noqa: E402


class CreditForTests(unittest.TestCase):
    def test_wikimedia_photo_by(self):
        credit = credits.credit_for(
            '/photos/039_Northern_lights_over_Myvatn_Iceland_Photo_by_Giles_Laurent.jpg')
        self.assertEqual(credit, 'Northern lights over Myvatn Iceland · Giles Laurent')

    def test_generic_by(self):
        self.assertEqual(
            credits.credit_for('/photos/Sunset_at_the_beach_by_A._Photographer.jpg'),
            'Sunset at the beach · A. Photographer')

    def test_plain_name_becomes_title(self):
        self.assertEqual(credits.credit_for('/photos/misty_morning.jpg'), 'Misty Morning')

    def test_empty_path(self):
        self.assertEqual(credits.credit_for(''), '')
        self.assertEqual(credits.credit_for(None), '')


class FrameCreditTests(unittest.TestCase):
    def test_single_frame(self):
        self.assertEqual(credits.frame_credit(['/p/misty_morning.jpg']), 'Misty Morning')

    def test_pair_joins_distinct_credits(self):
        frame = ['/p/first_shot.jpg', '/p/second_shot.jpg']
        self.assertEqual(credits.frame_credit(frame), 'First Shot  |  Second Shot')

    def test_pair_dedupes_identical_credits(self):
        frame = ['/p/a/same_name.jpg', '/p/b/same_name.jpg']
        self.assertEqual(credits.frame_credit(frame), 'Same Name')

    def test_empty_frame(self):
        self.assertEqual(credits.frame_credit([]), '')


if __name__ == '__main__':
    unittest.main()
