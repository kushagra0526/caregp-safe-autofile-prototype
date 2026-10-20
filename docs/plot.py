import json
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

a = json.load(open("out/heldout_first_run.json"))["results"]
b = json.load(open("out/heldout_after_fix.json"))["results"]
rows = [("exact name+DOB", a["exact"]), ("always file best", a["best"]), ("gated, first run", a["gated"]), ("gated, after fixes", b["gated"])]
fig, ax = plt.subplots(1, 2, figsize=(11, 4))
col = ["#bbb", "#888", "#2a7", "#7c7"]
ax[0].bar([r[0] for r in rows], [100 * r[1]["auto"] / r[1]["docs"] for r in rows], color=col); ax[0].set_title("% of documents filed with no human")
ax[1].bar([r[0] for r in rows], [1000 * r[1]["misfiled"] / r[1]["docs"] for r in rows], color=col); ax[1].set_title("misfiles per 1,000 documents")
for x in ax: x.tick_params(axis="x", labelsize=8)
fig.suptitle("Held-out: 5,000 synthetic inbound documents, new layouts, 2x OCR noise (15% are not this clinic's patients)")
fig.tight_layout(); fig.savefig("docs/result.png", dpi=110)
