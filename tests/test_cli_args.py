import os

from cli_args import cli_project_path, project_image_path, resolve_cli_project_path


def test_cli_project_path_flag_and_bare_json():
    json_path = r"\\fileserver\QA\case\vtk_image_labeler_2d.project.json"
    assert cli_project_path(["app", "--project", json_path]) == json_path
    assert cli_project_path(["app", "--project=" + json_path]) == json_path
    assert cli_project_path(["app", "--open", json_path]) == json_path
    assert cli_project_path(["app", json_path]) == json_path
    assert cli_project_path(["app", "--smoke-test"]) is None
    assert cli_project_path(["app"]) is None


def test_resolve_cli_project_path(tmp_path):
    dest = tmp_path / "vtk_image_labeler_2d.project.json"
    dest.write_text("{}\n", encoding="utf-8")
    resolved = resolve_cli_project_path(["ImageLabeler2D.exe", "--project", str(dest)])
    assert resolved == str(dest.resolve())


def test_project_image_path_resolves_relative_to_the_json(tmp_path):
    image = tmp_path / "input.dcm"
    image.write_bytes(b"")
    project = tmp_path / "_viewer" / "vtk_image_labeler_2d.project.json"
    project.parent.mkdir()
    data = {"kind": "vtk_image_labeler_2d_project", "image": "../input.dcm"}
    assert os.path.normcase(project_image_path(str(project), data)) == os.path.normcase(os.path.abspath(image))
    assert project_image_path(str(project), {"window_settings": {}}) is None
    assert project_image_path(str(project), {"kind": "vtk_image_labeler_2d_project"}) == ""
