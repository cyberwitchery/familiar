#!/usr/bin/env python3
import argparse
import shutil
import sys
from pathlib import Path


OUTFILE = {
    "claude": "CLAUDE.md",
    "codex": "AGENTS.md",
}


def copy_tree(src: Path, dst: Path) -> None:
    if not src.exists():
        return
    for p in src.rglob("*"):
        rel = p.relative_to(src)
        if str(rel) == "header.md":
            continue
        target = dst / rel
        if p.is_dir():
            target.mkdir(parents=True, exist_ok=True)
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(p, target)
            print(f"copied {target}")


def read_md(p: Path) -> str:
    return p.read_text(encoding="utf-8").rstrip() + "\n"


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(prog="summon.py", description="summon casts familiars")
    ap.add_argument("agent", choices=["claude", "codex"])
    ap.add_argument("profiles_csv", help="comma-separated, e.g. infra,sec,rust")
    ap.add_argument("--into", default=".", help="target dir (default: .)")
    args = ap.parse_args(argv)

    here = Path(__file__).resolve().parent
    templates_dir = here / "templates"
    agent_dir = here / "agents" / args.agent
    target_dir = Path(args.into).resolve()

    profiles = [p.strip() for p in args.profiles_csv.split(",") if p.strip()]
    if not profiles:
        print("no profiles given", file=sys.stderr)
        return 2

    parts: list[str] = []

    header = agent_dir / "header.md"
    if header.exists():
        parts.append(read_md(header))

    core = templates_dir / "core.md"
    if core.exists():
        parts.append(read_md(core))

    for name in profiles:
        frag = templates_dir / f"{name}.md"
        if not frag.exists():
            print(f"missing template: {frag}", file=sys.stderr)
            return 2
        # simple separator so boundaries stay visible
        if parts:
            parts.append("\n---\n\n")
        parts.append(read_md(frag))

    outfile = target_dir / OUTFILE[args.agent]
    outfile.parent.mkdir(parents=True, exist_ok=True)
    outfile.write_text("".join(parts), encoding="utf-8")

    # copy agent-specific extra files (optional)
    copy_tree(agent_dir, target_dir)

    print(f"wrote {outfile}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
