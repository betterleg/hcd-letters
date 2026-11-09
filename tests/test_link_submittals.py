"""Checks for he_letters/link_submittals.py review rounds. Run: python tests/test_link_submittals.py (or pytest).
Cases are real letter sequences (dates from HCD's letters and the Download Tool, 6th cycle)."""
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "he_letters"))
from link_submittals import review_rounds, norm  # noqa: E402


def letter(j, reviewed, typ, recv, first=None, cycle="6", status="downloaded"):
    return {"jurisdiction": j, "reviewed": reviewed, "type": typ, "cycle": cycle, "status": status,
            "received_date": recv, "first_received_date": first or recv}


def tool(*rows):
    he = {}
    for j, rd, typ in rows:
        he.setdefault(norm(j), []).append((date.fromisoformat(rd), {"type": typ, "planning_period": "6", "pdf_url": ""}))
    return he


def run(L, he):
    review_rounds(L, he)
    return {x["reviewed"]: x for x in L}


def test_jackson_new_round_after_out_letter():
    # May 2024 "Out" letter closed the March round; the December modifications start a new one.
    L = [letter("Jackson", "2023-05-08", "Initial Draft", "2023-02-08"),
         letter("Jackson", "2024-05-20", "Adopted", "2024-03-21"),
         letter("Jackson", "2025-02-06", "Adopted", "2024-12-09", first="2024-03-21")]
    r = run(L, tool(("Jackson", "2023-02-08", "Initial Draft"), ("Jackson", "2024-03-21", "Adopted"),
                    ("Jackson", "2024-12-09", "Adopted")))
    x = r["2025-02-06"]
    assert x["submittal_date"] == "2024-12-09" and x["review_days"] == 59, x
    assert x["review_start_text"] == "2024-12-09" and x["review_flags"] is None, x
    assert r["2024-05-20"]["review_days"] == 60


def test_statutory_limit_90_first_submittal_60_after():
    # Gov. Code 65585: 90 days for the first submittal of the cycle, 60 for every one after it.
    L = [letter("Jackson", "2015-07-13", "Adopted", None, cycle="5", status="downloaded"),   # prior cycle letter
         letter("Jackson", "2023-05-08", "Initial Draft", "2023-02-08"),
         letter("Jackson", "2024-05-20", "Adopted", "2024-03-21"),
         letter("Jackson", "2024-07-30", "Adopted", "2024-05-25")]                              # constructed: 66 days
    r = run(L, tool(("Jackson", "2023-02-08", "Initial Draft"), ("Jackson", "2024-03-21", "Adopted"),
                    ("Jackson", "2024-05-25", "Adopted")))
    a, b, c = r["2023-05-08"], r["2024-05-20"], r["2024-07-30"]
    assert a["review_limit_days"] == 90 and a["review_days"] == 89 and a["review_flags"] is None, a
    assert b["review_limit_days"] == 60 and b["review_days"] == 60 and b["review_flags"] is None, b
    assert c["review_limit_days"] == 60 and c["review_flags"] == "over_statutory_limit", c


def test_first_submittal_limit_applies_to_a_subsequent_draft_type_too():
    # The limit follows the order of submittals, not the type label: a jurisdiction's first letter of the cycle
    # gets 90 days even if HCD labels it a subsequent draft; a later "Draft" gets 60.
    L = [letter("Order", "2024-04-25", "Subsequent Draft", "2024-01-30"),     # 86 days, first of cycle
         letter("Order", "2024-09-10", "Draft", "2024-07-01")]                # 71 days, second
    r = run(L, tool(("Order", "2024-01-30", "Subsequent Draft"), ("Order", "2024-07-01", "Draft")))
    assert r["2024-04-25"]["review_limit_days"] == 90 and r["2024-04-25"]["review_flags"] is None
    assert r["2024-09-10"]["review_limit_days"] == 60 and r["2024-09-10"]["review_flags"] == "over_statutory_limit"


def test_ceres_revision_during_review_does_not_reset():
    # Adopted element received March 26; something received May 15 (a week before the letter) is a revision.
    L = [letter("Ceres", "2025-02-03", "Subsequent Draft", "2025-01-22"),
         letter("Ceres", "2025-05-22", "Adopted", "2025-05-15", first="2025-03-26")]
    r = run(L, tool(("Ceres", "2025-01-22", "Subsequent Draft"), ("Ceres", "2025-03-26", "Adopted")))
    x = r["2025-05-22"]
    assert x["submittal_date"] == "2025-03-26" and x["review_days"] == 57, x
    assert x["review_start_text"] == "2025-03-26" and x["review_flags"] is None, x


