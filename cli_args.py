"""Command-line project JSON for source and frozen (PyInstaller) launches."""

from __future__ import annotations

import os
import sys
from pathlib import Path

PROJECT_KIND = "vtk_image_labeler_2d_project"
PROJECT_FLAGS = ("--project", "--open", "-p")


def windows_command_line_argv() -> list[str]:
    """Windows process argv from GetCommandLineW (not Python/PyInstaller sys.argv)."""
    if os.name != "nt":
        return []
    try:
        import ctypes
        from ctypes import wintypes

        GetCommandLineW = ctypes.windll.kernel32.GetCommandLineW
        CommandLineToArgvW = ctypes.windll.shell32.CommandLineToArgvW
        LocalFree = ctypes.windll.kernel32.LocalFree
        GetCommandLineW.restype = ctypes.c_wchar_p
        CommandLineToArgvW.argtypes = [wintypes.LPCWSTR, ctypes.POINTER(ctypes.c_int)]
        CommandLineToArgvW.restype = ctypes.POINTER(ctypes.c_wchar_p)
        argc = ctypes.c_int(0)
        argv_p = CommandLineToArgvW(GetCommandLineW(), ctypes.byref(argc))
        if not argv_p:
            return []
        out = [argv_p[i] for i in range(argc.value)]
        LocalFree(argv_p)
        return out
    except Exception:
        return []


def cli_project_path(argv) -> str | None:
    """Return a project JSON path from argv, or None.

    Accepts ``--project PATH``, ``--open PATH``, ``-p PATH``, ``--project=PATH``,
    or a bare ``*.json`` argument.
    """
    args = [str(a) for a in list(argv or [])[1:]]
    i = 0
    while i < len(args):
        a = args[i]
        if a in PROJECT_FLAGS:
            if i + 1 >= len(args):
                return None
            return args[i + 1]
        if a.startswith("--project=") or a.startswith("--open="):
            return a.split("=", 1)[1]
        if (not a.startswith("-")) and a.lower().endswith(".json"):
            return a
        i += 1
    return None


def resolve_cli_project_path(argv=None) -> str | None:
    """Best-effort project path from Python argv and the Windows command line."""
    candidates = [argv if argv is not None else sys.argv, windows_command_line_argv()]
    for source in candidates:
        raw = cli_project_path(source)
        if not raw:
            continue
        path = Path(raw).expanduser()
        try:
            return str(path.resolve())
        except OSError:
            return str(path)
    return None


def project_image_path(workspace_json_path, data):
    """Image path for a 2D project JSON. None when this is a saved workspace."""
    if not isinstance(data, dict):
        return None
    kind = str(data.get("kind") or "")
    image = data.get("image")
    is_project = kind == PROJECT_KIND or (image is not None and str(image).strip() != "")
    if not is_project:
        return None
    image_rel = str(image or "").strip()
    if not image_rel:
        return ""
    if os.path.isabs(image_rel):
        return os.path.normpath(image_rel)
    folder = os.path.dirname(os.path.abspath(workspace_json_path))
    return os.path.normpath(os.path.join(folder, image_rel))
