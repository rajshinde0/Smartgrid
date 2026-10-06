"""Write generated tables into docs/PROJECT_REPORT.md from inside the notebooks.

The project rule is that **every number in the report comes from executed code**.
The safest way to guarantee that is to never type a number into the report by
hand. Instead the report contains named placeholder blocks:

    <!-- BEGIN:phase0_energy_profile -->
    pending Phase 0
    <!-- END:phase0_energy_profile -->

and a notebook fills one in with:

    report.update_block("phase0_energy_profile", report.md_table(df))

Re-running a notebook overwrites the block with the current numbers, so the
report cannot drift out of step with the analysis. Anything still reading
"pending Phase N" is genuinely not computed yet.
"""

from __future__ import annotations

import re
from pathlib import Path

import pandas as pd

from . import config as C

MD_DIR = C.RESULTS_DIR / "md"


def _fmt(value, float_places: int = 2) -> str:
    """Format one cell for a markdown table."""
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return "-"
    if isinstance(value, float):
        if value == int(value) and abs(value) < 1e15:
            return f"{int(value):,}"
        return f"{value:,.{float_places}f}"
    if isinstance(value, (int,)) and not isinstance(value, bool):
        return f"{value:,}"
    text = str(value)
    return text.replace("|", "\\|").replace("\n", " ")


def md_table(
    df: pd.DataFrame, *, index: bool = False, float_places: int = 2
) -> str:
    """Render a DataFrame as a GitHub-flavoured markdown table."""
    frame = df.reset_index() if index else df
    headers = [str(c).replace("_", " ") for c in frame.columns]

    lines = ["| " + " | ".join(headers) + " |"]
    lines.append("|" + "|".join("---" for _ in headers) + "|")
    for _, row in frame.iterrows():
        lines.append(
            "| " + " | ".join(_fmt(v, float_places) for v in row.tolist()) + " |"
        )
    return "\n".join(lines)


def figure(name: str, caption: str, takeaway: str) -> str:
    """Markdown for an embedded figure with its one-line takeaway underneath."""
    if not name.endswith(".png"):
        name = name + ".png"
    return f"![{caption}](../figures/{name})\n\n*{takeaway}*"


def save_md(name: str, text: str) -> Path:
    """Keep a copy of a generated block on disk (handy for the dashboard)."""
    MD_DIR.mkdir(parents=True, exist_ok=True)
    path = MD_DIR / f"{name}.md"
    path.write_text(text, encoding="utf-8")
    return path


MIN_HEADING_LEVEL = 4      # blocks sit under "## N." or "### N.x" sections


def _fix_heading_levels(content: str, minimum: int = MIN_HEADING_LEVEL) -> str:
    """Push a block's own headings below the section heading it sits under.

    Every block is a fragment inserted underneath a numbered section, so a
    heading written as `###` inside a block would render at the same level as
    the section containing it and flatten the document outline. This shifts a
    block's headings down so its shallowest one sits at `minimum`, preserving
    the relative structure within the block.

    Lines inside fenced code blocks are left alone -- a `#` there is a comment,
    not a heading.
    """
    lines = content.split("\n")
    in_fence = False
    levels = []
    for line in lines:
        if line.lstrip().startswith("```"):
            in_fence = not in_fence
            continue
        if not in_fence:
            match = re.match(r"^(#{1,6})\s+\S", line)
            if match:
                levels.append(len(match.group(1)))

    if not levels or min(levels) >= minimum:
        return content

    shift = minimum - min(levels)
    out = []
    in_fence = False
    for line in lines:
        if line.lstrip().startswith("```"):
            in_fence = not in_fence
            out.append(line)
            continue
        match = re.match(r"^(#{1,6})(\s+\S.*)$", line)
        if match and not in_fence:
            level = min(len(match.group(1)) + shift, 6)
            out.append("#" * level + match.group(2))
        else:
            out.append(line)
    return "\n".join(out)


