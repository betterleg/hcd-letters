"""Checks for he_letters/link_submittals.py review rounds. Run: python tests/test_link_submittals.py (or pytest).
Cases are real letter sequences (dates from HCD's letters and the Download Tool, 6th cycle)."""
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "he_letters"))
from link_submittals import review_rounds, match_elements, letter_cycles, norm  # noqa: E402


def letter(j, reviewed, typ, recv, first=None, cycle="6", status="downloaded"):
    return {"jurisdiction": j, "reviewed": reviewed, "type": typ, "cycle": cycle, "status": status,
            "received_date": recv, "first_received_date": first or recv}


def tool(*rows):
    he = {}
    for j, rd, typ in rows:
        he.setdefault(norm(j), []).append((date.fromisoformat(rd), {"type": typ, "planning_period": "6", "pdf_url": ""}))
    return he


def tool_c(*rows):
    """Tool rows with their own cycle: (jurisdiction, received date, type, planning_period)."""
    he = {}
    for j, rd, typ, cyc in rows:
        he.setdefault(norm(j), []).append((date.fromisoformat(rd), {"type": typ, "planning_period": cyc, "pdf_url": f"{j}-{rd}.pdf"}))
    return he


def full(L, he):
    """The order main() runs: letter cycles, element matching, review rounds."""
    letter_cycles(L, he)
    match_elements(L, he)
    review_rounds(L, he)
    return {x["reviewed"]: x for x in L}


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


def test_del_mar_other_cycle_letter_does_not_close_the_round():
    # Real sequence. HCD's Dec 4, 2020 "Conditional" letter (cycle 5) answers the City's Oct 20, 2020 correspondence
    # on its 5th-cycle programs (65585(i)); it falls inside the review of the Oct 20, 2020 6th-cycle draft, which
    # ended with the Dec 17, 2020 letter. Only same-cycle (or blank-cycle) letters close a round.
    L = [letter("Del Mar", "2020-07-31", "Tech Assist", None),
         letter("Del Mar", "2020-12-04", "Conditional", None, cycle="5"),
         letter("Del Mar", "2020-12-17", "Draft", "2020-10-20")]
    x = run(L, tool(("Del Mar", "2020-10-20", "Draft")))["2020-12-17"]
    assert x["submittal_date"] == "2020-10-20" and x["review_days"] == 58, x
    assert x["round_start_tool"] == "2020-10-20" and x["review_limit_days"] == 90 and x["review_flags"] is None, x


def test_winters_conditional_letter_still_closes_the_round():
    # Real sequence. The Dec 27, 2021 letter is labeled "Conditional" but reviewed the Sept 2021 adopted element,
    # so it closes that round; the May 2022 letter's round starts with the March 29, 2022 submittal.
    L = [letter("Winters", "2021-07-26", "Draft", "2021-05-27"),
         letter("Winters", "2021-12-27", "Conditional", "2021-09-30"),
         letter("Winters", "2022-05-11", "Adopted", "2022-03-29")]
    r = run(L, tool(("Winters", "2021-05-27", "Draft"), ("Winters", "2021-09-29", "Adopted"), ("Winters", "2022-03-29", "Adopted")))
    x = r["2022-05-11"]
    assert x["submittal_date"] == "2022-03-29" and x["review_days"] == 43, x


def test_element_link_stays_in_the_letters_cycle():
    # A cycle-5 letter that names no received date must not link a 6th-cycle Tool document posted before it.
    L = [letter("Del Mar", "2020-12-04", "Conditional", None, cycle="5")]
    he = tool(("Del Mar", "2020-10-20", "Draft"))
    he["delmar"][0][1]["pdf_url"] = "https://example/6th-cycle-draft.pdf"
    match_elements(L, he)
    review_rounds(L, he)
    x = L[0]
    assert not x["he_pdf_url"] and not x["submittal_match"] and not x["he_received_date"], x


