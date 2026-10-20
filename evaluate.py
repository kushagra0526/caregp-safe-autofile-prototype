"""Auto-file vs review on synthetic clinic inboxes.  python evaluate.py [dev|heldout] [out.json]"""
import json, sys
from docfile import clinic, docs, match

METHODS = {"exact": match.baseline_exact, "best": match.baseline_best, "gated": match.decide}


def run(which):
    if which == "heldout":
        h = json.load(open("heldout/config.json"))
        seeds, cfg = range(h["seeds"][0], h["seeds"][1] + 1), h["cfg"]
    else:
        seeds, cfg = range(1, 6), None
    res = {m: dict(docs=0, auto=0, misfiled=0, foreign_auto=0, urgent=0, urgent_found=0) for m in METHODS}
    reasons = {}
    for s in seeds:
        pts = clinic.make(s)
        idx = match.Index(pts)
        for d in docs.make(s * 31, pts, 1000, cfg):
            for m, fn in METHODS.items():
                o = fn(idx, d["text"])
                r = res[m]
                r["docs"] += 1
                if o["decision"] == "AUTO_FILE":
                    r["auto"] += 1
                    if o["patient"] != d["truth"]:
                        r["misfiled"] += 1
                        r["foreign_auto"] += d["truth"] is None
                if d["critical"]:
                    r["urgent"] += 1
                    r["urgent_found"] += o["urgent"]
                if m == "gated" and o["decision"] == "REVIEW":
                    k = o["reason"].split(":")[0].split("(")[0].strip()
                    reasons[k] = reasons.get(k, 0) + 1
    return dict(set=which, results=res, review_reasons=reasons)


if __name__ == "__main__":
    which = sys.argv[1] if len(sys.argv) > 1 else "dev"
    r = run(which)
    n = r["results"]["gated"]["docs"]
    print(f"{which}: {n} inbound documents over {n // 1000} synthetic clinics")
    names = {"exact": "exact name + DOB", "best": "best fuzzy match, always file", "gated": "scored + gated (this)"}
    for m, x in r["results"].items():
        print(f"  {names[m]:30s} auto-filed {100 * x['auto'] / x['docs']:5.1f}%   misfiled {x['misfiled']:4d} "
              f"({1000 * x['misfiled'] / x['docs']:.1f} per 1,000 docs; {x['foreign_auto']} not our patient)   urgent flagged {x['urgent_found']}/{x['urgent']}")
    print("  review reasons:", r["review_reasons"])
    if len(sys.argv) > 2:
        json.dump(r, open(sys.argv[2], "w"), indent=1)
