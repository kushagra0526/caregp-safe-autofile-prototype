"""Which patient does this document belong to, and is it safe to file it without a person?

Candidates come from identifiers and names found anywhere in the text (no reliance on labels,
which OCR mangles). Each candidate is scored field by field (Fellegi-Sunter style weights).
AUTO_FILE only if: best score >= T, best beats the runner-up by >= M, and no identifier conflict
(IRN or IHI pointing at someone else). Otherwise REVIEW with the reason.
"""
import re
from . import ids, clinic

T, M = 9.0, 4.0
MON = {m.lower(): i + 1 for i, m in enumerate("jan feb mar apr may jun jul aug sep oct nov dec".split())}
CRIT = re.compile(r"critical|\b(hh|ll)\b|phoned to|urgent|panic|call(ed)? (the )?(gp|doctor)|immediate", re.I)


def edit1(a, b):
    if a == b:
        return True
    if abs(len(a) - len(b)) > 1:
        return False
    if len(a) == len(b):
        return sum(x != y for x, y in zip(a, b)) <= 1
    if len(a) > len(b):
        a, b = b, a
    return any(a == b[:i] + b[i + 1:] for i in range(len(b)))


def digit_view(text):
    """Map OCR look-alikes to digits when they sit next to a digit (0/O, 1/l, 5/S, 8/B)."""
    out = list(text)
    for i, c in enumerate(text):
        if c in ids.OCR and ((i > 0 and text[i - 1].isdigit()) or (i + 1 < len(text) and text[i + 1].isdigit())):
            out[i] = ids.OCR[c]
    return "".join(out)


def dates(t):
    found = set()
    for d, m, y in re.findall(r"\b(\d{1,2})[/.\-](\d{1,2})[/.\-](\d{2,4})\b", t):
        found |= _ymd(y, m, d)
    for y, m, d in re.findall(r"\b(\d{4})-(\d{2})-(\d{2})\b", t):
        found |= _ymd(y, m, d)
    for d, mon, y in re.findall(r"\b(\d{1,2})\s+([A-Za-z]{3})[a-z]*\.?\s+(\d{4})\b", t):
        if mon.lower() in MON:
            found |= _ymd(y, MON[mon.lower()], d)
    for mon, d, y in re.findall(r"\b([A-Za-z]{3})[a-z]*\.?\s+(\d{1,2}),?\s+(\d{4})\b", t):
        if mon.lower() in MON:
            found |= _ymd(y, MON[mon.lower()], d)
    return found


def _ymd(y, m, d):
    y, m, d = int(y), int(m), int(d)
    ys = [y] if y > 99 else [1900 + y, 2000 + y]
    return {(yy, m, d) for yy in ys if 1 <= m <= 12 and 1 <= d <= 31}


def extract(text):
    t = digit_view(text)
    med = []
    for a, b, c, irn in re.findall(r"(\d{4})\s?(\d{5})\s?(\d)(?:\s*\((\d)\))?", t):
        num = a + b + c
        med.append((num, ids.medicare_ok(num), int(irn) if irn else None))
    ihi = [x for x in re.findall(r"\b(8003\d{12})\b", t)]
    words = [w.lower() for w in re.findall(r"[A-Za-z]+", text)]
    crit = bool(CRIT.search(text))
    return dict(dates=dates(t), medicare=med, ihi=ihi, words=words, critical=crit)


class Index:
    def __init__(self, patients):
        self.p = {p["id"]: p for p in patients}
        self.by_last, self.by_dob, self.by_card = {}, {}, {}
        for p in patients:
            for s in {p["last"].lower(), (p["prev_last"] or "").lower()} - {""}:
                self.by_last.setdefault(s, []).append(p["id"])
            self.by_dob.setdefault(p["dob"], []).append(p["id"])
            self.by_card.setdefault(p["medicare"], []).append(p["id"])

    def candidates(self, f):
        c = set()
        for w in set(f["words"]):
            for s in self.by_last:
                if len(w) >= 3 and edit1(w, s):
                    c.update(self.by_last[s])
        for d in f["dates"]:
            c.update(self.by_dob.get(d, []))
            c.update(self.by_dob.get((d[0], d[2], d[1]), []))
        for num, ok, _ in f["medicare"]:
            c.update(self.by_card.get(num, []))
        return c


