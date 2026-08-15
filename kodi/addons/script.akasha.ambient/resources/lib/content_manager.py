"""Akasha Ambient — content folder resolution.

Pure filesystem logic (stdlib `os` only, no `xbmc*`), so it is unit-testable
with plain temporary directories. The actual slideshow rotation/crossfade is
handled natively by Kodi's `multiimage` skin control (see decisions.md); this
module only decides *which* path the skin's `multiimage` control should point
at, and validates it isn't empty before use.
"""
import os

IMAGE_EXTENSIONS = ('.jpg', '.jpeg', '.png', '.bmp', '.gif', '.tbn', '.webp')


def list_images(folder):
    """Return the list of image files directly inside `folder`.

    Returns an empty list if the folder does not exist, is not a directory,
    or cannot be read (permissions, unmounted share, ...) — callers should
    treat that as "no content available" rather than an error.
    """
    try:
        if not folder or not os.path.isdir(folder):
            return []
        return sorted(
            entry for entry in os.listdir(folder)
            if entry.lower().endswith(IMAGE_EXTENSIONS)
            and os.path.isfile(os.path.join(folder, entry))
        )
    except OSError:
        return []


def has_content(folder):
    """True if `folder` contains at least one usable image."""
    return len(list_images(folder)) > 0


def resolve_slideshow_path(configured_path, fallback_folder):
    """Return the folder the `multiimage` skin control should use.

    - `configured_path` is used as-is when it contains at least one image.
    - Otherwise, fall back to another folder (bundled with the addon) so the
      screensaver never renders a blank screen. Kodi's `multiimage` control
      requires a *folder*, not a single file — passing it a plain file path
      makes it spin forever trying to enumerate a "directory" that doesn't
      behave like one, which was observed to also hang the controlling
      Python script (see docs/ambient-mode/decisions.md).
    """
    if has_content(configured_path):
        return configured_path
    return fallback_folder
