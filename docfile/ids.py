"""Australian patient identifiers: Medicare card number (check digit) and IHI (Luhn)."""
import re

OCR = {"O": "0", "o": "0", "D": "0", "I": "1", "l": "1", "|": "1", "S": "5", "s": "5", "B": "8", "Z": "2", "G": "6"}
W = (1, 3, 7, 9, 1, 3, 7, 9)


def medicare_ok(d10):
    """10 digits: first in 2-6, digit 9 = weighted sum of first 8 mod 10, digit 10 = issue number."""
    if not re.fullmatch(r"[2-6]\d{9}", d10 or ""):
        return False
    return sum(int(a) * w for a, w in zip(d10[:8], W)) % 10 == int(d10[8])


def medicare_check(first8):
    return str(sum(int(a) * w for a, w in zip(first8, W)) % 10)


def luhn_ok(s):
    if not re.fullmatch(r"\d+", s or ""):
        return False
    tot = 0
    for i, ch in enumerate(reversed(s)):
        d = int(ch)
        if i % 2 == 1:
            d = d * 2 - 9 if d > 4 else d * 2
        tot += d
    return tot % 10 == 0


def ihi_ok(s):
    return bool(s) and len(s) == 16 and s.startswith("800360") and luhn_ok(s)


def luhn_digit(body):
    for d in "0123456789":
        if luhn_ok(body + d):
            return d


def clean_number(raw, n):
    """Strip spaces/dashes; map OCR look-alikes to digits. Returns the digit string (maybe invalid)."""
    s = "".join(OCR.get(c, c) for c in (raw or "") if c not in " -/.")
    return s if len(s) == n and s.isdigit() else None
