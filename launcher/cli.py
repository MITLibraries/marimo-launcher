import logging
import subprocess
import sys
import uuid
from pathlib import Path
from typing import Literal

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
    "--repo-branch",
    envvar="NOTEBOOK_REPOSITORY_BRANCH",
    help=(
        "optional branch to checkout from cloned notebook repository "
        "(env: NOTEBOOK_REPOSITORY_BRANCH)"
    ),
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
    type=click.Choice(["run", "edit"]),
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
    "--token",
    envvar="NOTEBOOK_TOKEN",
    default=None,
    show_default=True,
    help=(
        "set a required authentication token/password for the notebook; "
        "if not set, no token/password is required (env: NOTEBOOK_TOKEN)"
    ),
)
@click.option(
    "--base-url",
    envvar="NOTEBOOK_BASE_URL",
    default=None,
    show_default=True,
    help=(
        "explicit base URL prefix to pass through to marimo; "
        "by default it's constructed from repository + notebook path "
        "(env: NOTEBOOK_BASE_URL)"
    ),
)
@click.option(
    "--skip-base-url",
    is_flag=True,
    envvar="NOTEBOOK_SKIP_BASE_URL",
    help=(
        "skip setting Marimo configuration --base-url when launching the notebook; "
        "can be set with (env: NOTEBOOK_SKIP_BASE_URL=1)"
    ),
)
@click.pass_context
def run(
    _ctx: click.Context,
    *,
    mount: Path | None,
    repo: str | None,
    repo_branch: str | None,
    notebook_path: str,
    requirements_file: Path | None,
    mode: Literal["run", "edit"],
    host: str,
    port: int,
    token: str | None,
    base_url: str | None,
    skip_base_url: bool,
) -> None:
    """Launch notebook in 'run' or 'edit' mode."""
    notebook_dir_path = resolve_notebook_directory(
        mount=str(mount) if mount else None,
        repo=repo,
        repo_branch=repo_branch,
    )
    full_notebook_path = resolve_notebook_path(notebook_dir_path, notebook_path)

    if base_url is None and not skip_base_url:
        base_url = resolve_base_url(mount, repo, notebook_path)

    cmd = prepare_run_command(
        mode=mode,
        host=host,
        port=port,
        token=token,
        notebook_path=notebook_path,
        requirements_file=requirements_file,
        base_url=base_url,
    )

    logger.info(f"launching notebook '{full_notebook_path}' with args {cmd}")

    result = subprocess.run(cmd, cwd=str(notebook_dir_path), check=True)  # noqa: S603

    raise sys.exit(result.returncode)


def resolve_notebook_directory(
    mount: str | None = None,
    repo: str | None = None,
    repo_branch: str | None = None,
) -> Path:
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
        - repo_branch: Optional git branch to checkout for notebook repository.
    """
    if mount:
        notebook_dir_path = Path(mount)
        if not notebook_dir_path.exists():
            raise FileNotFoundError(f"NOTEBOOK_MOUNT path does not exist: {mount}")
        return notebook_dir_path

    if repo:
        workdir = Path("/tmp")  # noqa: S108
        workdir.mkdir(parents=True, exist_ok=True)
        notebook_dir_path = workdir / f"notebook-clone-{uuid.uuid4()}"

        clone_notebook_repository(notebook_dir_path, repo, repo_branch)

        return notebook_dir_path

    raise ValueError(
        "either --mount/NOTEBOOK_MOUNT or --repo/NOTEBOOK_REPOSITORY must be provided"
    )


def clone_notebook_repository(
    notebook_dir: Path,
    repo: str,
    repo_branch: str | None = None,
) -> None:
    """Clone a notebook repository to a target directory.

    Behavior:
    - If the target directory does not already exist, clone the repository.
    - If the directory already exists or repo is None, do nothing.

    Args:
        - notebook_dir: Destination directory for the repository checkout.
        - repo: Git repository URL to clone (e.g., https://..., or SSH URL).
        - repo_branch: Optional, git branch to checkout during clone
    """
    if not notebook_dir.exists():
        cmd = [
            "git",
            "clone",
        ]

        if repo_branch:
            cmd += ["--branch", repo_branch]

        cmd += [repo, str(notebook_dir)]
        logger.info(f"Cloning repository with args: {cmd}")

        result = subprocess.run(cmd, check=True)  # noqa: S603

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


def resolve_base_url(
    mount: Path | None,
    repo: str | None,
    notebook_path: str,
) -> str:
    """Construct a base URL for the notebook to listen on after launch.

    This correlates to the --base-url flag when starting a Marimo notebook.  Because it's
    likely the notebook will be launched inside an ECS container, and serve requests from
    an Automatic Load Balancer (ALB), it's possible we may not have control over the URL
    request that is made.  This allows launching the notebook at a URL path we know
    requests will come in over.

    The default behavior is to take the repository name + full notebook path.  For example
    if `--repo=https://github.com/foo/my-repo` and `--path=super/duper/analyzer.py` is
    passed, the final result will be `--base-url=my-repo/super/duper/analyzer.py`.
    """
    base_url = "/"

    if mount:
        base_url += str(mount).removeprefix("/")

    if repo:
        base_url += repo.split("/")[-1]

    base_url += f"/{notebook_path}"

    return base_url


def prepare_run_command(
    *,
    mode: str,
    host: str,
    port: int,
    token: str | None,
    notebook_path: str,
    requirements_file: Path | None,
    base_url: str | None = None,
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
        - token: if not None, set as token for notebook, else launch with --no-token
        - notebook_path: path to the marimo notebook file.
        - requirements_file: optional path to a requirements file for `uv` (enables
            `--with-requirements`).
        - base_url: base URL path launched notebook will listen on
            e.g. host:port/<base_url>
    """
    # start with `uv run` so marimo executes in a managed Python environment
    cmd: list[str] = ["uv", "run"]

    # if a requirements file is provided, ensure uv uses it for dependency resolution
    if requirements_file:
        cmd += ["--with-requirements", str(requirements_file)]

    cmd += [
        "marimo",
        mode,
        "--headless",
        "--host",
        host,
        "--port",
        str(port),
    ]

    # without a dedicated requirements file, prefer an isolated/sandboxed environment
    if not requirements_file:
        cmd += ["--sandbox"]

    # set token if passed
    if token:
        cmd += ["--token", "--token-password", token]
    else:
        cmd += ["--no-token"]

    # set base url flag if passed
    if base_url:
        cmd += ["--base-url", base_url]

    # path to the notebook is the final positional argument
    cmd += [str(notebook_path)]

    return cmd


def main() -> None:
    """CLI entrypoint wrapper for package scripts."""
    cli()


if __name__ == "__main__":
    logger = logging.getLogger("launcher.cli")
    main()
