"""The Operator: the program `jobapply run` starts at the letter step instead of the applicant switching windows."""

import os
import stat
from pathlib import Path

import pytest

from jobapply.operator import operator_command, run_operator


@pytest.fixture
def fake_claude(tmp_path: Path, monkeypatch) -> Path:
    """A `claude` on PATH, so the default Operator counts as installed."""
    binary = tmp_path / "bin" / "claude"
    binary.parent.mkdir()
    binary.write_text("#!/bin/sh\nexit 0\n")
    binary.chmod(binary.stat().st_mode | stat.S_IXUSR)
    monkeypatch.setenv("PATH", f"{binary.parent}{os.pathsep}{os.environ['PATH']}")
    return binary


def test_missing_key_means_the_default_claude_command(workspace, fake_claude):
    workspace.config.pop("operator", None)
    argv = operator_command(workspace, "extract-posting", "2026-09-17-acme")
    assert argv[:2] == ["claude", "/extract-posting 2026-09-17-acme"]
    assert "--add-dir" in argv
    tool = Path(argv[argv.index("--add-dir") + 1])
    assert (tool / ".agents" / "skills" / "extract-posting" / "SKILL.md").exists()
    assert argv[argv.index("--allowedTools") + 1] == "Bash,Read,Write,Edit"


def test_empty_key_or_absent_program_disables_the_operator(workspace, fake_claude):
    workspace.config["operator"] = ""
    assert operator_command(workspace, "extract-posting", "acme") is None
    workspace.config["operator"] = 'no-such-program-xyz "/{skill} {slug}"'
    assert operator_command(workspace, "extract-posting", "acme") is None


def test_run_operator_starts_it_in_the_workspace_with_the_workspace_exported(application, fake_claude):
    calls = []

    def runner(argv, cwd, env):
        calls.append((argv, cwd, env))
        return 3

    code = run_operator(application, "extract-posting", runner=runner)
    assert code == 3
    (argv, cwd, env), = calls
    assert argv[1] == f"/extract-posting {application.slug}"
    assert Path(cwd) == application.workspace.root
    assert env["JOBAPPLY_WORKSPACE"] == str(application.workspace.root)
    assert env["PATH"] == os.environ["PATH"]
