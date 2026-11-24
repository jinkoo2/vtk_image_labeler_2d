"""Ensure the frozen app resolves imports and finds .env next to the executable."""

import importlib
import os
import sys


def _alias_vtk_modules():
    """vtk.qt is only an alias of vtkmodules.qt. PyInstaller does not follow it."""
    for alias, real in (
        ("vtk.qt", "vtkmodules.qt"),
        ("vtk.qt.QVTKRenderWindowInteractor", "vtkmodules.qt.QVTKRenderWindowInteractor"),
        ("vtk.util", "vtkmodules.util"),
        ("vtk.util.numpy_support", "vtkmodules.util.numpy_support"),
    ):
        if alias in sys.modules:
            continue
        try:
            sys.modules[alias] = importlib.import_module(real)
        except Exception:
            pass


def _ensure_path():
    if getattr(sys, "frozen", False):
        meipass = getattr(sys, "_MEIPASS", None)
        if meipass and meipass not in sys.path:
            sys.path.insert(0, meipass)
        exe_dir = os.path.dirname(sys.executable)
        if exe_dir and os.path.isdir(exe_dir):
            try:
                os.chdir(exe_dir)
            except OSError:
                pass


_alias_vtk_modules()
_ensure_path()