def test_fort_jones_mislabeled_letter_uses_the_tools_cycle():
    # Real sequence. HCD's table labels the Jan 16, 2020 letter cycle 6, but it reviewed the Nov 21, 2019 draft that the
    # Download Tool files as 5th cycle (fort-jones-5th-draft112119.pdf). With the Tool's cycle it closes that round,
    # so the Mar 10, 2020 letter on the adopted element counts 15 days from Feb 24, 2020.
    L = [letter("Fort Jones", "2020-01-16", "Draft", "2019-11-21"),
         letter("Fort Jones", "2020-03-10", "Adopted", "2020-02-24", cycle="5")]
    r = full(L, tool_c(("Fort Jones", "2019-11-21", "Draft", "5"), ("Fort Jones", "2020-02-24", "Adopted", "5")))
    a, b = r["2020-01-16"], r["2020-03-10"]
    assert a["cycle_from_tool"] == "5" and a["he_pdf_url"] == "Fort Jones-2019-11-21.pdf" and a["round_start_tool"] == "2019-11-21", a
    assert b["submittal_date"] == "2020-02-24" and b["review_days"] == 15 and b["review_flags"] is None, b


def test_kern_mislabeled_letter_closes_its_5th_cycle_round():
    # Real sequence. The Nov 29, 2021 letter (labeled cycle 6) reviewed the 5th-cycle adopted element of Aug 31, 2021;
    # the Jul 13, 2023 letter's round starts with the May 15, 2023 submittal, 59 days.
    L = [letter("Kern County", "2021-11-29", "Adopted", "2021-08-31"),
         letter("Kern County", "2023-07-13", "Adopted", "2023-05-15", cycle="5")]
    r = full(L, tool_c(("Kern County", "2021-08-31", "Adopted", "5"), ("Kern County", "2023-05-15", "Adopted", "5"),
                       ("Kern County", "2023-12-07", "Initial Draft", "6")))
    a, b = r["2021-11-29"], r["2023-07-13"]
    assert a["cycle_from_tool"] == "5" and a["round_start_tool"] == "2021-08-31" and a["review_days"] == 90, a
    assert b["submittal_date"] == "2023-05-15" and b["review_days"] == 59 and b["review_flags"] is None, b


def test_letter_with_no_date_keeps_its_label():
    # Del Mar's Dec 4, 2020 letter names no received date, so its cycle-5 label stands (no Tool match to go by).
    L = [letter("Del Mar", "2020-12-04", "Conditional", None, cycle="5")]
    x = full(L, tool_c(("Del Mar", "2020-10-20", "Draft", "6")))["2020-12-04"]
    assert x.get("cycle_from_tool") is None and not x["he_pdf_url"], x


def test_letter_that_reviews_no_submittal_has_no_limit():
    # Del Mar Dec 4, 2020 (65585(i), cycle 5) and the Jul 31, 2020 technical assistance letter name no received date
    # and have no Tool submittal: no statutory review period, flagged no_submittal_reviewed.
    L = [letter("Del Mar", "2020-07-31", "Tech Assist", None),
         letter("Del Mar", "2020-12-04", "Conditional", None, cycle="5"),
         letter("Del Mar", "2020-12-17", "Draft", "2020-10-20")]
    r = full(L, tool_c(("Del Mar", "2020-10-20", "Draft", "6")))
    for k in ("2020-07-31", "2020-12-04"):
        assert r[k]["review_limit_days"] is None and r[k]["review_flags"] == "no_submittal_reviewed", r[k]
    x = r["2020-12-17"]
    assert x["review_limit_days"] == 90 and x["review_days"] == 58 and x["review_flags"] is None, x


def test_adopted_letter_with_no_date_keeps_its_limit():
    # A letter labeled adopted (including HCD's "Addopted" spelling) is treated as a real review even with no date.
    L = [letter("Marina", "2023-04-27", "Adopted", None), letter("Contra Costa County", "2023-04-27", "Addopted", None)]
    r = full(L, {})
    for x in L:
        assert x["review_limit_days"] == 90 and x["review_flags"] == "no_tool_submittal", x


def test_scanned_letter_with_no_tool_submittal_is_not_called_a_non_review():
    # A scanned letter has no text, so a missing date says nothing about what it reviewed.
    L = [letter("Scanville", "2024-04-01", "Draft", None, status="downloaded_scanned")]
    x = full(L, {})["2024-04-01"]
    assert x["review_limit_days"] == 90 and x["review_flags"] == "no_tool_submittal", x


def test_no_tool_submittal_falls_back_to_letter():
    L = [letter("Nowhere", "2024-06-28", "Draft", "2024-04-30")]
    x = run(L, {})["2024-06-28"]
    assert x["submittal_date"] == "2024-04-30" and x["review_days"] == 59 and x["review_flags"] == "no_tool_submittal", x


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print("ok ", name)
