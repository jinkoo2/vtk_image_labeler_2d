# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for Image Labeler 2D (onedir)."""

import re
import sys
from pathlib import Path

from PyInstaller.building.api import COLLECT, EXE, PYZ
from PyInstaller.building.build_main import Analysis
from PyInstaller.utils.hooks import collect_all, collect_submodules

SPEC_DIR = Path(SPECPATH).resolve()
ROOT = SPEC_DIR.parent
ENTRY = ROOT / "vtkapp.py"

datas = []
binaries = []
hiddenimports = []

icons = ROOT / "icons"
if icons.exists():
    datas.append((str(icons), "icons"))

for name in ("vtk", "PyQt5", "SimpleITK"):
    try:
        d, b, h = collect_all(name)
        datas += d
        binaries += b
        hiddenimports += h
    except Exception as exc:  # noqa: BLE001 - best-effort collection
        print(f"collect_all({name!r}) skipped: {exc}", file=sys.stderr)

for package in ("vtkmodules.util", "vtkmodules.qt"):
    try:
        hiddenimports += collect_submodules(package)
    except Exception as exc:  # noqa: BLE001
        print(f"collect_submodules({package!r}) skipped: {exc}", file=sys.stderr)

hiddenimports += [
    "vtkmodules",
    "vtkmodules.util",
    "vtkmodules.util.numpy_support",
    "vtkmodules.qt",
    "vtkmodules.qt.QVTKRenderWindowInteractor",
    "dotenv",
    "config",
    "logger",
    "cli_args",
    "splash_screen",
    "version",
    "itk",
    "itkvtk",
    "vtk_tools",
    "color_rotator",
    "line_edit2",
    "labeled_slider",
    "rangeslider",
    "nnunet_service",
    "nnunet_client_manager",
    "vtk_segmentation_list_manager",
    "vtk_point_list_manager",
    "vtk_line_list_manager",
    "line_profile",
    "matplotlib.backends.backend_qt5agg",
    "vtk_rect_list_manager",
]

# Host OS should supply these; shipping copies from a newer distro
# (e.g. Ubuntu 24.04) causes GLIBC_2.38-not-found on older desktops.
_SYSTEM_LIB_PREFIXES = (
    "libX11",
    "libXext",
    "libXrender",
    "libXfixes",
    "libXinerama",
    "libXi",
    "libXrandr",
    "libXcursor",
    "libXdamage",
    "libXcomposite",
    "libXtst",
    "libXxf86vm",
    "libXss",
    "libxcb",
    "libbsd",
    "libmd.so",
)


def _is_os_x11_lib(dest_name: str) -> bool:
    name = Path(str(dest_name)).name
    if re.search(r"-[0-9a-f]{6,}\.so", name):
        return False
    return any(name.startswith(prefix) for prefix in _SYSTEM_LIB_PREFIXES)


a = Analysis(
    [str(ENTRY)],
    pathex=[str(ROOT)],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[str(SPEC_DIR / "runtime_hook_path.py")],
    excludes=[],
    noarchive=False,
)

kept_bins = []
dropped = []
for entry in a.binaries:
    dest = entry[0]
    if _is_os_x11_lib(dest):
        dropped.append(dest)
    else:
        kept_bins.append(entry)
if dropped:
    print(
        f"Excluded {len(dropped)} OS X11/bsd libs from bundle "
        f"(examples: {', '.join(dropped[:5])})",
        file=sys.stderr,
    )
a.binaries = kept_bins

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="ImageLabeler2D",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=True,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="ImageLabeler2D",
)
