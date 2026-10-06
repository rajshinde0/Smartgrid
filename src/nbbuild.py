"""Turn a percent-format Python file into a Jupyter notebook.

Why this exists
---------------
Writing .ipynb JSON by hand is painful and easy to corrupt. So every notebook in
this project is *authored* as an ordinary Python file in percent format under
notebooks/src_py/, and this module converts it to a real .ipynb which is then
executed with nbconvert. Both files are committed: the .py is the editable
source, the .ipynb is the graded artefact.

Percent format
--------------
    # %% [markdown]
    # ## A heading
    # Plain English explanation. Leading "# " is stripped.

    # %%
    print("a code cell")

Any line beginning with "# %%" starts a new cell. "# %% [markdown]" makes it a
markdown cell (comment markers stripped); plain "# %%" makes it a code cell
(left exactly as written). Text before the first marker is ignored, so a module
docstring at the top of the .py file is allowed.

Usage
-----
    python src/nbbuild.py notebooks/src_py/00_explore.py notebooks/00_explore.ipynb
"""

from __future__ import annotations

import sys
from pathlib import Path

import nbformat

MARKER = "# %%"
MARKDOWN_MARKER = "# %% [markdown]"


def _strip_comment(line: str) -> str:
    """Turn a markdown-cell source line back into plain markdown text."""
    if line.startswith("# "):
        return line[2:]
    if line == "#":
        return ""
    if line.startswith("#"):
        return line[1:]
    return line  # already plain (e.g. a line inside a fenced block)


def parse_cells(text: str) -> list[tuple[str, str]]:
    """Split percent-format source into a list of (cell_type, source) pairs."""
    cells: list[tuple[str, str]] = []
    kind: str | None = None
    buffer: list[str] = []

    def flush() -> None:
        if kind is None:
            return
        body = "\n".join(buffer).strip("\n")
        if not body.strip():
            return                      # skip empty cells
        cells.append((kind, body))

    for raw_line in text.splitlines():
        line = raw_line.rstrip("\n")
        if line.startswith(MARKER):
            flush()
            kind = "markdown" if line.startswith(MARKDOWN_MARKER) else "code"
            buffer = []
            continue
        if kind is None:
            continue                    # preamble before the first marker
        buffer.append(_strip_comment(line) if kind == "markdown" else line)

    flush()
    return cells


def build(py_path: str | Path, ipynb_path: str | Path) -> Path:
    """Convert one percent-format .py file into an (unexecuted) .ipynb."""
    py_path = Path(py_path)
    ipynb_path = Path(ipynb_path)

    cells = parse_cells(py_path.read_text(encoding="utf-8"))
    if not cells:
        raise ValueError(f"{py_path} produced no cells -- is it percent format?")

    nb = nbformat.v4.new_notebook()
    nb.cells = [
        nbformat.v4.new_markdown_cell(src)
        if kind == "markdown"
        else nbformat.v4.new_code_cell(src)
        for kind, src in cells
    ]
    nb.metadata = {
        "kernelspec": {
            "display_name": "Python 3",
            "language": "python",
            "name": "python3",
        },
        "language_info": {"name": "python", "version": sys.version.split()[0]},
    }

    ipynb_path.parent.mkdir(parents=True, exist_ok=True)
    nbformat.write(nb, ipynb_path)
    n_md = sum(1 for k, _ in cells if k == "markdown")
    print(
        f"nbbuild: {py_path.name} -> {ipynb_path.name} "
        f"({len(cells)} cells: {n_md} markdown, {len(cells) - n_md} code)"
    )
    return ipynb_path


def main(argv: list[str]) -> int:
    """Command-line entry point. Returns a process exit code."""
    if len(argv) != 3:
        print(__doc__)
        return 2
    build(argv[1], argv[2])
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
