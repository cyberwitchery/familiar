"""Command-line interface for familiar."""

from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import sys
import tempfile
import traceback
from pathlib import Path

from .agents import get_agents, get_agent
from .lint import lint_all
from .render import (
    NotFoundError,
    compose_system,
    list_items,
    list_snippets,
    render_invocation,
)

# exit codes
EXIT_SUCCESS = 0
EXIT_ERROR = 1  # general error (agent failed, etc.)
EXIT_USAGE = 2  # usage error (bad args, missing files, etc.)
_VALID_SKILL_NAME = re.compile(r"^[a-z0-9_-]+$")
_VALID_SUBAGENT_NAME = re.compile(r"^[a-z0-9_-]+$")


class CliError(Exception):
    """CLI error with optional hint."""

    def __init__(
        self, message: str, hint: str | None = None, exit_code: int = EXIT_USAGE
    ):
        super().__init__(message)
        self.hint = hint
        self.exit_code = exit_code


def find_repo_root(start: Path) -> Path:
    """Find the repository root by looking for .git directory.

    Walks up from start directory. Falls back to start directory itself
    if no .git is found, allowing use outside of git repositories.
    """
    cur = start.resolve()
    for p in [cur] + list(cur.parents):
        if (p / ".git").exists():
            return p
    return cur


