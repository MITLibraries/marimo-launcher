# marimo-launcher

## Development

- To preview a list of available Makefile commands: `make help`
- To install with dev dependencies: `make install`
- To update dependencies: `make update`
- To run unit tests: `make test`
- To lint the repo: `make lint`
- To run the app: `uv run launcher --help`

## Overview

This CLI is an application to launch _other_ Marimo notebooks.  There are two ways in which this CLI can launch a notebook:

1. The notebook is available on the same machine as the CLI, e.g. mounted into the Docker container
2. A Github repository is passed and cloned by the CLI that contains a notebook

Because this CLI is meant to launch notebooks, it does not have a dedicated ECS task or service.

Take a fictional example of a notebook called "Analyze All the Things (AATT)" in the repository `marimo-aatt`.  To provide this notebook for use, an ECS task would be created that sets two important environment variables:

  - `NOTEBOOK_REPOSITORY=https://github.com/MITLibraries/marimo-aatt`
  - `NOTEBOOK_PATH=aatt.py` (a non-default notebook path)

The ECS task / service would invoke this `marimo-launcher` CLI, and this CLI would perform the following:

1. Clone the Github repository into the container
2. Install dependencies
3. Launch the notebook `aatt.py`

More information about structuring notebooks and dependencies below in "Preparing Notebooks". 

## Preparing Notebooks

### Notebook Location
This CLI expects two primary things to discover the notebook to launch:

1. The root directory of the notebook project (either mounted or a cloned Github repository)
2. Path to the actual notebook python file to run

The root of the notebook directory is set either by CLI arg `--repo` / env var `NOTEBOOK_REPOSITORY` or CLI arg `--mount` / env var `NOTEBOOK_MOUNT` (less common, more for dev work).  In either approach, a notebook directory is established and all other filepaths -- e.g. notebook or requirements -- are **relative** to this path.

The default notebook path is `notebook.py` and is expected in the root of the cloned or mounted notebook repository.  The CLI arg `--path` or env var `NOTEBOOK_PATH` can be passed to override this.  

### Notebook Dependencies

There are two primary ways to handle dependencies for a notebook launched by this CLI:

1. Inline dependencies
2. External dependencies requirement file

#### 1- Inline dependencies

This is the **default** behavior for this CLI.

Python [PEP 723](https://peps.python.org/pep-0723/) introduced inline dependencies for a python file.  Marimo [fully supports this](https://docs.marimo.io/guides/package_management/inlining_dependencies/) for notebooks as well.

Inline dependencies are a text block at the top of the python notebook that outline what dependencies should be installed.  This section looks and feels much like sections in the `pyproject.toml`.  Here is a minimal example from `tests/fixtures/inline_deps/notebook.py`:

```python
# /// script
# requires-python = ">=3.13"
# dependencies = [
#     "marimo",
#     "tinydb==4.8.2",
# ]
# ///

# rest of notebook here...
```

When the CLI launches this notebook it will include the flag `--sandbox` when running Marimo that instructs Marimo to use the inlined dependencies.

The `Makefile` command `cli-test-inline-run` will demonstrate this.

#### 2- External dependencies requirement file

Another option, which requires the CLI flag `--requirements` or env var `NOTEBOOK_REQUIREMENTS`, is to install dependencies found in a standalone requirements file, e.g. `requirements.txt`.  The tests fixture `tests/fixtures/static_deps_reqs_txt/requirements.txt` shows an example of this kind of file.

The flag `--requirements` or env var `NOTEBOOK_REQUIREMENTS` should point to a relative path from the root of the notebook directory where this file can be found.  When passed, Marimo will be launched with the flag `--with-requirements` which instructs it to created an isolated environment with these dependencies.

There are many ways to create this file, [`uv export` is worth consideration](https://docs.astral.sh/uv/reference/cli/#uv-export).

The `Makefile` command `cli-test-reqs-txt-run` will demonstrate this.


## Environment Variables

### Required

```shell
SENTRY_DSN=### If set to a valid Sentry DSN, enables Sentry exception monitoring. This is not needed for local development.
WORKSPACE=### Set to `dev` for local development, this will be set to `stage` and `prod` in those environments by Terraform.
```

### Optional

Set these if you want to override defaults or pass values via env instead of flags. Keep them unset if you use CLI options.

```shell
NOTEBOOK_REPOSITORY= ### repository to clone that contains a notebook and any required assets
NOTEBOOK_REPOSITORY_BRANCH= ### optional branch to checkout on clone
NOTEBOOK_MOUNT= ### either local of Docker context, an accessible root directory that contains notebook(s)
NOTEBOOK_PATH=### Relative path of actual notebook .py file based on cloned repository or mounted directory; defaults to "notebook.py"
NOTEBOOK_REQUIREMENTS= ### filepath to install dependencies from, relative to notebook root; if unset assuming dependencies are inline in notebook

NOTEBOOK_MODE= ### how to launch marimo: "run" to execute, "edit" to open the editor; default "run"
NOTEBOOK_HOST= ### host to bind running notebook to
NOTEBOOK_PORT= ### port to serve running notebook on
```


## CLI Commands

### `launcher`

Base command

```text
Usage: marimo-launcher [OPTIONS] COMMAND [ARGS]...

Options:
  -v, --verbose  Pass to log at debug level instead of info
  --help         Show this message and exit.

Commands:
  run  Launch notebook in 'run' or 'edit' mode.
```

### `launcher run`

```text
Usage: marimo-launcher run [OPTIONS]

  Launch notebook in 'run' or 'edit' mode.

Options:
  --mount PATH         path to mounted / existing notebook directory (env:
                       NOTEBOOK_MOUNT)
  --repo TEXT          git repository URL containing the notebook (env:
                       NOTEBOOK_REPOSITORY)
  --repo-branch TEXT   optional branch to checkout from cloned notebook
                       repository (env: NOTEBOOK_REPOSITORY_BRANCH)
  --path TEXT          relative path to the notebook within the directory
                       (env: NOTEBOOK_PATH)
  --requirements PATH  path to requirements file for environment (env:
                       NOTEBOOK_REQUIREMENTS)
  --mode [run|edit]    launch mode, 'run' or 'edit' (env: NOTEBOOK_MODE)
                       [default: run]
  --host TEXT          host interface to bind (env: NOTEBOOK_HOST)  [default:
                       0.0.0.0]
  --port INTEGER       port to bind (env: NOTEBOOK_PORT)  [default: 2718]
  --token TEXT         set a required authentication token/password for the
                       notebook; if not set, no token/password is required
                       (env: NOTEBOOK_TOKEN)
  --base-url TEXT      explicit base URL prefix to pass through to marimo on
                       notebook launch (env: NOTEBOOK_BASE_URL)
  --help               Show this message and exit.
```




