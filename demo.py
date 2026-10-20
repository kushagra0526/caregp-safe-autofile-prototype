"""Three faxes into a synthetic Sydney clinic: twins on one Medicare card, an IRN that points at
someone else, and a letter about a person who isn't a patient here."""
import sys
from docfile import ids, match

sys.stdout.reconfigure(encoding="utf-8")
card = "29537194" + ids.medicare_check("29537194") + "1"
fam = [dict(id="P00101", first="Jack", last="Nguyen", sex="M", dob=(2012, 3, 14), prev_last=None, medicare=card, irn=3, address="5 King St", ihi=""),
       dict(id="P00102", first="Liam", last="Nguyen", sex="M", dob=(2012, 3, 14), prev_last=None, medicare=card, irn=4, address="5 King St", ihi=""),
       dict(id="P00103", first="Olivia", last="Patel", sex="F", dob=(1951, 4, 6), prev_last=None, medicare="4123456782", irn=1, address="12 Park Rd", ihi="")]
fam[2]["medicare"] = "41234567" + ids.medicare_check("41234567") + "2"
idx = match.Index(fam)
m = f"{card[:4]} {card[4:9]} {card[9]}"
faxes = [
    ("Fax 1: pathology, initial only", f"PATHOLOGY REPORT\nPatient: NGUYEN, J.\nDOB: 14/O3/2012\nMedicare No: {m}\nPotassium 6.9 mmol/L HH (3.5-5.2)\n*** CRITICAL RESULT ***"),
    ("Fax 2: same twins, full name + IRN", f"Radiology Report\nName: Liam Nguyen  D.O.B. 14 Mar 2012\nMedicare: {m} (4)\nX-ray wrist: no fracture."),
    ("Fax 3: Jack's name but Liam's IRN", f"Radiology Report\nName: Jack Nguyen  D.O.B. 14 Mar 2012\nMedicare: {m} (4)\nX-ray: normal."),
    ("Fax 4: letter about a non-patient", "Dear Dr Patel,\nRe: Olivia Chen, DOB 06/04/1951, of 7 Other St\nPlan: review in 6 weeks."),
]
names = {p["id"]: f"{p['first']} {p['last']}" for p in fam}
for title, text in faxes:
    o = match.decide(idx, text)
    b = match.baseline_best(idx, text)
    print(f"{title}\n   " + text.replace("\n", " | ")[:120])
    print(f"   always-file-best -> {names.get(b['patient'], '-')}")
    who = names.get(o["patient"], "-")
    print(f"   gated            -> {o['decision']}" + (f" to {who}" if o["decision"] == "AUTO_FILE" else f": {o['reason']}")
          + ("   + URGENT to GP" if o["urgent"] else "") + "\n")
