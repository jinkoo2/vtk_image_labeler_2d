"""Display and settings helpers that do not need Qt or VTK."""

from __future__ import annotations

import hashlib
import os


def as_bool(value, default=False):
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return bool(value)
    text = str(value).strip().lower()
    if text in ("1", "true", "yes", "on"):
        return True
    if text in ("0", "false", "no", "off", ""):
        return False
    return default


def first_number(value):
    """First finite number in a DICOM value, list, or backslash-separated string."""
    if value is None:
        return None
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return None
        text = text.replace(",", " ").split()[0]
        if "\\" in text:
            text = text.split("\\", 1)[0]
        try:
            return float(text)
        except ValueError:
            return None
    if isinstance(value, (bytes, bytearray)):
        return None
    try:
        iterator = iter(value)
    except TypeError:
        return None
    for item in iterator:
        number = first_number(item)
        if number is not None:
            return number
    return None


def dicom_window_level(dataset):
    """Return ``{"level", "width"}`` from WindowCenter / WindowWidth, or None."""
    if dataset is None:
        return None
    center = first_number(getattr(dataset, "WindowCenter", None))
    width = first_number(getattr(dataset, "WindowWidth", None))
    if center is None or width is None or width <= 0:
        return None
    return {"level": float(center), "width": float(width)}


def slider_bounds(scalar_min, scalar_max, level, width):
    """Slider range that can represent this window, expanded past the pixels if needed."""
    low = float(level) - float(width) / 2.0
    high = float(level) + float(width) / 2.0
    range_min = min(float(scalar_min), low)
    range_max = max(float(scalar_max), high)
    if range_max <= range_min:
        range_max = range_min + 1.0
    return range_min, range_max, low, high


def parallel_scale_to_fit(image_width, image_height, viewport_width, viewport_height, margin=1.02):
    """Parallel-projection scale that shows the whole image in the viewport.

    VTK's parallel scale is half the visible height in world units. The visible
    width is that height times the viewport aspect ratio.
    """
    image_width = abs(float(image_width))
    image_height = abs(float(image_height))
    if image_width <= 0 or image_height <= 0:
        return None
    viewport_width = max(float(viewport_width), 1.0)
    viewport_height = max(float(viewport_height), 1.0)
    aspect = viewport_width / viewport_height
    scale_for_height = image_height / 2.0
    scale_for_width = image_width / (2.0 * aspect)
    return max(scale_for_height, scale_for_width) * float(margin)


def window_level_settings_key(path):
    normalized = os.path.normcase(os.path.abspath(path))
    digest = hashlib.sha1(normalized.encode("utf-8", errors="replace")).hexdigest()
    return f"window_level/{digest}"


def format_window_level(level, width):
    return f"{float(level)},{float(width)}"


def parse_window_level(text):
    if text is None:
        return None
    parts = str(text).split(",")
    if len(parts) != 2:
        return None
    try:
        level = float(parts[0])
        width = float(parts[1])
    except ValueError:
        return None
    if width <= 0:
        return None
    return {"level": level, "width": width}


def dock_object_name(manager_name):
    slug = "".join(ch for ch in str(manager_name) if ch.isalnum())
    return f"{slug or 'Manager'}Dock"