WRAP_WIDTH = 80

# A paragraph is left exactly as written if any of its lines matches one of
# these: tables, headings, bullet and numbered lists, quotes, code fences,
# images and indented code all depend on their own line breaks.
#
# Note the bullet pattern requires a space after the marker. Matching a bare
# "*" would also catch a paragraph that merely *starts* with bold text, which
# is ordinary prose and should be re-wrapped like any other.
_STRUCTURAL_RE = re.compile(
    r"""^(?:
          \|                 # table row
        | \#{1,6}\s          # heading
        | [-*+]\s            # bullet list (marker must be followed by a space)
        | \d+\.\s            # numbered list
        | >                  # block quote
        | ```                # code fence
        | !\[                # image
        | \ {4}              # indented code
    )""",
    re.VERBOSE,
)


def _reflow(content: str, width: int = WRAP_WIDTH) -> str:
    """Re-wrap plain prose paragraphs to a fixed width.

    Generated prose is full of interpolated numbers, so a sentence written on one
    line in the notebook comes out broken at odd places once the values are
    substituted. Markdown joins those soft breaks when it renders, so the output
    is correct either way -- but the raw file is also read directly, and ragged
    paragraphs make it harder to follow.

    Only genuine prose is touched. Tables, lists, headings, block quotes, images
    and fenced code keep their own line structure.
    """
    import textwrap

    out: list[str] = []
    in_fence = False

    for paragraph in content.split("\n\n"):
        lines = paragraph.split("\n")
        fences = sum(1 for line in lines if line.lstrip().startswith("```"))

        if in_fence or fences:
            out.append(paragraph)
            if fences % 2 == 1:
                in_fence = not in_fence
            continue

        stripped = [line.strip() for line in lines if line.strip()]
        if not stripped:
            out.append(paragraph)
            continue

        is_structural = any(_STRUCTURAL_RE.match(line) for line in stripped)
        if is_structural:
            out.append(paragraph)
            continue

        joined = " ".join(stripped)
        joined = re.sub(r"\s+", " ", joined)
        # break_on_hyphens=False keeps "matched-budget" and "low-occupancy"
        # whole: markdown joins a soft line break with a space, so breaking at a
        # hyphen would render as "matched- budget". break_long_words=False
        # protects long URLs for the same reason.
        wrapped = textwrap.wrap(
            joined, width=width, break_on_hyphens=False, break_long_words=False
        )
        out.append("\n".join(wrapped) or paragraph)

    return "\n\n".join(out)


def update_block(name: str, content: str, *, report_path: Path | None = None) -> None:
    """Replace the text between <!-- BEGIN:name --> and <!-- END:name -->."""
    report_path = report_path or C.REPORT_PATH
    if not report_path.is_file():
        raise FileNotFoundError(
            f"{report_path} does not exist yet -- Phase 0 creates the skeleton."
        )

    text = report_path.read_text(encoding="utf-8")
    begin, end = f"<!-- BEGIN:{name} -->", f"<!-- END:{name} -->"

    pattern = re.compile(
        re.escape(begin) + r".*?" + re.escape(end), flags=re.DOTALL
    )
    if not pattern.search(text):
        raise KeyError(
            f"no block named {name!r} in {report_path.name}. "
            f"Add {begin} ... {end} to the report skeleton first."
        )

    body = _reflow(_fix_heading_levels(content.strip()))
    replacement = f"{begin}\n{body}\n{end}"
    report_path.write_text(pattern.sub(lambda _: replacement, text), encoding="utf-8")
    save_md(name, body)
    print(f"report: updated block {name!r} ({len(content.splitlines())} lines)")


def update_blocks(blocks: dict[str, str], *, report_path: Path | None = None) -> None:
    """Fill several blocks in one go."""
    for name, content in blocks.items():
        update_block(name, content, report_path=report_path)


