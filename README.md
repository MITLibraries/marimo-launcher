# marimo-launcher

## Development

- To preview a list of available Makefile commands: `make help`
- To install with dev dependencies: `make install`
- To update dependencies: `make update`
- To run unit tests: `make test`
- To lint the repo: `make lint`
- To run the app: `uv run launcher --help`

## Preparing Notebooks

_TODO: Explain how this launcher will find a root + file, and the default `notebook.py` convention._

_TODO: Explain how dependencies can be [inlined](https://docs.marimo.io/guides/package_management/inlining_dependencies/) or an external file and [`uv`'s `--with-requirements` flag](https://docs.astral.sh/uv/reference/cli/#uv-run--with-requirements) is used.  Could be helpful to link to [`uv export`](https://docs.astral.sh/uv/reference/cli/#uv-export) as a good way to take a `uv` project and produce a single `requirements.txt` file._ 

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
Usage: launcher [OPTIONS] COMMAND [ARGS]...

Options:
  -v, --verbose  Pass to log at debug level instead of info
  --help         Show this message and exit.

Commands:
  run
  validate
```

### `launcher run`

```text
Usage: python -m launcher.cli run [OPTIONS]

  Launch notebook in 'run' or 'edit' mode.

Options:
  --mount PATH          path to mounted / existing notebook directory (env:
                        NOTEBOOK_MOUNT)
  --repo TEXT           git repository URL containing the notebook (env:
                        NOTEBOOK_REPOSITORY)
  --path TEXT           relative path to the notebook within the directory
                        (env: NOTEBOOK_PATH)
  --requirements PATH   path to requirements file for environment (env:
                        NOTEBOOK_REQUIREMENTS)
  --mode TEXT           launch mode, 'run' or 'edit' (env: NOTEBOOK_MODE)
                        [default: run]
  --host TEXT           host interface to bind (env: NOTEBOOK_HOST)  [default:
                        0.0.0.0]
  --port INTEGER        port to bind (env: NOTEBOOK_PORT)  [default: 2718]
  --no-token / --token  run marimo without auth token  [default: no-token]
  --help                Show this message and exit.
```




