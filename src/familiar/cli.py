"""Command-line interface for familiar."""
from __future__ import annotations

import argparse
import json
import os
import sys
import traceback
from pathlib import Path
from typing import Any

from .agents import AGENTS, get_agent
from .render import compose, list_items, NotFoundError

# exit codes
EXIT_SUCCESS = 0
EXIT_ERROR = 1      # general error (agent failed, etc.)
EXIT_USAGE = 2      # usage error (bad args, missing files, etc.)


class CliError(Exception):
    """CLI error with optional hint."""

    def __init__(self, message: str, hint: str | None = None, exit_code: int = EXIT_USAGE):
        super().__init__(message)
        self.hint = hint
        self.exit_code = exit_code


def find_repo_root(start: Path) -> Path:
    cur = start.resolve()
    for p in [cur] + list(cur.parents):
        if (p / ".git").exists():
            return p
    return cur


def ensure_fam_dir(repo_root: Path) -> Path:
    d = repo_root / ".familiar"
    d.mkdir(parents=True, exist_ok=True)
    return d


def config_path(repo_root: Path, agent_name: str) -> Path:
    return ensure_fam_dir(repo_root) / f"{agent_name}.json"


def load_config(repo_root: Path, agent_name: str) -> dict[str, Any]:
    p = config_path(repo_root, agent_name)
    if p.exists():
        try:
            cfg: dict[str, Any] = json.loads(p.read_text(encoding="utf-8"))
            return cfg
        except json.JSONDecodeError as e:
            raise CliError(
                f"malformed config: {p}",
                hint=f"fix the json syntax error at line {e.lineno}, or delete the file to reset",
            )
    return {}


