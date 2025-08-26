# ruff: noqa: FBT001, S104

import subprocess
from pathlib import Path
from unittest import mock

import pytest

from launcher.cli import (
    cli,
    prepare_run_command,
    resolve_notebook_directory,
    resolve_notebook_path,
)


def test_resolve_notebook_directory_mount(tmp_path: Path) -> None:
    notebook_dir = tmp_path / "nb"
    notebook_dir.mkdir()
    resolved_notebook_dir = resolve_notebook_directory(mount=str(notebook_dir))
    assert resolved_notebook_dir == notebook_dir


def test_resolve_notebook_directory_missing_mount(tmp_path: Path) -> None:
    missing = tmp_path / "does-not-exist"
    with pytest.raises(FileNotFoundError):
        resolve_notebook_directory(mount=str(missing))


def test_resolve_notebook_directory_repo_creates_dir_via_git_clone(
    tmp_path: Path, mocked_git_clone
) -> None:
    notebook_dir = resolve_notebook_directory(
        mount=None, repo="https://example.com/x.git", repo_branch="main"
    )

    assert notebook_dir.is_dir()
    assert Path(mocked_git_clone[0]) == notebook_dir


def test_resolve_notebook_path_exists(tmp_path: Path) -> None:
    notebook_file = tmp_path / "notebook.py"
    notebook_file.write_text("print('hi')\n")
    resolved_path = resolve_notebook_path(tmp_path, "notebook.py")
    assert resolved_path == notebook_file


def test_resolve_notebook_path_missing(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        resolve_notebook_path(tmp_path, "missing.py")


@pytest.mark.parametrize(
    ("has_requirements", "token"),
    [
        (False, None),
        (False, "secret-token"),
        (True, None),
        (True, "secret-token"),
    ],
)
@pytest.mark.parametrize("mode", ["run", "edit"])
def test_prepare_run_command_variants(
    tmp_path: Path,
    has_requirements: bool,
    token: str | None,
    mode: str,
) -> None:
    requirements = tmp_path / "requirements.txt"
    if has_requirements:
        requirements.write_text("marimo==0.14.17\n")
        requirements_path: Path | None = requirements
    else:
        requirements_path = None

    command = prepare_run_command(
        mode=mode,
        host="127.0.0.1",
        port=8888,
        token=token,
        notebook_path="notebook.py",
        requirements_file=requirements_path,
    )

    # must start with uv run
    assert command[:2] == ["uv", "run"]

    # requirements handling
    if has_requirements:
        assert "--with-requirements" in command
        assert str(requirements) in command
        assert "--sandbox" not in command
    else:
        assert "--sandbox" in command
        assert "--with-requirements" not in command

    # token handling
    if token:
        assert ["--token", "--token-password", token] == command[-4:-1]
    else:
        assert "--no-token" in command

    # notebook path is last
    assert command[-1] == "notebook.py"


def test_cli_no_commands(caplog, runner):
    result = runner.invoke(cli, [])
    assert result.exit_code == 2


def test_cli_subprocess_run_minimal_required_args_get_defaults_success(runner):
    """Mock subprocess.run to simulate valid notebook run and exit."""
    args = ["run", "--mount", "tests/fixtures/inline_deps"]

    with mock.patch("launcher.cli.subprocess.run") as mock_subprocess_run:
        mock_subprocess_run.return_value = subprocess.CompletedProcess(
            args=args, returncode=0
        )
        _result = runner.invoke(cli, args)

    # assert subproces.run has correct working directory of notebook
    assert mock_subprocess_run.call_args.kwargs.get("cwd") == "tests/fixtures/inline_deps"

    # assert subprocess.run had defaults applied
    assert mock_subprocess_run.call_args.args[0] == [
        "uv",
        "run",
        "marimo",
        "run",
        "--headless",
        "--host",
        "0.0.0.0",
        "--port",
        "2718",
        "--sandbox",
        "--no-token",
        "--base-url",
        "/tests/fixtures/inline_deps/notebook.py",
        "notebook.py",
    ]


def test_cli_subprocess_run_base_url_override(runner):
    args = [
        "run",
        "--mount",
        "tests/fixtures/inline_deps",
        "--base-url",
        "/my/super/path.py",
    ]

    with mock.patch("launcher.cli.subprocess.run") as mock_subprocess_run:
        mock_subprocess_run.return_value = subprocess.CompletedProcess(
            args=args, returncode=0
        )
        _result = runner.invoke(cli, args)

    # assert subproces.run has correct working directory of notebook
    assert mock_subprocess_run.call_args.kwargs.get("cwd") == "tests/fixtures/inline_deps"

    # assert subprocess.run had defaults applied
    assert mock_subprocess_run.call_args.args[0] == [
        "uv",
        "run",
        "marimo",
        "run",
        "--headless",
        "--host",
        "0.0.0.0",
        "--port",
        "2718",
        "--sandbox",
        "--no-token",
        "--base-url",
        "/my/super/path.py",
        "notebook.py",
    ]


def test_cli_subprocess_run_skip_base_url(runner):
    args = ["run", "--mount", "tests/fixtures/inline_deps", "--skip-base-url"]

    with mock.patch("launcher.cli.subprocess.run") as mock_subprocess_run:
        mock_subprocess_run.return_value = subprocess.CompletedProcess(
            args=args, returncode=0
        )
        _result = runner.invoke(cli, args)

    # assert subproces.run has correct working directory of notebook
    assert mock_subprocess_run.call_args.kwargs.get("cwd") == "tests/fixtures/inline_deps"

    # assert subprocess.run had defaults applied
    assert mock_subprocess_run.call_args.args[0] == [
        "uv",
        "run",
        "marimo",
        "run",
        "--headless",
        "--host",
        "0.0.0.0",
        "--port",
        "2718",
        "--sandbox",
        "--no-token",
        "notebook.py",
    ]


def test_cli_subprocess_run_missing_mount_or_repo_args_error(runner):
    args = ["run"]

    result = runner.invoke(cli, args)

    assert result.exit_code == 1
    assert (
        str(result.exception)
        == "either --mount/NOTEBOOK_MOUNT or --repo/NOTEBOOK_REPOSITORY must be provided"
    )


def test_cli_subprocess_run_bad_notebook_path_error(runner):
    args = ["run", "--mount", "tests/fixtures/inline_deps", "--path", "bad-notebook.py"]

    result = runner.invoke(cli, args)

    assert result.exit_code == 1
    assert (
        str(result.exception)
        == "notebook path not found: tests/fixtures/inline_deps/bad-notebook.py"
    )
