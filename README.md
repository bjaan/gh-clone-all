# gh-clone-all

Clone every repository of a GitHub user or organization in one command.

Zero dependencies — Python 3 standard library only. No `gh` CLI, no `pygithub`. Just `git` and the GitHub REST API.

```bash
$ ./gh-clone-all.py storytold
60 repos, ~6.9 GB of history -> /tmp/storytold
  [      ok] artcraft: ok (1.3 GB)
  [      ok] winprint.rs: ok (0.2 MB)
  [ skipped] spark: skipped (exists)
  ...
Done: 60 cloned, 0 skipped, 0 failed. Dest: /tmp/storytold
```

## Features

- **One command, whole account** — paginates the GitHub API (`/users/<owner>/repos`) and clones everything
- **Parallel clones** — configurable worker pool (default 3)
- **Idempotent** — re-run any time; existing repos are skipped, so it doubles as a "catch up on new repos" command
- **Fork filtering** — forks excluded by default (usually you don't want 50 copies of someone else's project), `--include-forks` to keep them
- **Name filtering** — `--pattern '*craft*'` to grab a subset
- **Private repos & rate limits** — pass `--token` or set `GITHUB_TOKEN`; works for your own private repos too
- **HTTPS or SSH** — `--ssh` switches all clones to SSH remotes
- **Preview mode** — `--list-only` shows repo names and sizes before cloning anything
- **LFS-safe** — clones with plain `git clone`; if the account uses Git LFS, install `git-lfs` first so large-file checkouts don't fail

## Install

```bash
chmod +x gh-clone-all.py
sudo cp gh-clone-all.py /usr/local/bin/gh-clone-all   # optional: put it on your PATH
```

Requires Python 3.8+ and `git` on `PATH`. No third-party packages — see `requirements.txt`.

## Usage

```
gh-clone-all.py <owner> [--dest DIR] [--pattern GLOB] [--include-forks]
             [--ssh] [--token TOKEN] [--workers N] [--list-only]
```

| Flag | Description |
|---|---|
| `--dest DIR` | Target directory (default: `./<owner>`) |
| `--pattern GLOB` | Glob filter on repo names, e.g. `'*craft*'` |
| `--include-forks` | Include forked repositories |
| `--ssh` | Clone via SSH URLs instead of HTTPS |
| `--token TOKEN` | GitHub token for higher rate limits and private repos (or set `GITHUB_TOKEN`) |
| `--workers N` | Number of parallel clones (default 3) |
| `--list-only` | List repos with sizes, clone nothing |

### Examples

```bash
# Everything from an org into ./storytold
gh-clone-all storytold

# Only repos matching a pattern, into a custom directory
gh-clone-all storytold --pattern '*craft*' --dest ~/work/crafts

# Your own account, including private repos
GITHUB_TOKEN=*** gh-clone-all me --ssh

# Preview before committing to a 10 GB download
gh-clone-all someuser --list-only
```

## Notes

- Unauthenticated API requests are limited to 60/hour per IP; with a token you get 5,000/hour. Listing alone is a handful of requests — a token matters most for private repos.
- A personal access token with **no scopes** is enough for public data; for your private repos you need `repo` scope.
- Git LFS repositories (model weights, media) fail their checkout unless `git-lfs` is installed. The clone itself succeeds; fix afterwards with `git lfs install && git lfs checkout`.
- Exit code is non-zero if any clone failed — useful in CI / cron sync jobs.

## License

MIT
