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

    replacement = f"{begin}\n{content.strip()}\n{end}"
    report_path.write_text(pattern.sub(lambda _: replacement, text), encoding="utf-8")
    save_md(name, content)
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

    log = log.sort_values(["phase", "id"]).reset_index(drop=True)
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
        if "pending Phase" in match.group(2):
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
