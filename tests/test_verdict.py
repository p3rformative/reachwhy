"""Overall verdict of a partial engine: never green while complete is false."""
import pytest

from conftest import CASES, hop, load_case, run


@pytest.mark.parametrize("case", CASES)
def test_overall_is_never_green_while_incomplete(case):
    snap, exp = load_case(case)
    v = run(snap, exp)
    assert v["complete"] is False
    assert v["overall"] != "green", case


def test_all_green_evaluated_hops_give_amber_with_an_explanation():
    snap, exp = load_case("synthetic-dns-hub-zone-01")
    v = run(snap, exp)
    assert [h["state"] for h in v["hops"]] == ["green", "green"]
    assert v["overall"] == "amber" and v["firstRedHop"] is None
    assert v["summary"].startswith("2 of 7 hops evaluated (origin, dns)")
    assert "cannot be green" in v["summary"]


def test_red_stays_red_and_summary_counts_hops():
    snap, exp = load_case("demo-basic-01")
    v = run(snap, exp)
    assert v["overall"] == "red" and v["firstRedHop"] == "dns"
    assert v["summary"].startswith("2 of 7 hops evaluated")
    assert "cannot be green" not in v["summary"]


def test_cli_exit_code_for_the_downgraded_case(capsys):
    from conftest import CORPUS
    from reachwhy.__main__ import main
    assert main(["--case", str(CORPUS / "synthetic-route-all-off-dns-ok-01")]) == 0
    assert '"overall": "amber"' in capsys.readouterr().out
