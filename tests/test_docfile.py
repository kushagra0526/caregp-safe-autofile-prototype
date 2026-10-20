import os, sys, unittest
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from docfile import ids, clinic, docs, match


class T(unittest.TestCase):
    def test_medicare_check_digit(self):
        first8 = "29537194"
        num = first8 + ids.medicare_check(first8) + "1"
        self.assertTrue(ids.medicare_ok(num))
        bad = num[:3] + str((int(num[3]) + 1) % 10) + num[4:]
        self.assertFalse(ids.medicare_ok(bad))
        self.assertFalse(ids.medicare_ok("1" + num[1:]))          # must start 2-6

    def test_ihi_luhn(self):
        body = "800360816669001"
        self.assertTrue(ids.ihi_ok(body + ids.luhn_digit(body)))
        self.assertFalse(ids.ihi_ok(body + str((int(ids.luhn_digit(body)) + 1) % 10)))

    def test_ocr_digits_and_dates(self):
        f = match.extract("DOB: O3/l1/1975 and 7 Mar 2012 and 2001-02-03")
        self.assertIn((1975, 11, 3), f["dates"])
        self.assertIn((2012, 3, 7), f["dates"])
        self.assertIn((2001, 2, 3), f["dates"])

    def test_twins_need_more_than_dob_and_card(self):
        a = dict(id="A", first="Jack", last="Nguyen", sex="M", dob=(2012, 3, 14), prev_last=None, medicare="2953719401", irn=3, address="5 King St", ihi="")
        b = dict(a, id="B", first="Liam", irn=4)
        idx = match.Index([a, b])
        txt = "Patient: NGUYEN, J.\nDOB 14/03/2012\nMedicare No: 2953 71940 1"
        self.assertEqual(match.decide(idx, txt)["decision"], "REVIEW")
        self.assertEqual(match.decide(idx, txt.replace("NGUYEN, J.", "Jack Nguyen") + " (3)")["patient"], "A")

    def test_irn_conflict_blocks_autofile(self):
        a = dict(id="A", first="Sarah", last="Kelly", sex="F", dob=(1980, 5, 2), prev_last=None, medicare="2953719401", irn=1, address="9 Park Rd", ihi="")
        idx = match.Index([a])
        o = match.decide(idx, "Patient: Sarah Kelly DOB 02/05/1980 Medicare 2953 71940 1 (2)")
        self.assertEqual(o["decision"], "REVIEW")
        self.assertIn("IRN", o["reason"])

    def test_dev_no_misfiles(self):
        pts = clinic.make(9)
        idx = match.Index(pts)
        bad = sum(1 for d in docs.make(77, pts, 300) if (o := match.decide(idx, d["text"]))["decision"] == "AUTO_FILE" and o["patient"] != d["truth"])
        self.assertLessEqual(bad, 1)


if __name__ == "__main__":
    unittest.main()
