"""Checks for scripts/apply_corrections.py. Run: python tests/test_apply_corrections.py (or pytest)."""
import csv
import os
import subprocess
import sys
import tempfile
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "apply_corrections.py"


def write(p, rows, eol="\n"):
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f, lineterminator=eol)
        w.writerows(rows)


def read(p):
    return list(csv.DictReader(open(p, encoding="utf-8")))


def run(root):
    return subprocess.run([sys.executable, str(SCRIPT), "hau", "he"], env={**os.environ, "HCD_ROOT": str(root)},
                          capture_output=True, text=True, check=True).stdout


def test_corrections():
    with tempfile.TemporaryDirectory() as t:
        root = Path(t)
        write(root / "hau/corrections.csv", [["task", "field", "old_value", "new_value", "note"],
                                             ["T1", "letter_url", "https://x/davis.pdf", "https://x/del-mar.pdf", "wrong PDF"],
                                             ["T2", "letter_url", "https://x/old.pdf", "https://x/new.pdf", "HCD now shows another link"]])
        write(root / "hau/hau_letters.csv", [["task", "jurisdiction", "letter_url"], ["T1", "Del Mar", "https://x/davis.pdf"],
                                             ["T2", "Elsewhere", "https://x/changed.pdf"], ["T3", "Davis", "https://x/davis.pdf"]], eol="\r\n")
        write(root / "hau/letters_index.csv", [["task", "jurisdiction", "letter_url", "status", "fetched_from", "text_file"],
                                               ["T1", "Del Mar", "https://x/davis.pdf", "downloaded", "dashboard_link", "letters/Davis.txt"],
                                               ["T3", "Davis", "https://x/davis.pdf", "downloaded", "dashboard_link", "letters/Davis.txt"]])
        write(root / "he_letters/corrections.csv", [["jurisdiction", "letter_date", "type", "field", "old_value", "new_value", "note"],
                                                    ["Marina", "2023-04-27", "Adopted", "cycle", "6", "5", "5th-cycle element"]])
        write(root / "he_letters/letters.csv", [["county", "jurisdiction", "type", "cycle", "reviewed", "weblink"],
                                                ["Monterey", "Marina", "Adopted", "6", "2023-04-27", "https://x/m.pdf"],
                                                ["Monterey", "Marina", "Adopted", "6", "2024-04-11", "https://x/m2.pdf"]])
        out = run(root)
        h = {r["task"]: r for r in read(root / "hau/hau_letters.csv")}
        assert h["T1"]["letter_url"] == "https://x/del-mar.pdf" and h["T3"]["letter_url"] == "https://x/davis.pdf", h
        assert h["T2"]["letter_url"] == "https://x/changed.pdf" and "correction skipped" in out, out
        assert b"\r\n" in (root / "hau/hau_letters.csv").read_bytes()          # line endings kept
        i = {r["task"]: r for r in read(root / "hau/letters_index.csv")}
        assert i["T1"]["text_file"] == "" and i["T1"]["status"] == "not_downloaded_yet", i      # re-download the right PDF
        assert i["T3"]["text_file"] == "letters/Davis.txt", i
        m = read(root / "he_letters/letters.csv")
        assert [r["cycle"] for r in m] == ["5", "6"], m
        run(root)                                                              # running again changes nothing
        assert read(root / "he_letters/letters.csv") == m


if __name__ == "__main__":
    test_corrections()
    print("ok  test_corrections")
