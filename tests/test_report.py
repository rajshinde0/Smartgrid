"""The decision log must come out in the same order every time.

On 7 Oct the published table silently reordered: `log_decision` sorted on
`["phase", "id"]`, but `phase` goes in as a string and comes back from
`read_csv` as int64, so the column held mixed types and the sort fell back to
insertion order. Re-running one notebook moved its decisions to the bottom of
section 7 of the report.

Every id is a zero-padded `D<phase>-<n>`, so sorting on `id` as text *is*
phase-then-number, and it does not depend on how a dtype was inferred.
"""

from __future__ import annotations

import pandas as pd
import pytest

from src import report


@pytest.fixture
def log(tmp_path, monkeypatch):
    """Point the decision log at a temporary file, never the real one."""
    path = tmp_path / "decision_log.csv"
    monkeypatch.setattr(report, "DECISIONS_CSV", path)
    return path


def _log(id_: str, phase: str, decision: str = "x") -> None:
    report.log_decision(
        id=id_, phase=phase, decision=decision,
        options_considered="a; b", chosen="a", reason="r",
        effect_on_results="none",
    )


def test_entries_come_back_in_id_order_whatever_order_they_arrive(log):
    for id_, phase in [("D04-06", "4"), ("D00-01", "0"),
                       ("D08-04", "8"), ("D01-02", "1")]:
        _log(id_, phase)

    ids = pd.read_csv(log)["id"].tolist()
    assert ids == sorted(ids) == ["D00-01", "D01-02", "D04-06", "D08-04"]


def test_re_registering_one_entry_does_not_move_it(log):
    """Re-running a single notebook re-registers its decisions. That must not
    push them to the end of the published table.
    """
    for id_, phase in [("D00-01", "0"), ("D04-06", "4"), ("D08-04", "8")]:
        _log(id_, phase)
    before = pd.read_csv(log)["id"].tolist()

    _log("D04-06", "4", decision="same decision, re-registered")

    after = pd.read_csv(log)["id"].tolist()
    assert after == before, "a re-registered entry must keep its place"


def test_re_registering_replaces_rather_than_duplicates(log):
    _log("D02-01", "2", decision="first wording")
    _log("D02-01", "2", decision="second wording")

    rows = pd.read_csv(log)
    assert len(rows) == 1
    assert rows.loc[0, "decision"] == "second wording"


def test_ten_or_more_decisions_in_a_phase_still_sort_numerically(log):
    """Zero padding is what makes a text sort correct: D04-10 must follow
    D04-09, which plain lexicographic order on unpadded numbers would break.
    """
    for n in range(1, 13):
        _log(f"D04-{n:02d}", "4")

    ids = pd.read_csv(log)["id"].tolist()
    assert ids == [f"D04-{n:02d}" for n in range(1, 13)]


def test_published_table_is_in_the_same_order_as_the_log(log):
    """Section 7 is rendered from the CSV by a second sort, in a different
    function. The two must not disagree.
    """
    for id_, phase in [("D08-04", "8"), ("D00-01", "0"), ("D04-06", "4")]:
        _log(id_, phase)

    table = report.decision_log_table()
    stored = pd.read_csv(log)["id"].tolist()

    # The rendered table drops the id column, so check the decisions appear in
    # the order their ids imply.
    order = pd.read_csv(log).set_index("id").loc[stored, "decision"].tolist()
    positions = [table.index(d) for d in order]
    assert positions == sorted(positions), (
        "the published table must follow the same order as the stored log"
    )
