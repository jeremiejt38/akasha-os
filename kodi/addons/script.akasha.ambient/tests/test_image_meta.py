import os
import struct
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'resources', 'lib'))

import image_meta  # noqa: E402


def _png_bytes(width, height):
    ihdr = struct.pack('>IIBBBBB', width, height, 8, 2, 0, 0, 0)
    return b'\x89PNG\r\n\x1a\n' + struct.pack('>I', len(ihdr)) + b'IHDR' + ihdr


def _gif_bytes(width, height):
    return b'GIF89a' + struct.pack('<HH', width, height) + b'\x00' * 20


def _jpeg_bytes(width, height):
    # SOI + APP0 (skipped) + SOF0 carrying the dimensions.
    app0 = b'\xff\xe0' + struct.pack('>H', 16) + b'JFIF\x00' + b'\x00' * 11
    sof = (b'\xff\xc0' + struct.pack('>H', 17) + b'\x08' +
           struct.pack('>HH', height, width) + b'\x03' + b'\x00' * 9)
    return b'\xff\xd8' + app0 + sof + b'\xff\xd9'


class ImageSizeTests(unittest.TestCase):
    def _write(self, data, name='img.bin'):
        path = os.path.join(self._tmp.name, name)
        with open(path, 'wb') as f:
            f.write(data)
        return path

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()

    def tearDown(self):
        self._tmp.cleanup()

    def test_png_size(self):
        self.assertEqual(image_meta.image_size(self._write(_png_bytes(800, 1200))), (800, 1200))

    def test_gif_size(self):
        self.assertEqual(image_meta.image_size(self._write(_gif_bytes(640, 480))), (640, 480))

    def test_jpeg_size_skips_app_segments(self):
        self.assertEqual(image_meta.image_size(self._write(_jpeg_bytes(1920, 1080))), (1920, 1080))

    def test_garbage_returns_none(self):
        self.assertIsNone(image_meta.image_size(self._write(b'not an image at all')))

    def test_missing_file_returns_none(self):
        self.assertIsNone(image_meta.image_size('/nonexistent/x.jpg'))

    def test_is_portrait(self):
        portrait = self._write(_png_bytes(800, 1200))
        landscape = self._write(_png_bytes(1200, 800), 'b.png')
        unknown = self._write(b'junk', 'c.png')
        self.assertTrue(image_meta.is_portrait(portrait))
        self.assertFalse(image_meta.is_portrait(landscape))
        self.assertFalse(image_meta.is_portrait(unknown))


if __name__ == '__main__':
    unittest.main()