def test_arvin_letter_typo_kept_beside_tool_date():
    # The letter says December 17, 2023; the Download Tool has the subsequent draft on December 17, 2024.
    L = [letter("Arvin", "2023-10-13", "Initial Draft", "2023-07-20", cycle=""),   # a letter with no cycle still closes a round
         letter("Arvin", "2024-03-11", "Subsequent Draft", "2024-01-11"),
         letter("Arvin", "2024-07-15", "Adopted", "2024-05-16"),
         letter("Arvin", "2024-12-24", "Subsequent Draft", "2023-12-17")]
    r = run(L, tool(("Arvin", "2023-07-20", "Initial Draft"), ("Arvin", "2024-01-11", "Subsequent Draft"),
                    ("Arvin", "2024-05-16", "Adopted"), ("Arvin", "2024-12-17", "Subsequent Draft")))
    assert r["2024-03-11"]["submittal_date"] == "2024-01-11" and r["2024-03-11"]["review_days"] == 60
    x = r["2024-12-24"]
    assert x["submittal_date"] == "2024-12-17" and x["review_days"] == 7, x
    assert x["review_start_text"] == "2023-12-17" and "tool_text_disagree" in x["review_flags"], x


def test_amador_city_letter_closes_the_round_through_the_alias():
    # Real sequence: HCD wrote to "Amador City" on 2024-07-05 (the same jurisdiction via ALIASES), so the
    # February 2025 letter's round starts with the December 20, 2024 resubmittal, not May 7.
    L = [letter("Amador City", "2024-07-05", "Adopted", "2024-05-07"),
         letter("Amador", "2025-02-14", "Adopted", "2024-12-20", first="2024-05-07")]
    r = run(L, tool(("Amador", "2024-05-07", "Adopted"), ("Amador", "2024-12-20", "Adopted")))
    x = r["2025-02-14"]
    assert x["submittal_date"] == "2024-12-20" and x["review_days"] == 56 and x["review_flags"] is None, x


def test_long_round_without_a_letter_is_flagged():
    # Constructed: with no HCD letter between May 2024 and February 2025 it is one 283-day round, flagged.
    L = [letter("Amador", "2025-02-14", "Adopted", "2024-12-20", first="2024-05-07")]
    r = run(L, tool(("Amador", "2024-05-07", "Adopted"), ("Amador", "2024-12-20", "Adopted")))
    x = r["2025-02-14"]
    assert x["submittal_date"] == "2024-05-07" and x["review_days"] == 283 and x["round_submittals"] == 2, x
    assert x["review_flags"] == "over_statutory_limit", x


def test_contact_hcd_letters_close_rounds_and_get_no_pairing():
    L = [letter("Testville", "2024-01-10", "Draft", None, status="contact_hcd"),
         letter("Testville", "2024-04-01", "Draft", "2024-02-01")]
    r = run(L, tool(("Testville", "2023-11-01", "Draft"), ("Testville", "2024-02-01", "Draft")))
    assert r["2024-04-01"]["submittal_date"] == "2024-02-01" and r["2024-04-01"]["review_days"] == 60
    assert r["2024-01-10"].get("review_days") is None and r["2024-01-10"]["round_start_tool"] is None


def test_same_day_submittals_do_not_break_sorting():
    # Two uploads received the same day (e.g. element and appendix) must not make the sort compare rows.
    L = [letter("Twin", "2024-04-01", "Draft", "2024-02-01")]
    x = run(L, tool(("Twin", "2024-02-01", "Draft"), ("Twin", "2024-02-01", "Draft")))["2024-04-01"]
    assert x["submittal_date"] == "2024-02-01" and x["round_submittals"] == 2, x


def test_scanned_letter_uses_the_tool_date():
    # A PDF with no text layer ("downloaded_scanned") has no dates of its own; the Download Tool still dates it.
    L = [letter("Scanville", "2024-04-01", "Draft", None, status="downloaded_scanned")]
    x = run(L, tool(("Scanville", "2024-02-01", "Draft")))["2024-04-01"]
    assert x["submittal_date"] == "2024-02-01" and x["review_days"] == 60 and x["review_start_text"] is None, x


def test_element_link_is_the_rounds_first_submittal():
    # Ceres: the letter's received date (May 15) is a revision; the element reviewed is the March 26 submittal.
    L = [letter("Ceres", "2025-05-22", "Adopted", "2025-05-15", first="2025-03-26")]
    he = tool(("Ceres", "2025-03-26", "Adopted"), ("Ceres", "2025-05-15", "Adopted"))
    he["ceres"][0][1]["pdf_url"] = "https://example/round-start.pdf"
    x = run(L, he)["2025-05-22"]
    assert x["he_pdf_url"] == "https://example/round-start.pdf" and x["he_received_date"] == "2025-03-26", x
    assert x["submittal_match"] == "first submittal of the review round", x


def test_no_tool_submittal_falls_back_to_letter():
    L = [letter("Nowhere", "2024-06-28", "Draft", "2024-04-30")]
    x = run(L, {})["2024-06-28"]
    assert x["submittal_date"] == "2024-04-30" and x["review_days"] == 59 and x["review_flags"] == "no_tool_submittal", x


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print("ok ", name)
