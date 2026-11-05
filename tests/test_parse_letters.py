"""Checks for he_letters/parse_letters.py. Run: python tests/test_parse_letters.py (or pytest)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "he_letters"))
from parse_letters import parse  # noqa: E402

# Wording from HCD's Feb 6, 2025 letter to Jackson: the adopted element and, later, its modifications.
JACKSON = ("Dear City Manager: RE: City of Jackson's 6th Cycle (2021-2029) Adopted Housing Element "
           "Thank you for submitting the City of Jackson's (City) housing element that was adopted October 23, 2023 "
           "and received March 21, 2024, along with modifications received for review on December 9, 2024. "
           "The City did not adopt a compliant housing element within 120 days of the statutory deadline "
           "(September 15, 2021). HCD is pleased to find the adopted housing element in substantial compliance.")

DRAFT = ("RE: Review of the City's 6th Cycle Draft Housing Element "
         "Thank you for submitting the City's draft housing element received for review on April 30, 2024. "
         "Revisions will be necessary to substantially comply with State Housing Element Law.")


def test_letter_on_modifications_pairs_with_latest_receipt():
    p = parse(JACKSON, "2025-02-06")
    assert p["received_date"] == "2024-12-09", p
    assert p["first_received_date"] == "2024-03-21", p
    assert p["adopted_date"] == "2023-10-23", p
    assert p["statutory_due_date"] == "2021-09-15", p
    assert p["finding"] == "In", p


def test_single_receipt_unchanged():
    p = parse(DRAFT, "2024-06-28")
    assert p["received_date"] == p["first_received_date"] == "2024-04-30", p
    assert p["statutory_due_date"] is None and p["finding"] == "Out", p


def test_dates_after_the_letter_are_ignored():
    p = parse(DRAFT.replace("April 30, 2024", "April 30, 2025"), "2024-06-28")
    assert p["received_date"] is None, p


REVISIONS = ("Thank you for submitting the City of Farmersville's (City) revised draft housing element received for "
             "review on July 2, 2025, along with revisions received on August 26, 2025, and comments from the public. "
             "Revisions will be necessary to substantially comply with State Housing Element Law.")


def test_revisions_during_review_keep_the_original_submittal():
    # The 60/90-day review runs from the submittal (July 2), not from revisions sent during the review.
    p = parse(REVISIONS, "2025-08-29")
    assert p["received_date"] == "2025-07-02", p
    assert p["last_revision_date"] == "2025-08-26", p


def test_without_letter_date_takes_latest():
    assert parse(JACKSON)["received_date"] == "2024-12-09"


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print("ok ", name)
