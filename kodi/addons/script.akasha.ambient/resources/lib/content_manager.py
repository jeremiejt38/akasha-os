"""Akasha Ambient — content folder resolution.

Pure filesystem logic (stdlib `os` only, no `xbmc*`), so it is unit-testable
with plain temporary directories. The actual slideshow/playback is handled
natively by Kodi (multiimage skin control or xbmc.Player); this module only
decides *which* media the skin/player should use.
"""
import os

IMAGE_EXTENSIONS = ('.jpg', '.jpeg', '.png', '.bmp', '.gif', '.tbn', '.webp')
VIDEO_EXTENSIONS = ('.mp4', '.mkv', '.mov', '.avi', '.webm', '.m4v', '.ts', '.mpg', '.mpeg')
MEDIA_EXTENSIONS = IMAGE_EXTENSIONS + VIDEO_EXTENSIONS


def _list_files(folder, extensions):
    """Return the list of matching file names inside `folder`.

    Returns an empty list if the folder does not exist, is not a directory,
    or cannot be read (permissions, unmounted share, ...) — callers should
    treat that as "no content available" rather than an error.
    """
    try:
        if not folder or not os.path.isdir(folder):
            return []
        return sorted(
            entry for entry in os.listdir(folder)
            if entry.lower().endswith(extensions)
            and os.path.isfile(os.path.join(folder, entry))
        )
    except OSError:
        return []


def list_images(folder):
    """Return the list of image file names directly inside `folder`."""
    return _list_files(folder, IMAGE_EXTENSIONS)


def list_videos(folder):
    """Return the list of video file names directly inside `folder`."""
    return _list_files(folder, VIDEO_EXTENSIONS)


def list_media(folder):
    """Return the list of all supported media file names inside `folder`."""
    return _list_files(folder, MEDIA_EXTENSIONS)


def has_images(folder):
    """True if `folder` contains at least one usable image."""
    return len(list_images(folder)) > 0


def has_videos(folder):
    """True if `folder` contains at least one usable video."""
    return len(list_videos(folder)) > 0


def has_content(folder):
    """True if `folder` contains at least one usable image or video."""
    return has_images(folder) or has_videos(folder)


def resolve_slideshow_path(configured_path, fallback_folder):
    """Return the folder the `multiimage` skin control should use.

    - `configured_path` is used as-is when it contains at least one image.
    - Otherwise, fall back to another folder (bundled with the addon) so the
      screensaver never renders a blank screen. Kodi's `multiimage` control
      requires a *folder*, not a single file — passing it a plain file path
      makes it spin forever trying to enumerate a "directory" that doesn't
      behave like one, which was observed to also hang the controlling
      Python script (see docs/ambient-mode/decisions.md).

    **Deprecated**: prefer `resolve_media()` when video support is needed.
    This function is kept for backward compatibility with callers that only
    drive the `multiimage` control.
    """
    if has_images(configured_path):
        return configured_path
    if has_images(fallback_folder):
        return fallback_folder
    return fallback_folder


def resolve_media(configured_path, fallback_folder):
    """Decide whether the Ambient window should play images or videos.

    Returns a tuple `(media_type, content)` where:

    - `media_type == 'images'`: `content` is a folder path for `multiimage`.
    - `media_type == 'videos'`: `content` is a list of absolute video file
      paths for `xbmc.Player().play()`.

    Preference order:
    1. Videos in the user-configured folder (if any).
    2. Images in the user-configured folder (if any).
    3. Videos in the fallback folder (if any).
    4. Images in the fallback folder (bundled fallback, always present).

    This lets users drop either a photo pack, a video pack, or a mixed folder
    into `/storage/ambient/photos`; the Mode Ambient will pick the richest
    content type available and never leave the screen blank.
    """
    if has_videos(configured_path):
        return 'videos', [os.path.join(configured_path, name) for name in list_videos(configured_path)]
    if has_images(configured_path):
        return 'images', configured_path
    if has_videos(fallback_folder):
        return 'videos', [os.path.join(fallback_folder, name) for name in list_videos(fallback_folder)]
    return 'images', fallback_folder
