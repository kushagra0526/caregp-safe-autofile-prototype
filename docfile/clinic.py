"""A synthetic GP clinic patient index with the hard cases: households on one Medicare card,
twins, father/son with the same name, common surnames, married-name changes. No real people."""
import random
from . import ids

SURNAMES = ("Smith Nguyen Williams Brown Jones Wilson Taylor Singh Chen Li Patel Kelly Martin Anderson White Thompson "
            "Walker Harris Lee Ryan Tran Wang Robinson King Wright Murphy Young Mitchell Campbell Clarke").split()
MALE = "James William Jack Thomas Oliver Noah Michael Robert Christopher Daniel Alexander Liam Ethan Lucas Benjamin Jonathan".split()
FEMALE = "Charlotte Olivia Amelia Isla Mia Ava Grace Chloe Emily Sophie Elizabeth Margaret Katherine Jennifer Sarah Hannah".split()
NICK = {"William": ["Bill", "Will"], "Robert": ["Bob", "Rob"], "Michael": ["Mike"], "Thomas": ["Tom"], "James": ["Jim", "Jimmy"],
        "Christopher": ["Chris"], "Alexander": ["Alex"], "Benjamin": ["Ben"], "Jonathan": ["Jon"], "Daniel": ["Dan"],
        "Elizabeth": ["Liz", "Beth"], "Margaret": ["Maggie", "Meg"], "Katherine": ["Kate", "Katie"], "Jennifer": ["Jen"],
        "Charlotte": ["Lottie"], "Olivia": ["Liv"], "Samuel": ["Sam"]}
STREETS = "George Pitt Elizabeth King Oxford Victoria Church High Railway Park Station Bridge Queen Albert".split()
SUFFIX = ["St", "Rd", "Ave", "Pde", "Cres"]


def make(seed, n_households=700):
    r = random.Random(seed)
    pts = []
    for h in range(n_households):
        sur = r.choice(SURNAMES)
        first8 = str(r.randint(2, 6)) + "".join(str(r.randint(0, 9)) for _ in range(7))
        card = first8 + ids.medicare_check(first8) + str(r.randint(1, 5))
        addr = f"{r.randint(1, 240)} {r.choice(STREETS)} {r.choice(SUFFIX)}"
        members = []
        size = r.choices([1, 2, 3, 4, 5], [30, 30, 18, 15, 7])[0]
        y0 = r.randint(1945, 1995)
        for k in range(size):
            if k < 2:
                sex = "M" if (k == 0) ^ (r.random() < 0.5) else "F"
                yob = y0 + r.randint(-3, 3)
            else:
                sex = r.choice("MF")
                yob = y0 + r.randint(25, 35)
            first = r.choice(MALE if sex == "M" else FEMALE)
            dob = (yob, r.randint(1, 12), r.randint(1, 28))
            prev = r.choice(SURNAMES) if (k == 1 and sex == "F" and r.random() < 0.4) else None
            members.append(dict(first=first, last=sur, sex=sex, dob=dob, prev_last=prev))
        kids = [m for m in members[2:]]
        if len(kids) >= 2 and r.random() < 0.25:                        # twins: same DOB
            kids[1]["dob"] = kids[0]["dob"]
            if kids[1]["first"] == kids[0]["first"]:
                kids[1]["first"] = r.choice(MALE if kids[1]["sex"] == "M" else FEMALE)
        if kids and members[0]["sex"] == "M" and r.random() < 0.12:     # son named after father
            for m in kids:
                if m["sex"] == "M":
                    m["first"] = members[0]["first"]
                    break
        for irn, m in enumerate(members, 1):
            body = "800360" + "".join(str(r.randint(0, 9)) for _ in range(9))
            pts.append(dict(id=f"P{len(pts) + 1:05d}", **m, medicare=card, irn=irn, address=addr,
                            ihi=body + ids.luhn_digit(body)))
    return pts
