"""Window fit, DICOM window/level, and settings-key helpers."""

from view_state import (
    as_bool,
    dicom_window_level,
    dock_object_name,
    first_number,
    format_window_level,
    parallel_scale_to_fit,
    parse_window_level,
    slider_bounds,
    window_level_settings_key,
)


class _Dataset:
    def __init__(self, center, width):
        self.WindowCenter = center
        self.WindowWidth = width


def test_dicom_window_level_uses_the_first_pair():
    found = dicom_window_level(_Dataset([40, 50], [400, 350]))
    assert found == {"level": 40.0, "width": 400.0}


def test_dicom_window_level_accepts_strings_and_rejects_missing_or_empty():
    assert dicom_window_level(_Dataset("40.5", "400")) == {"level": 40.5, "width": 400.0}
    assert dicom_window_level(_Dataset(40, 0)) is None
    assert dicom_window_level(_Dataset(None, 400)) is None
    assert dicom_window_level(None) is None
    assert first_number("40\\400") == 40.0


def test_slider_bounds_include_a_window_outside_the_pixels():
    range_min, range_max, low, high = slider_bounds(-100, 100, 40, 400)
    assert low == -160
    assert high == 240
    assert range_min == -160
    assert range_max == 240


def test_parallel_scale_fits_a_wide_image_in_a_narrow_view():
    scale = parallel_scale_to_fit(1000, 100, 200, 800, margin=1)
    assert scale == 2000


def test_parallel_scale_fits_a_tall_image_in_a_wide_view():
    scale = parallel_scale_to_fit(100, 200, 400, 100, margin=1)
    assert scale == 100


def test_window_level_text_round_trip_and_stable_key():
    text = format_window_level(40, 400)
    assert parse_window_level(text) == {"level": 40.0, "width": 400.0}
    assert parse_window_level("nope") is None
    assert parse_window_level("10,0") is None
    key_a = window_level_settings_key(r"D:\QA\case.dcm")
    key_b = window_level_settings_key(r"D:\QA\case.dcm")
    assert key_a == key_b
    assert key_a.startswith("window_level/")


def test_dock_names_and_bools():
    assert dock_object_name("nnUNet Dashboard") == "nnUNetDashboardDock"
    assert as_bool("true") is True
    assert as_bool("0") is False
    assert as_bool(None, default=True) is True
