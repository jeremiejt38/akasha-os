import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'resources', 'lib'))

import content_manager  # noqa: E402


class ListImagesTests(unittest.TestCase):
    def test_missing_folder_returns_empty_list(self):
        self.assertEqual(content_manager.list_images('/nonexistent/path/xyz'), [])

    def test_lists_only_image_extensions(self):
        with tempfile.TemporaryDirectory() as tmp:
            for name in ('a.jpg', 'b.PNG', 'c.txt', 'd.mp4', 'e.webp'):
                open(os.path.join(tmp, name), 'w').close()
            self.assertEqual(
                content_manager.list_images(tmp),
                ['a.jpg', 'b.PNG', 'e.webp'],
            )

    def test_ignores_subdirectories(self):
        with tempfile.TemporaryDirectory() as tmp:
            open(os.path.join(tmp, 'photo.jpg'), 'w').close()
            os.mkdir(os.path.join(tmp, 'subfolder.jpg'))
            self.assertEqual(content_manager.list_images(tmp), ['photo.jpg'])

    def test_empty_folder_returns_empty_list(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(content_manager.list_images(tmp), [])


class HasContentTests(unittest.TestCase):
    def test_false_for_empty_or_missing_folder(self):
        self.assertFalse(content_manager.has_content('/nonexistent/path/xyz'))
        with tempfile.TemporaryDirectory() as tmp:
            self.assertFalse(content_manager.has_content(tmp))

    def test_true_when_at_least_one_image(self):
        with tempfile.TemporaryDirectory() as tmp:
            open(os.path.join(tmp, 'a.jpg'), 'w').close()
            self.assertTrue(content_manager.has_content(tmp))


class ResolveSlideshowPathTests(unittest.TestCase):
    def test_uses_configured_path_when_it_has_content(self):
        with tempfile.TemporaryDirectory() as tmp:
            open(os.path.join(tmp, 'a.jpg'), 'w').close()
            self.assertEqual(
                content_manager.resolve_slideshow_path(tmp, '/fallback.png'),
                tmp,
            )

    def test_falls_back_when_configured_path_is_empty(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(
                content_manager.resolve_slideshow_path(tmp, '/fallback.png'),
                '/fallback.png',
            )

    def test_falls_back_when_configured_path_missing(self):
        self.assertEqual(
            content_manager.resolve_slideshow_path('/nonexistent/xyz', '/fallback.png'),
            '/fallback.png',
        )


if __name__ == '__main__':
    unittest.main()