# ---------------------------------------------------------------------------
# Decision log
# ---------------------------------------------------------------------------
# Every judgement call in the project -- thresholds, how bad values were
# handled, what was dropped, model choices, random seeds -- is recorded here by
# the notebook that made it, then rendered into section 7 of the report. Keyed
# by a short id so re-running a notebook updates its row instead of duplicating.
DECISIONS_CSV = C.RESULTS_DIR / "decision_log.csv"

DECISION_COLUMNS = [
    "id", "phase", "decision", "options_considered", "chosen", "reason",
    "effect_on_results",
]


def log_decision(
    id: str,
    phase: str,
    decision: str,
    options_considered: str,
    chosen: str,
    reason: str,
    effect_on_results: str,
) -> None:
    """Record (or update) one judgement call in the decision log."""
    row = {
        "id": id,
        "phase": phase,
        "decision": decision,
        "options_considered": options_considered,
        "chosen": chosen,
        "reason": reason,
        "effect_on_results": effect_on_results,
    }
    C.RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    if DECISIONS_CSV.is_file():
        log = pd.read_csv(DECISIONS_CSV)
        log = log[log["id"] != id]
        log = pd.concat([log, pd.DataFrame([row])], ignore_index=True)
    else:
        log = pd.DataFrame([row])

    # Sort on `id` alone, and as text. Every id is D<phase>-<n> zero-padded, so
    # lexicographic order *is* phase-then-number -- and it stays stable no
    # matter which notebook is re-run.
    #
    # Sorting on ["phase", "id"] looked equivalent and was not: `phase` is
    # passed in as a string but comes back from read_csv as int64, so the
    # column held mixed types and the sort silently fell back to insertion
    # order. Re-running one notebook moved its decisions to the bottom of the
    # published table.
    log["phase"] = log["phase"].astype(str)
    log = log.sort_values("id", kind="stable").reset_index(drop=True)
    log.to_csv(DECISIONS_CSV, index=False)


def decision_log_table() -> str:
    """Render the whole decision log as the markdown table for section 7."""
    if not DECISIONS_CSV.is_file():
        return "pending Phase 1"
    log = pd.read_csv(DECISIONS_CSV).sort_values(["phase", "id"]).reset_index(drop=True)
    log.insert(0, "#", range(1, len(log) + 1))
    log = log.drop(columns=["id"])
    log.columns = [
        "#", "Phase", "Decision", "Options considered", "Chosen", "Reason",
        "Effect on results",
    ]
    return md_table(log)


def publish_decision_log(report_path: Path | None = None) -> None:
    """Regenerate section 7 from the accumulated decision log."""
    update_block("decision_log", decision_log_table(), report_path=report_path)


def pending_blocks(report_path: Path | None = None) -> list[str]:
    """Every block still holding a 'pending Phase N' placeholder.

    Phase 7 must leave this list empty.
    """
    report_path = report_path or C.REPORT_PATH
    text = report_path.read_text(encoding="utf-8")
    out = []
    for match in re.finditer(
        r"<!-- BEGIN:(.*?) -->(.*?)<!-- END:\1 -->", text, flags=re.DOTALL
    ):
        # A block counts as unfilled only if it *starts* with the placeholder.
        # Matching the phrase anywhere in the block is too loose: a filled
        # section that explains how the placeholder mechanism works would flag
        # itself, which is exactly what happened to the Phase 7 methodology.
        if match.group(2).strip().startswith("pending Phase"):
            out.append(match.group(1))
    return out


def check_figures(report_path: Path | None = None) -> list[str]:
    """Every ![](../figures/x.png) link in the report that has no file behind it."""
    report_path = report_path or C.REPORT_PATH
    text = report_path.read_text(encoding="utf-8")
    missing = []
    for match in re.finditer(r"!\[[^\]]*\]\(\.\./figures/([^)]+)\)", text):
        if not (C.FIGURES_DIR / match.group(1)).is_file():
            missing.append(match.group(1))
    return sorted(set(missing))
