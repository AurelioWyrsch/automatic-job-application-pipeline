"""The Operator: the external program `jobapply run` starts to complete a judgment file.

ADR 0001 keeps LLM calls out of the tool; the Operator is the pluggable program that
does that part — today a coding agent running the repo's skills, later perhaps a local
model. Which one is the Workspace's business (`operator` and `operator_unattended` in
`config.json`), the tool only substitutes the placeholders and starts it (ADR 0004).

Two modes: **interactive** (the letter interview, in the applicant's terminal) and
**unattended** (`claude -p …`: extraction and field mapping, output only).
"""

from __future__ import annotations

import os
import shlex
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Callable

from .workspace import ENV_VAR, Workspace

# The prompt comes before `--allowedTools`: that flag is variadic and would swallow it.
DEFAULT_TEMPLATE = 'claude "/{skill} {slug}" --add-dir {tool} --allowedTools Bash,Read,Write,Edit'
DEFAULT_UNATTENDED_TEMPLATE = 'claude -p "/{skill} {slug}" --add-dir {tool} --allowedTools Bash,Read,Write,Edit'

CONFIG_KEYS = {False: ("operator", DEFAULT_TEMPLATE), True: ("operator_unattended", DEFAULT_UNATTENDED_TEMPLATE)}

Runner = Callable[[list[str], str, dict[str, str]], int]
CapturingRunner = Callable[[list[str], str, dict[str, str]], tuple[int, str]]


def tool_dir() -> Path:
    """The directory holding `.agents/skills`: the repo checkout the package runs from."""
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / ".agents" / "skills").is_dir():
            return parent
    return here.parents[1]


def operator_command(workspace: Workspace, skill: str, slug: str, *, unattended: bool = False) -> list[str] | None:
    """The argv that runs `skill` for the Application `slug`, or None when that mode is not set up.

    A missing key means the default; an empty one, or a program that is not on PATH,
    means the applicant works with their agent by hand.
    """
    key, default = CONFIG_KEYS[unattended]
    template = workspace.config.get(key, default)
    if not template:
        return None
    command = template.format(skill=skill, slug=slug, tool=shlex.quote(str(tool_dir())))
    argv = shlex.split(command)
    if not argv or shutil.which(argv[0]) is None:
        return None
    return argv


# Everything an Operator session switches on and a killed one leaves behind: mouse tracking
# (1000/1002/1003, SGR 1006), focus reporting (1004), bracketed paste (2004), the kitty
# keyboard stack (`CSI < n u` pops n entries) and xterm's modifyOtherKeys. The next program
# then reads "^[[<35;39;10M", "^[[O" or "^[[99;5u" as typed text (anthropics/claude-code#84029,
# #76816). Unknown sequences are ignored by terminals that lack the feature. Not in the list:
# leaving the alternate screen (`?1049l`) — on a terminal already on the normal screen it
# still "restores the cursor" to a stale position and the next lines overwrite old ones;
# Claude Code renders inline and never enters it.
TERMINAL_RESET = ("\x1b[?1000l\x1b[?1002l\x1b[?1003l\x1b[?1006l\x1b[?1004l\x1b[?2004l"
                  "\x1b[<99u\x1b[>4;0m\x1b[?25h\x1b[0m")
MOUSE_OFF = TERMINAL_RESET  # kept for callers of the earlier name


def reset_terminal(stream=None) -> None:
    """Put the terminal back into its plain state, when there is one (see TERMINAL_RESET)."""
    stream = stream or sys.stdout
    try:
        if not stream.isatty():
            return
        stream.write(TERMINAL_RESET)
        stream.flush()
    except (AttributeError, OSError, ValueError):
        pass


def _env(app) -> dict[str, str]:
    """The child inherits the environment plus JOBAPPLY_WORKSPACE, so `jobapply` commands
    inside the session hit the same Workspace."""
    return {**os.environ, ENV_VAR: str(app.workspace.root)}


def run_operator(app, skill: str, runner: Runner | None = None) -> int | None:
    """Start the interactive Operator for `app` in the Workspace and wait for it; returns
    its exit code, or None when no Operator is set up."""
    argv = operator_command(app.workspace, skill, app.slug)
    if argv is None:
        return None
    if runner is None:
        runner = lambda argv, cwd, env: subprocess.call(argv, cwd=cwd, env=env)  # noqa: E731
    reset_terminal()
    try:
        return runner(argv, str(app.workspace.root), _env(app))
    finally:
        reset_terminal()


def run_unattended(app, skill: str, *, capture: bool = False,
                   runner: CapturingRunner | None = None) -> tuple[int, str] | None:
    """Run `skill` with the unattended Operator; returns (exit code, captured output) or None
    when that mode is not set up. Without `capture` the output goes straight to the terminal
    and the returned text is empty."""
    argv = operator_command(app.workspace, skill, app.slug, unattended=True)
    if argv is None:
        return None
    if runner is None:
        def runner(argv, cwd, env):
            if capture:
                proc = subprocess.run(argv, cwd=cwd, env=env, stdin=subprocess.DEVNULL,
                                      stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
                return proc.returncode, proc.stdout
            return subprocess.call(argv, cwd=cwd, env=env, stdin=subprocess.DEVNULL), ""
    if capture:
        return runner(argv, str(app.workspace.root), _env(app))
    reset_terminal()
    try:
        return runner(argv, str(app.workspace.root), _env(app))
    finally:
        reset_terminal()
