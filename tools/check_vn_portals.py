#!/usr/bin/env python3
"""Watch the Vietnam-portal fork for new or fixed job-portal skills.

Usage:
  python tools/check_vn_portals.py            # fetch + report what is new since the last --ack
  python tools/check_vn_portals.py --ack      # same, then mark everything as reviewed
  python tools/check_vn_portals.py --remote vn-fork --branch master

What it does (report-only; it NEVER merges, copies files, or edits portal code):
1. Adds the `vn-fork` remote (https://github.com/jamesng16/ai-job-search-vn) if missing and fetches it.
2. Lists commits on the remote branch that were not yet acknowledged, with the portal
   skill folders under `.agents/skills/` each one touches.
3. Lists portal skills (`.agents/skills/*-search`) that exist on the remote but not locally.
4. For portal skills present on both sides, says whether the remote copy differs from local.

The last reviewed commit is kept in `.git/vn_upstream_state.json` (inside .git, never committed).
Port anything worth keeping by hand: a portal that works upstream can still break the
contract here (robots.txt rules, the zero-dependency default, the allowlists in
`.claude/settings.json` and `tools/security_guards.py`).
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REMOTE_URL = "https://github.com/jamesng16/ai-job-search-vn.git"
SKILLS = ".agents/skills"
STATE = ROOT / ".git" / "vn_upstream_state.json"


def git(*args: str, check: bool = False) -> tuple[int, str]:
    res = subprocess.run(
        ["git", *args], cwd=str(ROOT), capture_output=True, text=True,
        encoding="utf-8", errors="replace",
    )
    if check and res.returncode != 0:
        raise SystemExit(f"git {' '.join(args)} failed: {res.stderr.strip()}")
    return res.returncode, res.stdout


def portal_dirs(ref: str | None) -> set[str]:
    """Names of `*-search` skill folders, from a git ref or from the working tree."""
    if ref is None:
        base = ROOT / SKILLS
        return {p.name for p in base.glob("*-search") if p.is_dir()} if base.exists() else set()
    rc, out = git("ls-tree", "--name-only", f"{ref}:{SKILLS}/")
    if rc != 0:
        return set()
    return {n.strip().rstrip("/") for n in out.splitlines() if n.strip().endswith("-search")}


def load_state() -> dict:
    try:
        return json.loads(STATE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def main() -> int:
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure:
            reconfigure(encoding="utf-8")

    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--remote", default="vn-fork")
    ap.add_argument("--branch", default="master")
    ap.add_argument("--ack", action="store_true", help="mark the fetched head as reviewed")
    args = ap.parse_args()

    rc, url = git("remote", "get-url", args.remote)
    if rc != 0:
        git("remote", "add", args.remote, REMOTE_URL, check=True)
        print(f"added remote {args.remote} -> {REMOTE_URL}")
    rc, _ = git("fetch", "--quiet", args.remote, args.branch)
    if rc != 0:
        print(f"ERROR: could not fetch {args.remote}/{args.branch} (network or repo moved?)")
        return 2

    ref = f"{args.remote}/{args.branch}"
    _, head = git("rev-parse", ref)
    head = head.strip()
    state = load_state()
    last = state.get("last_reviewed")

    print(f"# Vietnam-portal watch: {ref} @ {head[:7]}")
    if last == head:
        print("No new commits since the last review.")
    else:
        rng = f"{last}..{ref}" if last else ref
        _, log = git("log", "--format=%H%x09%h%x09%ad%x09%s", "--date=short", rng)
        commits = [l.split("\t", 3) for l in log.splitlines() if l.strip()]
        print(f"\n{len(commits)} unreviewed commit(s):")
        for full, short, date, subject in commits:
            _, files = git("show", "--name-only", "--format=", full)
            touched = sorted({
                f.split("/")[2] for f in files.splitlines()
                if f.startswith(SKILLS + "/") and len(f.split("/")) > 3
            })
            portals = f"  [portals: {', '.join(touched)}]" if touched else ""
            print(f"- {short} {date} {subject}{portals}")

    remote_set, local_set = portal_dirs(ref), portal_dirs(None)
    new = sorted(remote_set - local_set)
    print("\nPortal skills on the remote but not installed locally:")
    print("\n".join(f"- {n}" for n in new) if new else "- (none)")

    # After the first review, "differs" means the REMOTE changed since then (our own local fixes
    # would otherwise keep every patched portal listed forever). Before it, compare to local.
    print("\nPortal skills on both sides whose remote copy changed:" if last else
          "\nPortal skills on both sides whose remote copy differs from local:")
    changed = []
    for name in sorted(remote_set & local_set):
        if last:
            rc, _ = git("diff", "--quiet", last, ref, "--", f"{SKILLS}/{name}")
        else:
            rc, _ = git("diff", "--quiet", ref, "--", f"{SKILLS}/{name}")
        if rc != 0:
            changed.append(name)
    shown = f"{last}..{ref}" if last else ref
    print("\n".join(f"- {n}   (git diff {shown} -- {SKILLS}/{n})" for n in changed) if changed else "- (none)")

    if args.ack:
        STATE.write_text(json.dumps({"last_reviewed": head, "remote": args.remote, "branch": args.branch}), encoding="utf-8")
        print(f"\nAcknowledged {head[:7]}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
