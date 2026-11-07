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
                content_manager.resolve_slideshow_path(tmp, '/fallback/folder'),
                tmp,
            )

    def test_falls_back_when_configured_path_is_empty(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(
                content_manager.resolve_slideshow_path(tmp, '/fallback/folder'),
                '/fallback/folder',
            )

    def test_falls_back_when_configured_path_missing(self):
        self.assertEqual(
            content_manager.resolve_slideshow_path('/nonexistent/xyz', '/fallback/folder'),
            '/fallback/folder',
        )


class ListVideosTests(unittest.TestCase):
    def test_missing_folder_returns_empty_list(self):
        self.assertEqual(content_manager.list_videos('/nonexistent/path/xyz'), [])

    def test_lists_only_video_extensions(self):
        with tempfile.TemporaryDirectory() as tmp:
            for name in ('a.mp4', 'b.MOV', 'c.txt', 'd.jpg', 'e.webm'):
                open(os.path.join(tmp, name), 'w').close()
            self.assertEqual(
                content_manager.list_videos(tmp),
                ['a.mp4', 'b.MOV', 'e.webm'],
            )

    def test_empty_folder_returns_empty_list(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(content_manager.list_videos(tmp), [])


class ResolveMediaTests(unittest.TestCase):
    def test_prefers_videos_in_configured_path(self):
        with tempfile.TemporaryDirectory() as content, tempfile.TemporaryDirectory() as fallback:
            open(os.path.join(content, 'clip.mp4'), 'w').close()
            open(os.path.join(content, 'photo.jpg'), 'w').close()
            media_type, content_out = content_manager.resolve_media(content, fallback)
            self.assertEqual(media_type, 'videos')
            self.assertEqual(content_out, [os.path.join(content, 'clip.mp4')])

    def test_falls_back_to_images_when_no_videos(self):
        with tempfile.TemporaryDirectory() as content, tempfile.TemporaryDirectory() as fallback:
            open(os.path.join(content, 'photo.jpg'), 'w').close()
            media_type, content_out = content_manager.resolve_media(content, fallback)
            self.assertEqual(media_type, 'images')
            self.assertEqual(content_out, content)

    def test_falls_back_to_videos_in_fallback(self):
        with tempfile.TemporaryDirectory() as content, tempfile.TemporaryDirectory() as fallback:
            open(os.path.join(fallback, 'fallback.mp4'), 'w').close()
            media_type, content_out = content_manager.resolve_media(content, fallback)
            self.assertEqual(media_type, 'videos')
            self.assertEqual(content_out, [os.path.join(fallback, 'fallback.mp4')])

    def test_falls_back_to_images_in_fallback(self):
        with tempfile.TemporaryDirectory() as content, tempfile.TemporaryDirectory() as fallback:
            open(os.path.join(fallback, 'fallback.png'), 'w').close()
            media_type, content_out = content_manager.resolve_media(content, fallback)
            self.assertEqual(media_type, 'images')
            self.assertEqual(content_out, fallback)


class ResolveImagePathsTests(unittest.TestCase):
    def test_returns_absolute_paths_from_configured_folder(self):
        with tempfile.TemporaryDirectory() as content, tempfile.TemporaryDirectory() as fallback:
            open(os.path.join(content, 'a.jpg'), 'w').close()
            open(os.path.join(content, 'b.png'), 'w').close()
            open(os.path.join(fallback, 'fb.png'), 'w').close()
            self.assertEqual(
                content_manager.resolve_image_paths(content, fallback),
                [os.path.join(content, 'a.jpg'), os.path.join(content, 'b.png')],
            )

    def test_falls_back_when_configured_folder_has_no_images(self):
        with tempfile.TemporaryDirectory() as content, tempfile.TemporaryDirectory() as fallback:
            open(os.path.join(content, 'clip.mp4'), 'w').close()
            open(os.path.join(fallback, 'fb.png'), 'w').close()
            self.assertEqual(
                content_manager.resolve_image_paths(content, fallback),
                [os.path.join(fallback, 'fb.png')],
            )

    def test_empty_when_neither_folder_has_images(self):
        with tempfile.TemporaryDirectory() as content, tempfile.TemporaryDirectory() as fallback:
            self.assertEqual(content_manager.resolve_image_paths(content, fallback), [])


class RemoteSourceTests(unittest.TestCase):
    """H8: content folder may point at a Kodi VFS share (smb://...)."""

    def test_remote_listing_uses_xbmcvfs(self):
        import types
        fake = types.ModuleType('xbmcvfs')
        fake.listdir = lambda path: ([], ['b.png', 'a.jpg', 'skip.txt'])
        sys.modules['xbmcvfs'] = fake
        try:
            self.assertEqual(
                content_manager.list_images('smb://nas/photos'),
                ['a.jpg', 'b.png'],
            )
        finally:
            del sys.modules['xbmcvfs']

    def test_remote_without_xbmcvfs_reports_no_content(self):
        sys.modules.pop('xbmcvfs', None)
        self.assertEqual(content_manager.list_images('smb://nas/photos'), [])
        self.assertFalse(content_manager.has_content('nfs://nas/photos'))

    def test_remote_vfs_failure_falls_back_cleanly(self):
        import types
        fake = types.ModuleType('xbmcvfs')

        def _boom(path):
            raise RuntimeError('share unreachable')
        fake.listdir = _boom
        sys.modules['xbmcvfs'] = fake
        try:
            with tempfile.TemporaryDirectory() as fallback:
                open(os.path.join(fallback, 'fb.png'), 'w').close()
                self.assertEqual(
                    content_manager.resolve_image_paths('smb://nas/photos', fallback),
                    [os.path.join(fallback, 'fb.png')],
                )
        finally:
            del sys.modules['xbmcvfs']


if __name__ == '__main__':
    unittest.main()
