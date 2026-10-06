"""Pre-commit / pre-push safety guard.

Fails (exit 1) if anything that must never reach GitHub is about to be committed:
  * any path under Dataset/ (the read-only 1.6 GB source data)
  * any path under data/    (our derived parquet cache)
  * any *.parquet / *.pkl / *.joblib file
  * any file larger than 50 MB

Run it before every push:  python tools/check_no_data.py
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

MAX_BYTES = 50 * 1024 * 1024
FORBIDDEN_PREFIXES = ("Dataset/", "data/")
FORBIDDEN_SUFFIXES = (".parquet", ".pkl", ".joblib")


class NotAGitRepo(RuntimeError):
    """Raised when this guard is run somewhere git cannot answer."""


def tracked_files() -> list[str]:
    """Every path git currently tracks (i.e. would be pushed).

    Raises NotAGitRepo with a readable explanation rather than letting a
    CalledProcessError or FileNotFoundError traceback escape: this script is a
    safety guard, and a guard that crashes confusingly is worse than one that
    says plainly why it could not check.
    """
    try:
        result = subprocess.run(
            ["git", "ls-files"], capture_output=True, text=True, check=True
        )
    except FileNotFoundError as exc:
        raise NotAGitRepo("git is not installed or not on PATH") from exc
    except subprocess.CalledProcessError as exc:
        detail = (exc.stderr or "").strip().splitlines()
        raise NotAGitRepo(
            detail[0] if detail else "git ls-files failed"
        ) from exc
    return [line for line in result.stdout.splitlines() if line.strip()]


def main() -> int:
    """Check that nothing forbidden is tracked. Returns an exit code.

    Non-zero means a data file, a parquet, or a file over 50 MB has been
    staged, and the commit should not go out.
    """
    problems: list[str] = []

    try:
        tracked = tracked_files()
    except NotAGitRepo as exc:
        print(f"check_no_data: cannot check -- {exc}.")
        print("Run this from inside the project's git working tree.")
        return 2

    for rel in tracked:
        if rel.startswith(FORBIDDEN_PREFIXES):
            problems.append(f"FORBIDDEN PATH   {rel}")
            continue
        if rel.endswith(FORBIDDEN_SUFFIXES):
            problems.append(f"FORBIDDEN TYPE   {rel}")
            continue
        path = Path(rel)
        if path.is_file() and path.stat().st_size > MAX_BYTES:
            mb = path.stat().st_size / 1024 / 1024
            problems.append(f"TOO LARGE {mb:7.1f} MB  {rel}")

    if problems:
        print("check_no_data: FAILED -- these must not be committed:")
        for p in problems:
            print("  " + p)
        return 1

    print(f"check_no_data: OK ({len(tracked)} tracked files, none forbidden, "
          "none >50 MB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
