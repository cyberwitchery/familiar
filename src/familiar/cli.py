"""Command-line interface for familiar."""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

from .agents import AGENTS, get_agent
from .render import compose, NotFoundError


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
        system, _, _ = compose(repo_root, args.profiles, invocation="__noop__", args=[], kv={})
    except NotFoundError as e:
        raise SystemExit(str(e))
    write_instruction(repo_root, args.agent, system)
    save_config(repo_root, args.agent, {"profiles": args.profiles})
    print(f"wrote instructions for {args.agent}")
    return 0


def cmd_invoke(args: argparse.Namespace) -> int:
    repo_root = find_repo_root(Path(args.into or os.getcwd()))
    cfg = load_config(repo_root, args.agent)
    profiles = args.profiles if args.profiles is not None else cfg.get("profiles", [])
    if not profiles:
        print("warning: no profiles specified, using core only", file=sys.stderr)
    kv = parse_kv(args.kv or [])
    try:
        _, _, full = compose(repo_root, profiles, args.invocation, args.inv_args or [], kv)
    except NotFoundError as e:
        raise SystemExit(str(e))
    return run_agent(repo_root, args.agent, full, headless=args.headless)


def main() -> None:
    parser = argparse.ArgumentParser(prog="familiar", description="conjure and invoke familiars")
    sub = parser.add_subparsers(dest="command", required=True)

    agent_choices = list(AGENTS.keys())

    conjure = sub.add_parser("conjure", help="compose system instructions for an agent")
    conjure.add_argument("agent", choices=agent_choices)
    conjure.add_argument("profiles", nargs="+", help="profile names, e.g. rust infra sec")
    conjure.add_argument("--into", help="target repo path (default: current directory)")
    conjure.set_defaults(func=cmd_conjure)

    invoke = sub.add_parser("invoke", help="render an invocation and run the agent")
    invoke.add_argument("agent", choices=agent_choices)
    invoke.add_argument("invocation")
    invoke.add_argument("--into", help="target repo path (default: current directory)")
    invoke.add_argument("--headless", action="store_true", help="run without interactive UI")
    invoke.add_argument("--profiles", nargs="*", default=None, help="override saved profiles")
    invoke.add_argument("--kv", nargs="*", help="named arguments as key=value pairs")
    invoke.add_argument("inv_args", nargs="*", help="positional arguments for the invocation")
    invoke.set_defaults(func=cmd_invoke)

    args = parser.parse_args()
    rc = args.func(args)
    raise SystemExit(rc)


if __name__ == "__main__":
    main()