def score(p, f):
    s, why, conflict = 0.0, [], None
    words = f["words"]
    lasts = {p["last"].lower(), (p["prev_last"] or "").lower()} - {""}
    if lasts & set(words):
        s += 3
    elif any(edit1(w, l) for w in words for l in lasts if len(w) >= 3):
        s += 2
    else:
        s -= 3; why.append("surname not found")
    fn = p["first"].lower()
    nicks = [n.lower() for n in clinic.NICK.get(p["first"], [])]
    if fn in words:
        s += 3
    elif any(n in words for n in nicks):
        s += 1.5
    elif any(edit1(w, fn) for w in words if len(w) >= 3):
        s += 2
    elif fn[0] in words:                                  # an initial ("J. Smith")
        s += 0.5
    else:
        s -= 3; why.append("first name differs")
    if f["dates"]:
        y, m, d = p["dob"]
        if (y, m, d) in f["dates"]:
            s += 5
        elif (y, d, m) in f["dates"]:
            s += 2; why.append("DOB day/month swapped")
        else:
            s -= 5; why.append("DOB differs")
    for num, ok, irn in f["medicare"]:
        if ok and num == p["medicare"]:
            s += 6
            if irn is not None:
                if irn == p["irn"]:
                    s += 4
                else:
                    s -= 8; conflict = f"Medicare IRN {irn} is another person on this card"
        elif ok:
            s -= 6; why.append("valid Medicare number for a different card")
        elif sum(a != b for a, b in zip(num, p["medicare"])) <= 1:
            s += 2; why.append("Medicare number fails check digit (1 digit off)")
    for x in f["ihi"]:
        if ids.ihi_ok(x):
            if x == p["ihi"]:
                s += 10
            else:
                s -= 10; conflict = "IHI belongs to someone else"
    num, street = p["address"].split()[0], p["address"].split()[1].lower()
    if street in words and num in re.findall(r"\d+", " ".join(words) + " " + num):
        s += 1
    return s, why, conflict


def decide(idx, text):
    f = extract(text)
    scored = sorted(((score(idx.p[c], f), c) for c in idx.candidates(f)), key=lambda x: -x[0][0])
    urgent = f["critical"]
    if not scored or scored[0][0][0] < 4:
        return dict(decision="REVIEW", patient=None, reason="no matching patient in this clinic", urgent=urgent, best=None)
    (s1, why1, conf1), best = scored[0]
    s2 = scored[1][0][0] if len(scored) > 1 else -99
    if conf1:
        return dict(decision="REVIEW", patient=best, reason=conf1, urgent=urgent, best=best)
    if s1 < T:
        return dict(decision="REVIEW", patient=best, reason=f"weak match ({s1:.1f}): " + "; ".join(why1), urgent=urgent, best=best)
    if s1 - s2 < M:
        other = idx.p[scored[1][1]]
        return dict(decision="REVIEW", patient=best, urgent=urgent, best=best,
                    reason=f"two close candidates: {idx.p[best]['first']} vs {other['first']} {other['last']} ({s1:.1f} vs {s2:.1f})")
    return dict(decision="AUTO_FILE", patient=best, reason=f"score {s1:.1f}, next {s2:.1f}", urgent=urgent, best=best)


def baseline_exact(idx, text):
    """File only if exactly one patient's full first+last name and DOB appear exactly."""
    f = extract(text)
    hits = [p for p in idx.p.values() if p["first"].lower() in f["words"] and p["last"].lower() in f["words"] and p["dob"] in f["dates"]]
    return dict(decision="AUTO_FILE" if len(hits) == 1 else "REVIEW", patient=hits[0]["id"] if len(hits) == 1 else None,
                urgent=f["critical"])


def baseline_best(idx, text):
    """Always file to the highest-scoring candidate."""
    f = extract(text)
    scored = sorted(((score(idx.p[c], f)[0], c) for c in idx.candidates(f)), reverse=True)
    return dict(decision="AUTO_FILE" if scored else "REVIEW", patient=scored[0][1] if scored else None, urgent=f["critical"])