def save_config(repo_root: Path, agent_name: str, cfg: dict[str, Any]) -> None:
    p = config_path(repo_root, agent_name)
    p.write_text(json.dumps(cfg, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_instruction(repo_root: Path, agent_name: str, system: str) -> None:
    agent = get_agent(agent_name)
    (repo_root / agent.output_file).write_text(system.strip() + "\n", encoding="utf-8")


def parse_kv(pairs: list[str]) -> dict[str, str]:
    out: dict[str, str] = {}
    for p in pairs:
        if '=' not in p:
            raise CliError(
                f"invalid argument: {p}",
                hint="use key=value format, e.g. --kv name=myproject",
            )
        k, v = p.split('=', 1)
        out[k.strip()] = v.strip()
    return out


def run_agent(repo_root: Path, agent_name: str, prompt: str, headless: bool) -> int:
    agent = get_agent(agent_name)
    try:
        return agent.run(repo_root, prompt, headless)
    except FileNotFoundError:
        raise CliError(
            f"{agent_name} not found in PATH",
            hint=f"install {agent_name} or check your PATH environment variable",
        )


def cmd_conjure(args: argparse.Namespace) -> int:
    repo_root = find_repo_root(Path(args.into or os.getcwd()))
    try:
        system, _, _ = compose(repo_root, args.conjurings, invocation="__noop__", args=[], kv={})
    except NotFoundError as e:
        raise CliError(
            str(e),
            hint="run 'familiar list conjurings' to see available options",
        )
    write_instruction(repo_root, args.agent, system)
    save_config(repo_root, args.agent, {"conjurings": args.conjurings})
    print(f"wrote instructions for {args.agent}")
    return EXIT_SUCCESS


def cmd_invoke(args: argparse.Namespace) -> int:
    repo_root = find_repo_root(Path(args.into or os.getcwd()))
    cfg = load_config(repo_root, args.agent)
    conjurings = args.conjurings if args.conjurings is not None else cfg.get("conjurings", [])
    if not conjurings:
        print("warning: no conjurings specified, using core only", file=sys.stderr)
    kv = parse_kv(args.kv or [])
    try:
        _, _, full = compose(repo_root, conjurings, args.invocation, args.inv_args or [], kv)
    except NotFoundError as e:
        hint = "run 'familiar list' to see available options"
        if "invocation" in str(e):
            hint = "run 'familiar list invocations' to see available options"
        elif "template" in str(e):
            hint = "run 'familiar list conjurings' to see available options"
        raise CliError(str(e), hint=hint)
    return run_agent(repo_root, args.agent, full, headless=args.headless)


def _print_items(items: list[tuple[str, str, bool]], verbose: bool) -> None:
    for name, first_line, is_local in items:
        marker = " (local)" if is_local else ""
        if verbose:
            print(f"  {name}{marker}: {first_line}")
        else:
            print(f"  {name}{marker}")


def cmd_conjurings_show(args: argparse.Namespace) -> int:
    repo_root = find_repo_root(Path(args.into or os.getcwd()))
    cfg = load_config(repo_root, args.agent)
    conjurings = cfg.get("conjurings", [])
    if not conjurings:
        print(f"no conjurings saved for {args.agent}")
    else:
        for name in conjurings:
            print(name)
    return EXIT_SUCCESS


def cmd_conjurings_set(args: argparse.Namespace) -> int:
    repo_root = find_repo_root(Path(args.into or os.getcwd()))
    # validate that all conjurings exist
    for name in args.conjurings:
        try:
            from .render import load_text
            load_text(repo_root, "templates", name)
        except NotFoundError:
            raise CliError(
                f"unknown conjuring: {name}",
                hint="run 'familiar list conjurings' to see available options",
            )
    save_config(repo_root, args.agent, {"conjurings": args.conjurings})
    print(f"saved conjurings for {args.agent}: {' '.join(args.conjurings)}")
    return EXIT_SUCCESS


def cmd_conjurings_reset(args: argparse.Namespace) -> int:
    repo_root = find_repo_root(Path(args.into or os.getcwd()))
    p = config_path(repo_root, args.agent)
    if p.exists():
        p.unlink()
        print(f"reset conjurings for {args.agent}")
    else:
        print(f"no conjurings saved for {args.agent}")
    return EXIT_SUCCESS


def cmd_list(args: argparse.Namespace) -> int:
    repo_root = find_repo_root(Path(args.into or os.getcwd()))

    if args.kind is None:
        # list both
        conjurings = list_items(repo_root, "templates")
        invocations = list_items(repo_root, "invocations")
        print("conjurings:")
        _print_items(conjurings, args.verbose)
        print("\ninvocations:")
        _print_items(invocations, args.verbose)
        return 0

    # map CLI names to internal names
    kind = "templates" if args.kind == "conjurings" else args.kind
    items = list_items(repo_root, kind)

    if not items:
        print(f"no {kind} found")
        return EXIT_SUCCESS

    for name, first_line, is_local in items:
        marker = " (local)" if is_local else ""
        if args.verbose:
            print(f"{name}{marker}: {first_line}")
        else:
            print(f"{name}{marker}")
    return EXIT_SUCCESS


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="familiar",
        description="conjure and invoke familiars",
        epilog="examples:\n"
               "  familiar conjure codex rust sec      # create AGENTS.md\n"
               "  familiar invoke codex bootstrap-rust # run invocation\n"
               "  familiar list                        # show all options\n",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--debug", action="store_true", help="show full traceback on error")
    sub = parser.add_subparsers(dest="command", required=True)

    agent_choices = list(AGENTS.keys())

    conjure = sub.add_parser(
        "conjure",
        help="compose system instructions for an agent",
        epilog="example: familiar conjure codex rust infra sec",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    conjure.add_argument("agent", choices=agent_choices)
    conjure.add_argument("conjurings", nargs="+", help="conjuring names, e.g. rust infra sec")
    conjure.add_argument("--into", help="target repo path (default: current directory)")
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
    invoke.add_argument("--headless", action="store_true", help="run without interactive UI")
    invoke.add_argument("--conjurings", nargs="*", default=None, help="override saved conjurings")
    invoke.add_argument("--kv", nargs="*", help="named arguments as key=value pairs")
    invoke.add_argument("inv_args", nargs="*", help="positional arguments for the invocation")
    invoke.set_defaults(func=cmd_invoke)

    list_cmd = sub.add_parser(
        "list",
        help="list available conjurings and invocations",
        epilog="example: familiar list conjurings -v",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    list_cmd.add_argument("kind", nargs="?", choices=["conjurings", "invocations"], help="what to list (default: both)")
    list_cmd.add_argument("--into", help="target repo path (default: current directory)")
    list_cmd.add_argument("-v", "--verbose", action="store_true", help="show first line of each file")
    list_cmd.set_defaults(func=cmd_list)

    # conjurings subcommand with show/set/reset
    conjurings_cmd = sub.add_parser(
        "conjurings",
        help="manage saved conjurings for an agent",
        epilog="examples:\n"
               "  familiar conjurings show claude\n"
               "  familiar conjurings set codex rust sec\n"
               "  familiar conjurings reset claude\n",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    conjurings_sub = conjurings_cmd.add_subparsers(dest="action", required=True)

    conj_show = conjurings_sub.add_parser("show", help="show saved conjurings")
    conj_show.add_argument("agent", choices=agent_choices)
    conj_show.add_argument("--into", help="target repo path (default: current directory)")
    conj_show.set_defaults(func=cmd_conjurings_show)

    conj_set = conjurings_sub.add_parser("set", help="set conjurings for an agent")
    conj_set.add_argument("agent", choices=agent_choices)
    conj_set.add_argument("conjurings", nargs="+", help="conjuring names")
    conj_set.add_argument("--into", help="target repo path (default: current directory)")
    conj_set.set_defaults(func=cmd_conjurings_set)

    conj_reset = conjurings_sub.add_parser("reset", help="reset saved conjurings")
    conj_reset.add_argument("agent", choices=agent_choices)
    conj_reset.add_argument("--into", help="target repo path (default: current directory)")
    conj_reset.set_defaults(func=cmd_conjurings_reset)

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
