"""Line profile sampling without a display."""

from line_profile import sample_line_profile


def _value(i, j, k):
    return 100 + i


def test_horizontal_profile_matches_pixel_centers():
    distances, values = sample_line_profile(
        (0, 0, 0),
        (2, 2, 1),
        (4, 2, 1),
        _value,
        (0, 0, 0),
        (6, 0, 0),
    )
    assert distances == [0.0, 2.0, 4.0, 6.0]
    assert values == [100, 101, 102, 103]


def test_profile_outside_the_image_is_empty():
    _distances, values = sample_line_profile(
        (0, 0, 0),
        (1, 1, 1),
        (4, 4, 1),
        _value,
        (-10, 0, 0),
        (-8, 0, 0),
    )
    assert values
    assert all(value is None for value in values)
