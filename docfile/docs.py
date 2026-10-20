"""Inbound clinical documents (fax / scan / email text) for a clinic, with OCR noise and the
ways real documents identify patients. ~10% belong to someone who is NOT a patient here."""
import random
from . import clinic, ids

MONTHS = "Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec".split()
OCR_SWAP = {"0": "O", "1": "l", "5": "S", "8": "B", "o": "0", "l": "1", "e": "c", "m": "rn", "a": "o"}

DEV = dict(templates=["path", "rad", "letter", "discharge"], ocr=0.02, nick=0.15, initial=0.10, irn_missing=0.30,
           medicare_missing=0.20, swap_dm=0.02, foreign=0.10, critical=0.05, dob_fmt=["dmy", "dmy_text", "iso", "dmy_short"],
           crit_phrases=["*** CRITICAL RESULT ***", "Phoned to doctor", "URGENT - please review today"],
           flags=["HH", "LL"])


def noisy(r, s, p):
    return "".join(OCR_SWAP.get(c, c) if r.random() < p and c in OCR_SWAP else c for c in s)


def fmt_dob(r, dob, style, swap):
    y, m, d = dob
    if swap and d <= 12:
        m, d = d, m
    return {"dmy": f"{d:02d}/{m:02d}/{y}", "dmy_text": f"{d} {MONTHS[m - 1]} {y}", "iso": f"{y}-{m:02d}-{d:02d}",
            "dmy_short": f"{d}/{m}/{str(y)[2:]}", "mdy_text": f"{MONTHS[m - 1]} {d}, {y}", "dotted": f"{d:02d}.{m:02d}.{y}"}[style]


def render(r, p, cfg, template):
    first = p["first"]
    if r.random() < cfg["nick"] and first in clinic.NICK:
        first = r.choice(clinic.NICK[first])
    last = p["prev_last"] if p["prev_last"] and r.random() < 0.3 else p["last"]
    name = f"{first[0]}. {last}" if r.random() < cfg["initial"] else f"{first} {last}"
    if r.random() < 0.4:
        name = f"{last.upper()}, {first}"
    dob = fmt_dob(r, p["dob"], r.choice(cfg["dob_fmt"]), r.random() < cfg["swap_dm"])
    med = None if r.random() < cfg["medicare_missing"] else p["medicare"]
    irn = None if (med is None or r.random() < cfg["irn_missing"]) else p["irn"]
    crit = template in ("path", "pathx") and r.random() < cfg["critical"]
    flag = r.choice(cfg["flags"])
    res = (f"Potassium 6.9 mmol/L {flag} (3.5-5.2)\n{r.choice(cfg['crit_phrases'])}" if crit
           else f"Potassium 4.{r.randint(0, 9)} mmol/L (3.5-5.2)\nHb {r.randint(120, 160)} g/L")
    medtxt = (f"{med[:4]} {med[4:9]} {med[9]}" + (f" ({irn})" if irn else "")) if med else ""
    T = {
        "path": f"PATHOLOGY REPORT\nPatient: {name}\nDOB: {dob}   Sex: {p['sex']}\nMedicare No: {medtxt}\nAddress: {p['address']}\n{res}",
        "rad": f"Radiology Report\nName: {name}  D.O.B. {dob}\nMedicare: {medtxt}\nCT chest: no acute findings.",
        "letter": f"Dear Dr Patel,\nRe: {name}, DOB {dob}, of {p['address']}\nThank you for referring this patient. Plan: review in 6 weeks.",
        "discharge": f"DISCHARGE SUMMARY\nPatient name: {name}\nDate of birth: {dob}\nIHI: {p['ihi']}\nMedicare number: {medtxt}\nDischarged home.",
        # held-out templates
        "pathx": f"Lab result | Pt {name} | born {dob} | Medicare card {medtxt} | {res.replace(chr(10), ' | ')}",
        "email": f"Hi team, attaching results for our mutual patient {name} (DOB {dob}). Medicare {medtxt}. Regards, Dr Wu",
        "fax_cover": f"FAX COVER SHEET - 3 pages\nRE PATIENT: {name}\nD/O/B: {dob}\nMC#: {medtxt}  IHI {p['ihi'] if r.random() < 0.5 else ''}\nPlease file.",
    }
    return noisy(r, T[template], cfg["ocr"]), crit


def make(seed, patients, n, cfg=None):
    c = {**DEV, **(cfg or {})}
    r = random.Random(seed)
    out = []
    for i in range(n):
        tpl = r.choice(c["templates"])
        if r.random() < c["foreign"]:
            # someone not registered here: often shares a surname (or a whole name) with a patient
            base = dict(r.choice(patients))
            base["dob"] = (base["dob"][0] + r.choice([-2, -1, 1, 3]), base["dob"][1], base["dob"][2])
            first8 = str(r.randint(2, 6)) + "".join(str(r.randint(0, 9)) for _ in range(7))
            base.update(medicare=first8 + ids.medicare_check(first8) + "1", irn=1, ihi="", id=None, prev_last=None,
                        address=f"{r.randint(1, 99)} Other St")
            if r.random() < 0.5:
                base["first"] = r.choice(clinic.MALE + clinic.FEMALE)
            p = base
        else:
            p = r.choice(patients)
        text, crit = render(r, p, c, tpl)
        out.append(dict(id=f"D{i:05d}", text=text, truth=p["id"], critical=crit, template=tpl))
    return out
