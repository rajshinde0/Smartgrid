"""Build one notebook from its percent-format source and execute it end to end.

    python tools/build_and_run.py 00_explore

Steps:
  1. notebooks/src_py/<name>.py  --nbbuild-->  notebooks/<name>.ipynb
  2. jupyter nbconvert --to notebook --execute --inplace notebooks/<name>.ipynb

Exits non-zero if execution fails, and prints the offending cell plus its
traceback so the error can be fixed before anything is committed. A notebook is
never committed unless this script exits 0.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src import nbbuild  # noqa: E402

TIMEOUT_SECONDS = 3600      # generous: some cells read 100+ MB CSVs


def report_failure(ipynb: Path) -> None:
    """Print the first cell that raised, with its traceback."""
    try:
        import nbformat

        nb = nbformat.read(ipynb, as_version=4)
    except Exception as exc:                        # pragma: no cover
        print(f"(could not re-read {ipynb.name} to locate the error: {exc})")
        return

    for i, cell in enumerate(nb.cells):
        for out in cell.get("outputs", []):
            if out.get("output_type") == "error":
                print(f"\n--- FAILED in cell {i} ({cell.cell_type}) ---")
                print(cell.source[:1500])
                print("--- traceback ---")
                print("\n".join(out.get("traceback", []))[:4000])
                return
    print("(no error output found in the notebook)")


def main(argv: list[str]) -> int:
    """Build and execute one notebook. Returns a process exit code.

    Non-zero means the notebook raised, and nothing should be committed.
    """
    if len(argv) != 2:
        print(__doc__)
        return 2

    name = argv[1].removesuffix(".py").removesuffix(".ipynb")
    py = ROOT / "notebooks" / "src_py" / f"{name}.py"
    ipynb = ROOT / "notebooks" / f"{name}.ipynb"

    if not py.is_file():
        print(f"ERROR: source not found: {py}")
        return 2

    nbbuild.build(py, ipynb)

    cmd = [
        sys.executable, "-m", "nbconvert",
        "--to", "notebook", "--execute", "--inplace",
        f"--ExecutePreprocessor.timeout={TIMEOUT_SECONDS}",
        "--ExecutePreprocessor.kernel_name=python3",
        str(ipynb),
    ]
    print("running:", " ".join(cmd[-4:]))
    proc = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)

    tail = (proc.stderr or "").strip().splitlines()
    if tail:
        print("\n".join(tail[-25:]))

    if proc.returncode != 0:
        print(f"\n*** EXECUTION FAILED (exit {proc.returncode}) ***")
        report_failure(ipynb)
        return proc.returncode

    print(f"\nOK: {ipynb.relative_to(ROOT)} executed cleanly.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