def create_worktree(repo_root: Path) -> Path:
    """Create a temporary git worktree for the repository."""
    # Ensure it's a git repo
    try:
        subprocess.run(
            ["git", "-C", str(repo_root), "rev-parse", "--is-inside-work-tree"],
            check=True,
            capture_output=True,
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        raise CliError(
            "not a git repository", hint="--worktree requires a git repository"
        )

    tmpdir = tempfile.mkdtemp(prefix="familiar-")
    # git worktree add requires the directory to NOT exist.
    # mkdtemp creates it. Let's remove it and let git create it.
    os.rmdir(tmpdir)

    try:
        subprocess.run(
            [
                "git",
                "-C",
                str(repo_root),
                "worktree",
                "add",
                "--detach",
                tmpdir,
                "HEAD",
            ],
            check=True,
            capture_output=True,
        )
    except subprocess.CalledProcessError as e:
        raise CliError(f"failed to create git worktree: {e.stderr.decode().strip()}")

    return Path(tmpdir)


def write_instruction(repo_root: Path, agent_name: str, system: str) -> None:
    try:
        agent = get_agent(agent_name)
    except KeyError as e:
        raise CliError(str(e), hint=f"valid agents: {', '.join(get_agents().keys())}")
    (repo_root / agent.output_file).write_text(system.strip() + "\n", encoding="utf-8")


def write_skill(
    repo_root: Path, agent_name: str, invocation: str, skill_name: str, prompt: str
) -> Path:
    """Write a reusable skill file for supported agents."""
    if not _VALID_SKILL_NAME.match(skill_name):
        raise CliError(
            f"invalid skill name: {skill_name}",
            hint="use lowercase letters, numbers, underscore, or hyphen",
        )

    try:
        agent = get_agent(agent_name)
    except KeyError as e:
        raise CliError(str(e), hint=f"valid agents: {', '.join(get_agents().keys())}")

    if not agent.supports_skills():
        raise CliError(f"agent does not support skills: {agent_name}")

    skill_path = agent.skill_path(repo_root, skill_name)
    skill_path.parent.mkdir(parents=True, exist_ok=True)
    content = (
        f"# {skill_name}\n\n"
        "use this skill when this recurring task appears in this repository.\n\n"
        "## generated from\n\n"
        f"- invocation: {invocation}\n"
        f"- agent: {agent_name}\n\n"
        "## instructions\n\n"
        f"{prompt.strip()}\n"
    )
    skill_path.write_text(content, encoding="utf-8")
    return skill_path


def write_subagent(
    repo_root: Path,
    agent_name: str,
    conjurings: list[str],
    subagent_name: str,
    system: str,
) -> Path:
    """Write a reusable subagent file for supported agents."""
    if not _VALID_SUBAGENT_NAME.match(subagent_name):
        raise CliError(
            f"invalid subagent name: {subagent_name}",
            hint="use lowercase letters, numbers, underscore, or hyphen",
        )

    try:
        agent = get_agent(agent_name)
    except KeyError as e:
        raise CliError(str(e), hint=f"valid agents: {', '.join(get_agents().keys())}")

    if not agent.supports_subagents():
        raise CliError(f"agent does not support subagents: {agent_name}")

    subagent_path = agent.subagent_path(repo_root, subagent_name)
    subagent_path.parent.mkdir(parents=True, exist_ok=True)
    profile = ", ".join(conjurings)
    content = (
        f"# {subagent_name}\n\n"
        "use this subagent when this repository needs this persistent behavior profile.\n\n"
        "## generated from\n\n"
        f"- conjurings: {profile}\n"
        f"- agent: {agent_name}\n\n"
        "## instructions\n\n"
        f"{system.strip()}\n"
    )
    subagent_path.write_text(content, encoding="utf-8")
    return subagent_path


def parse_kv(pairs: list[str]) -> dict[str, str]:
    out: dict[str, str] = {}
    for p in pairs:
        if "=" not in p:
            raise CliError(
                f"invalid argument: {p}",
                hint="use key=value format, e.g. --kv name=myproject",
            )
        k, v = p.split("=", 1)
        out[k.strip()] = v.strip()
    return out


def run_agent(
    repo_root: Path, agent_name: str, prompt: str, headless: bool, auto: bool = False
) -> int:
    try:
        agent = get_agent(agent_name)
    except KeyError as e:
        raise CliError(str(e), hint=f"valid agents: {', '.join(get_agents().keys())}")
    try:
        return agent.run(repo_root, prompt, headless, auto=auto)
    except FileNotFoundError:
        raise CliError(
            f"{agent_name} not found in PATH",
            hint=f"install {agent_name} or check your PATH environment variable",
        )


def cmd_conjure(args: argparse.Namespace) -> int:
    repo_root = find_repo_root(Path(args.into or os.getcwd()))
    try:
        system = compose_system(repo_root, args.conjurings)
    except NotFoundError as e:
        raise CliError(
            str(e),
            hint="run 'familiar list conjurings' to see available options",
        )
    write_instruction(repo_root, args.agent, system)
    if getattr(args, "save_subagent", False):
        subagent_name = getattr(args, "subagent_name", None) or "_".join(
            args.conjurings
        )
        subagent_path = write_subagent(
            repo_root, args.agent, args.conjurings, subagent_name, system
        )
        print(f"wrote subagent: {subagent_path}")
    print(f"wrote instructions for {args.agent}")
    return EXIT_SUCCESS


def cmd_invoke(args: argparse.Namespace) -> int:
    repo_root = find_repo_root(Path(args.into or os.getcwd()))
    kv = parse_kv(args.kv or [])
    try:
        prompt = render_invocation(repo_root, args.invocation, args.inv_args or [], kv)
    except NotFoundError as e:
        raise CliError(
            str(e),
            hint="run 'familiar list invocations' to see available options",
        )

    if args.dry_run:
        print(prompt)
        return EXIT_SUCCESS

    if getattr(args, "save_skill", False):
        skill_name = getattr(args, "skill_name", None) or args.invocation
        skill_path = write_skill(
            repo_root, args.agent, args.invocation, skill_name, prompt
        )
        print(f"wrote skill: {skill_path}")
        return EXIT_SUCCESS

    target_dir = repo_root
    if args.worktree:
        target_dir = create_worktree(repo_root)
        print(f"created worktree at {target_dir}")

        # Best-effort copy of instruction file into the worktree
        try:
            agent = get_agent(args.agent)
            instr_file = repo_root / agent.output_file
            if instr_file.exists():
                shutil.copy2(instr_file, target_dir / agent.output_file)
        except (OSError, KeyError):
            pass

    try:
        rc = run_agent(
            target_dir, args.agent, prompt, headless=args.headless, auto=args.auto
        )
        if args.worktree:
            print(f"\nworktree remains at: {target_dir}")
            print(f"to remove it: git worktree remove {target_dir}")
        return rc
    except Exception:
        if args.worktree:
            print(f"\nworktree remains at: {target_dir}")
        raise


def _print_items(
    items: list[tuple[str, str, bool]], verbose: bool, indent: str = ""
) -> None:
    for name, first_line, is_local in items:
        marker = " (local)" if is_local else ""
        if verbose:
            print(f"{indent}{name}{marker}: {first_line}")
        else:
            print(f"{indent}{name}{marker}")


def cmd_list(args: argparse.Namespace) -> int:
    repo_root = find_repo_root(Path(args.into or os.getcwd()))

    if args.kind is None:
        # list all
        conjurings = list_items(repo_root, "conjurings")
        invocations = list_items(repo_root, "invocations")
        snippets = list_snippets(repo_root)
        print("conjurings:")
        _print_items(conjurings, args.verbose, indent="  ")
        print("\ninvocations:")
        _print_items(invocations, args.verbose, indent="  ")
        if snippets:
            print("\nsnippets:")
            _print_items(snippets, args.verbose, indent="  ")
        return EXIT_SUCCESS

    if args.kind == "snippets":
        items = list_snippets(repo_root)
    else:
        items = list_items(repo_root, args.kind)

    if not items:
        print(f"no {args.kind} found")
        return EXIT_SUCCESS

    _print_items(items, args.verbose)
    return EXIT_SUCCESS


def cmd_lint(args: argparse.Namespace) -> int:
    repo_root = find_repo_root(Path(args.into or os.getcwd()))

    messages = lint_all(repo_root)

    # Filter by level if requested
    if args.errors_only:
        messages = [m for m in messages if m.level == "error"]

    if not messages:
        print("all checks passed")
        return EXIT_SUCCESS

    # Group by level for output
    errors = [m for m in messages if m.level == "error"]
    warnings = [m for m in messages if m.level == "warning"]

    for msg in errors:
        print(msg, file=sys.stderr)
    for msg in warnings:
        print(msg, file=sys.stderr)

    if errors:
        print(f"\n{len(errors)} error(s), {len(warnings)} warning(s)", file=sys.stderr)
        return EXIT_ERROR

    print(f"\n{len(warnings)} warning(s)", file=sys.stderr)
    return EXIT_SUCCESS


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="familiar",
        description="conjure and invoke familiars",
        epilog="examples:\n"
        "  familiar conjure codex rust sec      # create AGENTS.md\n"
        "  familiar invoke codex bootstrap-rust # run invocation\n"
        "  familiar list                        # show all options\n"
        "  familiar lint                        # validate prompts\n",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--debug", action="store_true", help="show full traceback on error"
    )
    sub = parser.add_subparsers(dest="command", required=True)

    agent_choices = list(get_agents().keys())

    conjure = sub.add_parser(
        "conjure",
        help="compose system instructions for an agent",
        epilog="example: familiar conjure codex rust infra sec",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    conjure.add_argument("agent", choices=agent_choices)
    conjure.add_argument(
        "conjurings", nargs="+", help="conjuring names, e.g. rust infra sec"
    )
    conjure.add_argument("--into", help="target repo path (default: current directory)")
    conjure.add_argument(
        "--save-subagent",
        action="store_true",
        help="write composed conjurings as a reusable subagent",
    )
    conjure.add_argument(
        "--subagent-name",
        help="override subagent name (default: joined conjuring names)",
    )
    conjure.set_defaults(func=cmd_conjure)

    invoke = sub.add_parser(
        "invoke",
        help="render an invocation and run the agent",
        epilog="example: familiar invoke codex bootstrap-rust myapp bin 1.78 mit",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    invoke.add_argument("agent", choices=agent_choices)
    invoke.add_argument("invocation")
    invoke.add_argument("--into", help="target repo path (default: current directory)")
    invoke.add_argument(
        "--headless", action="store_true", help="run without interactive UI"
    )
    invoke.add_argument(
        "--auto", action="store_true", help="skip agent permission prompts"
    )
    invoke.add_argument(
        "--dry-run", action="store_true", help="print rendered prompt and exit"
    )
    invoke.add_argument(
        "--worktree", action="store_true", help="run in a separate git worktree"
    )
    invoke.add_argument(
        "--save-skill",
        action="store_true",
        help="write rendered invocation as a skill and exit",
    )
    invoke.add_argument(
        "--skill-name",
        help="override skill name (default: invocation name)",
    )
    invoke.add_argument("--kv", nargs="*", help="named arguments as key=value pairs")
    invoke.add_argument(
        "inv_args", nargs="*", help="positional arguments for the invocation"
    )
    invoke.set_defaults(func=cmd_invoke)

    list_cmd = sub.add_parser(
        "list",
        help="list available conjurings and invocations",
        epilog="example: familiar list conjurings -v",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    list_cmd.add_argument(
        "kind",
        nargs="?",
        choices=["conjurings", "invocations", "snippets"],
        help="what to list (default: all)",
    )
    list_cmd.add_argument(
        "--into", help="target repo path (default: current directory)"
    )
    list_cmd.add_argument(
        "-v", "--verbose", action="store_true", help="show first line of each file"
    )
    list_cmd.set_defaults(func=cmd_list)

    lint_cmd = sub.add_parser(
        "lint",
        help="lint conjurings and invocations",
        epilog="example: familiar lint --errors-only",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    lint_cmd.add_argument(
        "--into", help="target repo path (default: current directory)"
    )
    lint_cmd.add_argument(
        "--errors-only", action="store_true", help="show only errors, not warnings"
    )
    lint_cmd.set_defaults(func=cmd_lint)

    args = parser.parse_args()

    try:
        rc = args.func(args)
    except CliError as e:
        if args.debug:
            traceback.print_exc()
        print(f"error: {e}", file=sys.stderr)
        if e.hint:
            print(f"hint: {e.hint}", file=sys.stderr)
        raise SystemExit(e.exit_code)
    except Exception as e:
        if args.debug:
            traceback.print_exc()
        print(f"error: {e}", file=sys.stderr)
        raise SystemExit(EXIT_ERROR)

    raise SystemExit(rc)


if __name__ == "__main__":
    main()
