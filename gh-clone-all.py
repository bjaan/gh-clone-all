#!/usr/bin/env python3
"""gh-clone-all — clone every repository of a GitHub user or org.

Usage:
  gh-clone-all <owner> [--dest DIR] [--pattern GLOB] [--include-forks]
               [--ssh] [--token TOKEN] [--workers N] [--list-only]

Examples:
  gh-clone-all storytold
  gh-clone-all storytold --dest ~/repos/storytold
  gh-clone-all storytold --pattern '*craft*' --workers 4
  gh-clone-all me --token $GITHUB_TOKEN --include-forks

Lists all public repos of the owner (or your own repos if a token is
provided and owner matches), paginating the GitHub API, then clones
each with git. Existing directories are skipped (idempotent re-runs).
"""
import argparse
import fnmatch
import json
import os
import subprocess
import sys
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed

API = "https://api.github.com"


def api_get(url, token=None):
    req = urllib.request.Request(
        url,
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": "gh-clone-all",
        },
    )
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def list_repos(owner, token=None):
    repos, page = [], 1
    while True:
        url = f"{API}/users/{owner}/repos?per_page=100&page={page}&type=all"
        try:
            batch = api_get(url, token)
        except urllib.error.HTTPError as e:
            if e.code in (403, 429):
                sys.exit(
                    f"GitHub rate limit hit (HTTP {e.code}). "
                    "Pass --token or set GITHUB_TOKEN."
                )
            if e.code == 404:
                sys.exit(f"Owner '{owner}' not found.")
            raise
        if not isinstance(batch, list):
            sys.exit(f"Unexpected API response: {batch}")
        repos.extend(batch)
        if len(batch) < 100:
            return repos
        page += 1


def clone(repo, dest, use_ssh, token):
    name = repo["name"]
    path = os.path.join(dest, name)
    if os.path.isdir(path):
        return name, "skipped (exists)"
    if use_ssh:
        url = repo["ssh_url"]
    else:
        url = repo["clone_url"]
        if token and repo.get("private"):
            url = url.replace("https://", f"https://x-access-token:{token}@")
    proc = subprocess.run(
        ["git", "clone", "--quiet", url, path],
        capture_output=True, text=True,
    )
    if proc.returncode != 0:
        return name, f"FAILED: {proc.stderr.strip().splitlines()[-1] if proc.stderr.strip() else 'git clone error'}"
    size = sum(
        os.path.getsize(os.path.join(dp, f))
        for dp, _, fs in os.walk(path) for f in fs
    ) / (1024 * 1024)
    return name, f"ok ({size:.1f} MB)"


def main():
    ap = argparse.ArgumentParser(description="Clone every repo of a GitHub user/org.")
    ap.add_argument("owner")
    ap.add_argument("--dest", default=None, help="Target dir (default: ./<owner>)")
    ap.add_argument("--pattern", default="*", help="Glob filter on repo names")
    ap.add_argument("--include-forks", action="store_true")
    ap.add_argument("--ssh", action="store_true", help="Clone via SSH instead of HTTPS")
    ap.add_argument("--token", default=os.environ.get("GITHUB_TOKEN"),
                    help="GitHub token (or GITHUB_TOKEN env) for rate limits/private repos")
    ap.add_argument("--workers", type=int, default=3, help="Parallel clones (default 3)")
    ap.add_argument("--list-only", action="store_true", help="Just list repo names")
    args = ap.parse_args()

    repos = list_repos(args.owner, args.token)
    repos = [r for r in repos if fnmatch.fnmatch(r["name"], args.pattern)]
    if not args.include_forks:
        repos = [r for r in repos if not r["fork"]]

    if args.list_only:
        for r in repos:
            print(f"{r['name']}\t{r['size']/1024:.1f} MB\t{'' if not r['fork'] else 'fork'}")
        print(f"-- {len(repos)} repos", file=sys.stderr)
        return

    dest = os.path.abspath(os.path.expanduser(args.dest or args.owner))
    os.makedirs(dest, exist_ok=True)
    total_kb = sum(r["size"] for r in repos)
    print(f"{len(repos)} repos, ~{total_kb/1024/1024:.2f} GB of history -> {dest}")

    ok = skipped = failed = 0
    with ThreadPoolExecutor(max_workers=args.workers) as ex:
        futs = {ex.submit(clone, r, dest, args.ssh, args.token): r["name"] for r in repos}
        for fut in as_completed(futs):
            name, status = fut.result()
            print(f"  [{status.split()[0]:>7}] {name}: {status}")
            if status.startswith("ok"):
                ok += 1
            elif status.startswith("skipped"):
                skipped += 1
            else:
                failed += 1
    print(f"\nDone: {ok} cloned, {skipped} skipped, {failed} failed. Dest: {dest}")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
