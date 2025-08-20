import pytest
from click.testing import CliRunner

import launcher.cli as cli_module


@pytest.fixture(autouse=True)
def _test_env(monkeypatch):
    monkeypatch.setenv("SENTRY_DSN", "None")
    monkeypatch.setenv("WORKSPACE", "test")


@pytest.fixture
def runner():
    return CliRunner()


@pytest.fixture
def mocked_git_clone(monkeypatch):
    """Simulate a successful git clone by creating the target directory."""
    created: list[str] = []

    def _fake_clone(target, repo: str, branch: str | None = None):
        target.mkdir(parents=True, exist_ok=True)
        created.append(str(target))

    monkeypatch.setattr(cli_module, "clone_notebook_repository", _fake_clone)

    return created
