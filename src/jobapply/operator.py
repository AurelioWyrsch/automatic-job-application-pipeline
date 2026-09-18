"""The Operator: the external program `jobapply run` starts to complete a judgment file.

ADR 0001 keeps LLM calls out of the tool; the Operator is the pluggable program that
does that part — today a coding agent running the repo's skills, later perhaps a local
model. Which one is the Workspace's business (`operator` in `config.json`), the tool only
substitutes the placeholders and starts it (ADR 0004).
"""

from __future__ import annotations

import shlex
import shutil
from pathlib import Path

from .workspace import Workspace

# The prompt comes before `--allowedTools`: that flag is variadic and would swallow it.
DEFAULT_TEMPLATE = 'claude "/{skill} {slug}" --add-dir {tool} --allowedTools Bash,Read,Write,Edit'


def tool_dir() -> Path:
    """The directory holding `.agents/skills`: the repo checkout the package runs from."""
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / ".agents" / "skills").is_dir():
            return parent
    return here.parents[1]


def operator_command(workspace: Workspace, skill: str, slug: str) -> list[str] | None:
    """The argv that runs `skill` for the Application `slug`, or None when no Operator is set up.

    A missing `operator` key means the default; an empty one, or a program that is not
    on PATH, means the applicant works with their agent by hand.
    """
    template = workspace.config.get("operator", DEFAULT_TEMPLATE)
    if not template:
        return None
    command = template.format(skill=skill, slug=slug, tool=shlex.quote(str(tool_dir())))
    argv = shlex.split(command)
    if not argv or shutil.which(argv[0]) is None:
        return None
    return argv


def run_operator(app, skill: str, runner=None) -> int | None:
    """Start the Operator for `app` in the Workspace and wait for it; returns its exit code.

    None when no Operator is set up. The child inherits the environment plus
    JOBAPPLY_WORKSPACE, so `jobapply` commands inside the session hit the same Workspace.
    """
    import os
    import subprocess

    from .workspace import ENV_VAR

    argv = operator_command(app.workspace, skill, app.slug)
    if argv is None:
        return None
    env = {**os.environ, ENV_VAR: str(app.workspace.root)}
    if runner is None:
        runner = lambda argv, cwd, env: subprocess.call(argv, cwd=cwd, env=env)  # noqa: E731
    return runner(argv, str(app.workspace.root), env)
