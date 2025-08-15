import logging
import subprocess
import sys
import uuid
from pathlib import Path

import click

from launcher.config import configure_logger, configure_sentry

logger = logging.getLogger(__name__)


@click.group("launcher")
@click.option(
    "-v",
    "--verbose",
    is_flag=True,
    help="Pass to log at debug level instead of info",
)
@click.pass_context
def cli(
    _ctx: click.Context,
    *,
    verbose: bool,
) -> None:
    root_logger = logging.getLogger()
    logger.info(configure_logger(root_logger, verbose=verbose))
    logger.info(configure_sentry())


@cli.command()
@click.option(
    "--mount",
    envvar="NOTEBOOK_MOUNT",
    type=click.Path(path_type=Path),
    help="path to mounted / existing notebook directory (env: NOTEBOOK_MOUNT)",
)
@click.option(
    "--repo",
    envvar="NOTEBOOK_REPOSITORY",
    help="git repository URL containing the notebook (env: NOTEBOOK_REPOSITORY)",
)
@click.option(
    "--path",
    "notebook_path",
    envvar="NOTEBOOK_PATH",
    help="relative path to the notebook within the directory (env: NOTEBOOK_PATH)",
    default="notebook.py",
)
@click.option(
    "--requirements",
    "requirements_file",
    envvar="NOTEBOOK_REQUIREMENTS",
    type=click.Path(path_type=Path),
    help="path to requirements file for environment (env: NOTEBOOK_REQUIREMENTS)",
)
@click.option(
    "--mode",
    envvar="NOTEBOOK_MODE",
    default="run",
    show_default=True,
    help="launch mode, 'run' or 'edit' (env: NOTEBOOK_MODE)",
)
@click.option(
    "--host",
    envvar="NOTEBOOK_HOST",
    default="0.0.0.0",  # noqa: S104
    show_default=True,
    help="host interface to bind (env: NOTEBOOK_HOST)",
)
@click.option(
    "--port",
    envvar="NOTEBOOK_PORT",
    default=2718,
    show_default=True,
    type=int,
    help="port to bind (env: NOTEBOOK_PORT)",
)
@click.option(
    "--no-token/--token",
    default=True,
    show_default=True,
    help="run marimo without auth token",
)
@click.pass_context
def run(
    _ctx: click.Context,
    *,
    mount: Path | None,
    repo: str | None,
    notebook_path: str,
    requirements_file: Path | None,
    mode: str,
    host: str,
    port: int,
    no_token: bool,
) -> None:
    """Launch notebook in 'run' or 'edit' mode."""
    try:
        dir_path = resolve_notebook_directory(str(mount) if mount else None, repo)
        ensure_repo_cloned(dir_path, repo)
        full_notebook_path = resolve_notebook_path(dir_path, notebook_path)

        cmd = prepare_run_command(
            mode=mode,
            host=host,
            port=port,
            no_token=no_token,
            notebook_path=notebook_path,
            requirements_file=requirements_file,
        )

        logger.info(f"launching notebook '{full_notebook_path}' with args {cmd}")

        result = subprocess.run(cmd, cwd=str(dir_path), check=True)  # noqa: S603

        raise sys.exit(result.returncode)

    except (ValueError, FileNotFoundError, RuntimeError) as exc:
        click.echo(f"Error: {exc}", err=True)
        sys.exit(2)


def resolve_notebook_directory(mount: str | None, repo: str | None) -> Path:
    """Determine the root directory that will contain the notebook.

    Resolution rules:
    1) If "mount" is provided:
       - Validate that the path exists and return it.
    2) Else if "repo" is provided:
       - Clone repository to /tmp/notebook-<UUID> and return this location.
    3) Else:
       - Raise an error because at least one of the two is required.

    Args:
        - mount: Optional path to an existing host directory to use directly.
        - repo: Optional git repository URL to clone into a workspace.
    """
    if mount:
        p = Path(mount)
        if not p.exists():
            raise FileNotFoundError(f"NOTEBOOK_MOUNT path does not exist: {mount}")
        return p

    if repo:
        workdir = Path("/tmp")  # noqa: S108
        workdir.mkdir(parents=True, exist_ok=True)
        return workdir / f"notebook-clone-{uuid.uuid4()}"

    raise ValueError("either NOTEBOOK_MOUNT or NOTEBOOK_REPOSITORY must be provided")


def ensure_repo_cloned(notebook_dir: Path, repo: str | None) -> None:
    """Clone a repository and set as the notebook directory.

    Behavior:
    - If repo is provided AND the target directory does not exist, run:
      git clone <repo> <notebook_dir>
    - If the directory already exists or repo is None, do nothing.

    Args:
        - notebook_dir: Destination directory for the repository checkout.
        - repo: Git repository URL to clone (e.g., https://..., or SSH URL).
    """
    if repo and not notebook_dir.exists():
        result = subprocess.run(  # noqa: S603
            ["git", "clone", repo, str(notebook_dir)],  # noqa: S607
            check=True,
        )
        if result.returncode != 0:
            raise RuntimeError(f"git clone failed with code {result.returncode}")


def resolve_notebook_path(notebook_dir: Path, notebook_path: str) -> Path:
    """Build and validate the absolute path to the notebook file within notebook_dir.

    Args:
        - notebook_dir: Base directory that contains the notebook file.
        - notebook_path: Relative path (or filename) of the notebook within notebook_dir.
    """
    full_path = notebook_dir / notebook_path
    if not full_path.exists():
        raise FileNotFoundError(f"notebook path not found: {full_path}")
    return full_path


def prepare_run_command(
    *,
    mode: str,
    host: str,
    port: int,
    no_token: bool,
    notebook_path: str,
    requirements_file: Path | None,
) -> list[str]:
    """Build the shell command used to launch a marimo notebook via `uv run`.

    The command has the following general shape:
      uv run [--with-requirements <file>] marimo <mode> --host <host> --port <port>
        [--sandbox] [--no-token] <notebook_path>

    Behavior:
    - If a requirements file is provided, `uv run --with-requirements <file>` is used so
        the notebook runs with those pinned dependencies.
    - If no requirements file is provided, `--sandbox` is added to marimo to avoid
        mutating the user's environment.
    - `--no-token` disables marimo's auth token if requested.
    - The final positional argument is the path to the notebook to run.

    Args:
        - mode: marimo subcommand to run (e.g., "run", "edit").
        - host: interface to bind the marimo server to (e.g., "127.0.0.1", "0.0.0.0").
        - port: TCP port for the marimo server.
        - no_token: when True, add `--no-token` to disable auth.
        - notebook_path: path to the marimo notebook file.
        - requirements_file: optional path to a requirements file for `uv` (enables
            `--with-requirements`).
    """
    # start with `uv run` so marimo executes in a managed Python environment
    cmd: list[str] = ["uv", "run"]

    # if a requirements file is provided, ensure uv uses it for dependency resolution
    if requirements_file:
        cmd += ["--with-requirements", str(requirements_file)]

    cmd += [
        "marimo",
        mode,
        "--host",
        host,
        "--port",
        str(port),
    ]

    # without a dedicated requirements file, prefer an isolated/sandboxed environment
    if not requirements_file:
        cmd += ["--sandbox"]

    # optionally disable auth token
    if no_token:
        cmd += ["--no-token"]

    # path to the notebook is the final positional argument
    cmd += [str(notebook_path)]

    return cmd


def main() -> None:
    """CLI entrypoint wrapper for package scripts."""
    cli()


if __name__ == "__main__":
    logger = logging.getLogger("launcher.cli")
    main()
