"""Sample pixel values along a line and show them in a profile window."""

from __future__ import annotations

import math

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QDialog, QLabel, QVBoxLayout


def sample_line_profile(origin, spacing, dimensions, value_at, p1, p2, max_samples=2000):
    """Return ``(distances_mm, values)`` along the segment from ``p1`` to ``p2``.

    ``value_at(i, j, k)`` reads one voxel. Values are ``None`` outside the image.
    Distance is the 3D length in the same units as ``spacing``.
    """
    origin = [float(v) for v in origin]
    spacing = [float(v) for v in spacing]
    dims = [int(v) for v in dimensions]
    start = [float(v) for v in p1]
    end = [float(v) for v in p2]
    delta = [end[i] - start[i] for i in range(3)]
    length = math.sqrt(sum(component * component for component in delta))

    step = min(abs(spacing[0]), abs(spacing[1]))
    if step <= 0:
        step = 1.0
    count = int(math.ceil(length / step)) + 1 if length > 0 else 2
    count = max(2, min(count, int(max_samples)))

    depth = dims[2] if len(dims) > 2 else 1
    if depth <= 1 or spacing[2] == 0:
        slice_k = 0
    else:
        slice_k = int(round(((start[2] + end[2]) / 2.0 - origin[2]) / spacing[2]))
        slice_k = max(0, min(depth - 1, slice_k))

    distances = []
    values = []
    for index in range(count):
        fraction = 0.0 if count == 1 else index / (count - 1)
        world = [start[axis] + delta[axis] * fraction for axis in range(3)]
        ix = (world[0] - origin[0]) / spacing[0] if spacing[0] else 0.0
        iy = (world[1] - origin[1]) / spacing[1] if spacing[1] else 0.0
        distances.append(length * fraction)
        values.append(_bilinear(value_at, dims, ix, iy, slice_k))
    return distances, values


def _bilinear(value_at, dims, x, y, k):
    if dims[0] <= 0 or dims[1] <= 0:
        return None
    if x < 0 or y < 0 or x > dims[0] - 1 or y > dims[1] - 1:
        return None
    x0 = int(math.floor(x))
    y0 = int(math.floor(y))
    x1 = min(x0 + 1, dims[0] - 1)
    y1 = min(y0 + 1, dims[1] - 1)
    tx = x - x0
    ty = y - y0
    samples = (
        value_at(x0, y0, k),
        value_at(x1, y0, k),
        value_at(x0, y1, k),
        value_at(x1, y1, k),
    )
    if any(sample is None for sample in samples):
        return None
    v00, v10, v01, v11 = samples
    top = v00 * (1.0 - tx) + v10 * tx
    bottom = v01 * (1.0 - tx) + v11 * tx
    return top * (1.0 - ty) + bottom * ty


def sample_vtk_image(vtk_image, p1, p2):
    dims = vtk_image.GetDimensions()
    spacing = vtk_image.GetSpacing()
    origin = vtk_image.GetOrigin()
    scalars = vtk_image.GetPointData().GetScalars()

    def value_at(i, j, k):
        if scalars is None:
            return None
        if not (0 <= i < dims[0] and 0 <= j < dims[1] and 0 <= k < dims[2]):
            return None
        flat = (int(k) * int(dims[1]) + int(j)) * int(dims[0]) + int(i)
        return float(scalars.GetTuple1(flat))

    return sample_line_profile(origin, spacing, dims, value_at, p1, p2)


class LineProfileDialog(QDialog):
    """Profile plot. It stays open so the curve can follow a line while it is dragged."""

    def __init__(self, parent=None):
        super().__init__(parent)
        from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg, NavigationToolbar2QT
        from matplotlib.figure import Figure

        self.setWindowTitle("Line Profile")
        self.setModal(False)
        self.resize(720, 420)
        self.setWindowFlag(Qt.Window, True)

        self._summary = QLabel("Add a ruler or select a line.")
        self._summary.setWordWrap(True)

        self._figure = Figure(figsize=(7.0, 3.6), tight_layout=True)
        self._axes = self._figure.add_subplot(111)
        self._artist, = self._axes.plot([], [], color="#1f4e79", linewidth=1.5)
        self._axes.set_xlabel("Distance (mm)")
        self._axes.set_ylabel("Pixel value")
        self._axes.grid(True, alpha=0.3)
        self._canvas = FigureCanvasQTAgg(self._figure)
        toolbar = NavigationToolbar2QT(self._canvas, self)

        layout = QVBoxLayout(self)
        layout.addWidget(self._summary)
        layout.addWidget(toolbar)
        layout.addWidget(self._canvas, stretch=1)

    def show_message(self, text):
        self._summary.setText(text)
        self._artist.set_data([], [])
        self._axes.relim()
        self._axes.autoscale_view()
        self._canvas.draw_idle()

    def show_profile(self, label, distances, values):
        plotted = [float("nan") if value is None else float(value) for value in values]
        finite = [value for value in plotted if value == value]
        length = distances[-1] if distances else 0.0
        if finite:
            self._summary.setText(
                f"{label}    {length:.2f} mm    min {min(finite):.1f}    max {max(finite):.1f}"
            )
        else:
            self._summary.setText(f"{label}    {length:.2f} mm    no pixels under this line")
        self._axes.set_title(label)
        self._artist.set_data(distances, plotted)
        self._axes.relim()
        self._axes.autoscale_view()
        self._canvas.draw_idle()
