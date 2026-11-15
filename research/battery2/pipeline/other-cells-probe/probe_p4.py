"""Other cells pass 4, per OTHER-CELLS-PASS4.md (commit ead83e0). Reads fields by code only."""
import sys, os, json, re
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import f
from probe import get, jparse, nrm
from probe3 import camb
from probe_p2 import FULL
from kyoto4 import ou_parse, strip_markup

SPENT = {d.lower() for d in """10.1017/s0362502800003862 10.1017/s0362502800005009 10.1017/s0362502800005010 10.1017/s0362502800005034
10.1017/s0362502800004296 10.1017/s0362502800003230 10.1017/s0362502800004284 10.1017/s0362502800003242 10.1017/s0362502800003278
10.1017/s0362502800001012 10.1017/s0362502800003291 10.1017/s0362502800004260 10.1017/s0362502800002212 10.1017/s0362502800000675
10.1017/s0362502800000638 10.1017/s0362502800007082 10.1017/s0362502800007136 10.1017/s0362502800001826 10.1017/s0362502800000687
10.1017/s0362502800007161""".split()}
assert len(SPENT) == 20
BAD = re.compile(r"\bpp\b|\bISBN\b|\bpress\b|\b(19|20)\d\d\.\s|in memoriam|obituary|summary of japanese scholarship|\breview\b", re.I)
KY = "https://corpus.kanji.zinbun.kyoto-u.ac.jp/gitlab/api/v4/projects/10/repository/files/OU{:03d}.txt/raw?ref=main"

def title_match(ct, kt):
    a, b = nrm(strip_markup(ct)), nrm(kt)
    if not a or not b: return False
    if a == b: return True
    return min(len(a), len(b)) >= 15 and (a.startswith(b) or b.startswith(a))

def run():
    q = "https://api.crossref.org/journals/0362-5028/works?rows=100&select=DOI,title,author,issued,volume,page&filter=from-pub-date:1998,until-pub-date:2011"
    st, t, _ = get("ds", q); js = jparse(t) or {}
    items = js.get("message", {}).get("items", [])
    elig = [it for it in items if it.get("author") and it.get("page") and it["DOI"].lower() not in SPENT
            and not BAD.search(strip_markup((it.get("title") or [""])[0]))]
    cands = elig[:8]
    files, ec = [], []
    for i in range(1, 59):
        force_retry = i in (30, 58)
        if force_retry:
            s, tx, n = get("ms", KY.format(i))   # cached failure -> get() retries with force from try 2
        else:
            snap = f.fetch("ms", KY.format(i)); s, tx, n = snap["status"], f.text(snap), 0
        ok = s == 200 and bool(tx) and "security risk" not in tx[:300]
        files.append({"file": f"OU{i:03d}", "status": s, "new_tries": n, "opened": ok})
        if ok:
            for a in ou_parse(tx):
                if a["j"] == "420300": ec.append(dict(a, file=f"OU{i:03d}"))
    ec_years = sorted({int(re.sub(r"\D", "", a["d"])[:4]) for a in ec if a["d"] and re.sub(r"\D", "", a["d"])[:4]})
    rows = []
    for it in cands:
        pii = it["DOI"].split("/")[-1].upper()
        s, tx, n = get("ds", f"https://www.cambridge.org/core/product/identifier/{pii}/type/journal_article")
        A = camb(tx)
        hits = [a for a in ec if a["t"] and title_match(it["title"][0], a["t"])]
        B = {}
        if len(hits) == 1:
            h = hits[0]; B = {"title": h["t"], "author": h["a"][0] if h["a"] else None, "venue": "Early China", "year": h["d"]}
        cy = (it.get("issued", {}).get("date-parts") or [[None]])[0][0]
        r = {"id": it["DOI"], "vol": it.get("volume"), "crossref_year": cy, "year_in_kyoto_range": bool(cy and ec_years and min(ec_years) <= cy <= max(ec_years) + 1),
             "A_status": s, "A_tries": n, "A_full": FULL(A), "A_missing": [k for k in A if not A[k]], "B_hits": len(hits), "B_full": FULL(B), "_A": A, "_B": B}
        if r["A_full"] and r["B_full"]:
            r["title_agree"] = nrm(strip_markup(A["title"])) == nrm(B["title"])
            r["year_agree"] = str(A["year"])[:4] == re.sub(r"\D", "", B["year"])[:4]
        rows.append(r)
    return {"enum_status": st, "enum_total": js.get("message", {}).get("total-results"), "returned": len(items), "eligible": len(elig),
            "files": files, "ec_records": len(ec), "ec_years": ec_years, "rows": rows}

if __name__ == "__main__":
    res = run(); json.dump(res, open("p4_result.json", "w"), ensure_ascii=False, indent=1, default=str); print("done")
