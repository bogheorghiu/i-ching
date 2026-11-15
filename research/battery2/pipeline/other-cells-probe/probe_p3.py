"""Other cells pass 3, per OTHER-CELLS-PASS3.md (commit 2130e7a). Reads fields by code only.
Run from the working folder that holds snap/ (f.py writes there)."""
import sys, os, json, re, unicodedata
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import f
from probe import get, jparse, nrm
from probe3 import camb
from probe_p2 import SPENT, FULL, mfields, msub, marc, same_isbn, cinii_list, cinii_rec

KY = "https://corpus.kanji.zinbun.kyoto-u.ac.jp/gitlab/api/v4/projects/10/repository/files/OU{:03d}.txt/raw?ref=main"

def ou_parse(t):
    """issue blocks -> articles: list of dicts {j, d, t, a}"""
    t = unicodedata.normalize("NFKC", t)
    arts, blk, art, last = [], {}, None, None
    for line in t.splitlines():
        s = line.strip()
        if not s or s.startswith("```"): continue
        if re.fullmatch(r"[A-Z]\d{6}", s):
            blk, art, last = {}, None, None; continue
        if re.fullmatch(r"\d{8}", s):
            art = {"j": blk.get("j"), "d": blk.get("d"), "t": None, "a": []}; arts.append(art); last = None; continue
        m = re.match(r"\$([A-Za-z])(.*)$", s)
        if m:
            k, v = m.group(1), m.group(2).strip()
            if art is None:
                if k in ("j", "d"): blk[k] = v
                last = None
            else:
                if k == "t": art["t"] = v; last = "t"
                elif k == "a": art["a"].append(v); last = "a"
                else: last = None
            continue
        if art is not None and last == "t": art["t"] += " " + s
        elif art is not None and last == "a" and art["a"]: art["a"][-1] += " " + s
    return arts

def title_match(ct, kt):
    a, b = nrm(ct), nrm(kt)
    if not a or not b: return False
    if a == b: return True
    short = min(len(a), len(b))
    return short >= 15 and (a.startswith(b) or b.startswith(a))

def e_kyoto():
    q = "https://api.crossref.org/journals/0362-5028/works?rows=40&select=DOI,title,author,issued,volume,page&filter=from-pub-date:2001,until-pub-date:2009"
    st, t, _ = get("ds", q); js = jparse(t) or {}
    items = js.get("message", {}).get("items", [])
    elig = [it for it in items if it.get("author") and it.get("page") and not re.search(r"\bpp\.|\bISBN\b", (it.get("title") or [""])[0], re.I)]
    cands = elig[:8]
    rows = []
    for it in cands:
        pii = it["DOI"].split("/")[-1].upper()
        s, tx, n = get("ds", f"https://www.cambridge.org/core/product/identifier/{pii}/type/journal_article")
        A = camb(tx)
        rows.append({"id": it["DOI"], "vol": it.get("volume"), "crossref_title": it["title"][0], "crossref_year": (it.get("issued", {}).get("date-parts") or [[None]])[0][0],
                     "A_status": s, "A_tries": n, "A_full": FULL(A), "A_missing": [k for k in A if not A[k]], "_A": A, "hits": []})
    files, blocks = [], set()
    for i in range(1, 59):
        if all(r["hits"] for r in rows): break
        s, tx, n = get("ms", KY.format(i))
        ok = s == 200 and bool(tx) and "security risk" not in tx[:300]
        files.append({"file": f"OU{i:03d}", "status": s, "tries": n, "len": len(tx), "opened": ok})
        if not ok: continue
        for a in ou_parse(tx):
            if a["j"] != "420300": continue
            blocks.add((f"OU{i:03d}", a["d"]))
            for r in rows:
                if a["t"] and title_match(r["crossref_title"], a["t"]):
                    r["hits"].append({"file": f"OU{i:03d}", "t": a["t"], "a": a["a"][:1], "d": a["d"]})
    for r in rows:
        B = {}
        if len(r["hits"]) == 1:
            h = r["hits"][0]; B = {"title": h["t"], "author": h["a"][0] if h["a"] else None, "venue": "Early China", "year": h["d"]}
        r["B_hits"] = len(r["hits"]); r["B_full"] = FULL(B); r["_B"] = B
        if r["A_full"] and r["B_full"]:
            r["title_agree"] = nrm(r["_A"]["title"]) == nrm(B["title"])
            r["year_agree"] = str(r["_A"]["year"])[:4] == re.sub(r"\D", "", B["year"])[:4]
    return {"enum_status": st, "enum_total": js.get("message", {}).get("total-results"), "returned": len(items), "eligible": len(elig),
            "files": files, "ec_blocks": sorted(blocks), "rows": rows}

def n_en_776():
    lists = ["subject=%E6%98%93%E7%B5%8C&lang=eng&format=json&count=50", "subject=Yi%20jing&lang=eng&format=json&count=50",
             "subject=I%20ching&lang=eng&format=json&count=50", "clas=123.1&lang=eng&format=json&count=50"]
    seen, elig, enums = set(), [], []
    for q in lists:
        meta, items = cinii_list(q); enums.append(meta)
        for ncid, isbn in items:
            if ncid in seen: continue
            seen.add(ncid)
            if isbn and ncid not in SPENT: elig.append((ncid, isbn))
    cands = elig[8:16]
    rows = []
    for ncid, isbn in cands:
        sa, na, A = cinii_rec("ds", ncid)
        sk, tk, nk = get("ms", f"https://sru.k10plus.de/opac-de-627?version=1.1&operation=searchRetrieve&query=pica.isb%3D{isbn}&maximumRecords=1&recordSchema=marcxml")
        K = marc(tk); z776 = [v for fl in mfields(tk, "776") for v in msub(fl, "z")]
        nrec = re.search(r"numberOfRecords>(\d+)", tk)
        same020 = same_isbn(isbn, K["isbns"]); same776 = same_isbn(isbn, z776)
        r = {"id": ncid, "isbn": isbn, "A_status": sa, "B_status": sk, "B_tries": nk, "B_numberOfRecords": nrec.group(1) if nrec else None,
             "A_full": FULL(A), "B_fields_present": [k for k in ("title", "author", "venue", "year") if K.get(k)],
             "same_020": same020, "same_776": same776, "B_full": FULL(K) and (same020 or same776), "B_full_020only": FULL(K) and same020, "_A": A, "_K": K}
        if r["A_full"] and r["B_full"]:
            x, y = nrm(A["title"].split(" : ")[0]), nrm(K["title"])
            r["title_agree"] = bool(x and y and (x == y or x.startswith(y) or y.startswith(x)))
            r["year_agree"] = re.sub(r"\D", "", str(A["year"]))[:4] == re.sub(r"\D", "", K["year"])[:4]
        rows.append(r)
    return {"enumerations": enums, "union": len(seen), "eligible": len(elig), "rows": rows}

if __name__ == "__main__":
    part = sys.argv[1]
    res = {"books": lambda: {"N-en/K776": n_en_776()}, "articles": lambda: {"E-kyoto": e_kyoto()}}[part]()
    json.dump(res, open(f"p3_{part}_result.json", "w"), ensure_ascii=False, indent=1, default=str)
    print("done", part)
