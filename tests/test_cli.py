from launcher.cli import cli


def test_cli_no_commands(caplog, runner):
    result = runner.invoke(cli, [])
    assert result.exit_code == 2
