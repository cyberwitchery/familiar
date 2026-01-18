"""Command-line interface for familiar."""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

from .agents import AGENTS, get_agent
from .render import compose, list_items, NotFoundError


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
        cfg: dict[str, Any] = json.loads(p.read_text(encoding="utf-8"))
        return cfg
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
            raise SystemExit(f"expected key=value, got: {p}")
        k, v = p.split('=', 1)
        out[k.strip()] = v.strip()
    return out


def run_agent(repo_root: Path, agent_name: str, prompt: str, headless: bool) -> int:
    agent = get_agent(agent_name)
    try:
        return agent.run(repo_root, prompt, headless)
    except FileNotFoundError:
        raise SystemExit(f"{agent_name} not found in PATH")


def cmd_conjure(args: argparse.Namespace) -> int:
    repo_root = find_repo_root(Path(args.into or os.getcwd()))
    try:
        system, _, _ = compose(repo_root, args.conjurings, invocation="__noop__", args=[], kv={})
    except NotFoundError as e:
        raise SystemExit(str(e))
    write_instruction(repo_root, args.agent, system)
    save_config(repo_root, args.agent, {"conjurings": args.conjurings})
    print(f"wrote instructions for {args.agent}")
    return 0


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
        raise SystemExit(str(e))
    return run_agent(repo_root, args.agent, full, headless=args.headless)


def _print_items(items: list[tuple[str, str, bool]], verbose: bool) -> None:
    for name, first_line, is_local in items:
        marker = " (local)" if is_local else ""
        if verbose:
            print(f"  {name}{marker}: {first_line}")
        else:
            print(f"  {name}{marker}")


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
        return 0

    for name, first_line, is_local in items:
        marker = " (local)" if is_local else ""
        if args.verbose:
            print(f"{name}{marker}: {first_line}")
        else:
            print(f"{name}{marker}")
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(prog="familiar", description="conjure and invoke familiars")
    sub = parser.add_subparsers(dest="command", required=True)

    agent_choices = list(AGENTS.keys())

    conjure = sub.add_parser("conjure", help="compose system instructions for an agent")
    conjure.add_argument("agent", choices=agent_choices)
    conjure.add_argument("conjurings", nargs="+", help="conjuring names, e.g. rust infra sec")
    conjure.add_argument("--into", help="target repo path (default: current directory)")
    conjure.set_defaults(func=cmd_conjure)

    invoke = sub.add_parser("invoke", help="render an invocation and run the agent")
    invoke.add_argument("agent", choices=agent_choices)
    invoke.add_argument("invocation")
    invoke.add_argument("--into", help="target repo path (default: current directory)")
    invoke.add_argument("--headless", action="store_true", help="run without interactive UI")
    invoke.add_argument("--conjurings", nargs="*", default=None, help="override saved conjurings")
    invoke.add_argument("--kv", nargs="*", help="named arguments as key=value pairs")
    invoke.add_argument("inv_args", nargs="*", help="positional arguments for the invocation")
    invoke.set_defaults(func=cmd_invoke)

    list_cmd = sub.add_parser("list", help="list available conjurings and invocations")
    list_cmd.add_argument("kind", nargs="?", choices=["conjurings", "invocations"], help="what to list (default: both)")
    list_cmd.add_argument("--into", help="target repo path (default: current directory)")
    list_cmd.add_argument("-v", "--verbose", action="store_true", help="show first line of each file")
    list_cmd.set_defaults(func=cmd_list)

    args = parser.parse_args()
    rc = args.func(args)
    raise SystemExit(rc)


if __name__ == "__main__":
    main()
