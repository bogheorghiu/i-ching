"""Other cells pass 2, per OTHER-CELLS-PASS2.md (commit 6b13e3a + section 5). Reads fields by code only.
Run from the working folder that holds snap/ (f.py writes there)."""
import sys, os, json, re, csv, io, concurrent.futures as cf
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import f
from probe import get, jparse, nrm
from probe3 import camb, CNKI_SELF

SPENT = set("""BA81633630 BD20731693 BD13182686 BB14892784 BB08537573 BA90059004 BA84281380 BA84279403
BA53798596 BN14267128 BN13011082 BN12710982 BN12370250 BN11489597 BN0972278X BN08503827 BA59890988 BA14308857
BA10720382 BA66883097 BA65238668 BA64022299 BA6333309X BA63316330 BA62363109 BA62362106 BA6222256X BN08502438
BN08081759 BN07741626 BN07534574 BN07196314 BN07114127 BN06773809 BN04345305 BA56630131 BB04075567""".split())
assert len(SPENT) == 37
FULL = lambda d: all(d.get(k) for k in ("title", "author", "venue", "year"))

# ---------- MARC (strict: no 880), namespace prefix allowed ----------
def mfields(t, tag): return re.findall(rf'<(?:\w+:)?datafield\s*tag="{tag}".*?</(?:\w+:)?datafield>', t, re.S)
def msub(fl, code): return [re.sub(r"\s+", " ", x).strip() for x in re.findall(rf'<(?:\w+:)?subfield\s*code="{code}">(.*?)</(?:\w+:)?subfield>', fl, re.S)]
def mfirst(t, tags, code):
    for tg in tags:
        for fl in mfields(t, tg):
            v = msub(fl, code)
            if v and v[0]: return v[0]
    return None
def marc(t):
    return {"title": mfirst(t, ["245"], "a"), "author": mfirst(t, ["100", "700"], "a") or mfirst(t, ["245"], "c"),
            "venue": mfirst(t, ["264", "260"], "b"), "year": mfirst(t, ["264", "260"], "c"),
            "isbns": [v for fl in mfields(t, "020") for v in msub(fl, "a")]}
def isbn_forms(i):
    d = re.sub(r"[^0-9Xx]", "", i).upper(); out = {d}
    if len(d) == 10:
        b = "978" + d[:9]; s = sum(int(c) * (1 if k % 2 == 0 else 3) for k, c in enumerate(b)); out.add(b + str((10 - s % 10) % 10))
    if len(d) == 13 and d.startswith("978"):
        b = d[3:12]; s = sum(int(c) * (10 - k) for k, c in enumerate(b)); r = (11 - s % 11) % 11; out.add(b + ("X" if r == 10 else str(r)))
    return out
def same_isbn(asked, vals):
    forms = isbn_forms(asked)
    return any(any(fm in re.sub(r"[^0-9Xx]", "", v).upper() for fm in forms) for v in vals)

# ---------- CiNii ----------
def cinii_list(q):
    st, t, _ = get("ds", "https://ci.nii.ac.jp/books/opensearch/search?" + q); js = jparse(t)
    g = (js or {}).get("@graph", [{}])[0] if js else {}
    out = []
    for it in g.get("items", []):
        isbns = [p["@id"].split(":")[-1] for p in it.get("dcterms:hasPart", []) if "isbn" in p.get("@id", "")]
        out.append((it["@id"].rsplit("/", 1)[-1], isbns[0] if isbns else None))
    return {"q": q, "status": st, "total": g.get("opensearch:totalResults"), "returned": len(out)}, out
def cinii_rec(which, ncid):
    s, t, n = get(which, f"https://ci.nii.ac.jp/ncid/{ncid}.json"); j = jparse(t)
    g = (j or {}).get("@graph", [{}])[0] if j else {}
    A = {"title": (g.get("dc:title") or [{}])[0].get("@value") if g.get("dc:title") else None, "author": g.get("dc:creator"),
         "venue": (g.get("dc:publisher") or [{}])[0].get("@value") if g.get("dc:publisher") else None, "year": g.get("dc:date")}
    return s, n, A

def book_arms(cell, lists):
    enums, seen, elig = [], set(), []
    for q in lists:
        meta, items = cinii_list(q); enums.append(meta)
        for ncid, isbn in items:
            if ncid in seen: continue
            seen.add(ncid)
            if isbn and ncid not in SPENT: elig.append((ncid, isbn))
    cands = elig[:8]
    def one(c):
        ncid, isbn = c
        r = {"id": ncid, "isbn": isbn}
        sa, na, A = cinii_rec("ds", ncid)
        sk, tk, nk = get("ms", f"https://sru.k10plus.de/opac-de-627?version=1.1&operation=searchRetrieve&query=pica.isb%3D{isbn}&maximumRecords=1&recordSchema=marcxml")
        K = marc(tk)
        sa2, na2, A2 = cinii_rec("ms", ncid)
        sh, th, nh = get("ds", f"https://catalog.hathitrust.org/api/volumes/full/isbn/{re.sub(r'[^0-9Xx]','',isbn)}.json")
        hj = jparse(th) or {}; recs = list((hj.get("records") or {}).values()) if isinstance(hj, dict) else []
        H = marc(recs[0].get("marc-xml", "")) if recs else marc("")
        for tag, a, b, sts in (("K", A, K, (sa, sk, nk)), ("H", A2, H, (sa2, sh, nh))):
            bfull = FULL(b) and same_isbn(isbn, b["isbns"])
            row = {"A_status": sts[0], "B_status": sts[1], "B_tries": sts[2], "A_full": FULL(a), "B_full": bfull,
                   "B_fields_present": [k for k in ("title", "author", "venue", "year") if b.get(k)], "B_isbn_match": same_isbn(isbn, b["isbns"]),
                   "B_isbns": b["isbns"][:4], "B_found": bool(b["title"])}
            if FULL(a) and bfull:
                row["title_agree"] = (lambda x, y: bool(x and y and (x == y or x.startswith(y) or y.startswith(x))))(nrm(a["title"].split(" : ")[0]), nrm(b["title"]))
                row["year_agree"] = re.sub(r"\D", "", str(a["year"]))[:4] == re.sub(r"\D", "", b["year"])[:4]
            r[tag] = row
        r["_A"], r["_K"], r["_H"] = A, K, H
        return r
    with cf.ThreadPoolExecutor(4) as ex: rows = list(ex.map(one, cands))
    return {"cell": cell, "enumerations": enums, "union": len(seen), "eligible": len(elig), "rows": rows}

# ---------- Early China ----------
NCL = "https://www.ncl.edu.tw/OpenDataFile/0Q162567915924642807/47140e1f-36d1-405e-b6bb-a98e6c4d69d7"
def ncl_table():
    s, t, n = get("ms", NCL)
    body = re.sub(r"^```\w*\n|\n```\s*$", "", t.strip())
    rows = list(csv.reader(io.StringIO(body)))
    hdr = rows[0] if rows else []
    ok = all(any(h.strip().lstrip("﻿") == c for h in hdr) for c in ("篇名", "刊名", "著者", "出版年"))
    recs = [dict(zip([h.strip().lstrip("﻿") for h in hdr], r)) for r in rows[1:]] if ok else []
    return {"status": s, "tries": n, "len": len(t), "header": hdr[:12], "parsed": ok, "rows": len(recs),
            "dots_lines": sum(1 for l in t.splitlines() if l.strip() == "...")}, recs

def early_china():
    q = "https://api.crossref.org/journals/0362-5028/works?rows=40&select=DOI,title,author,issued,volume,page&filter=from-pub-date:1996,until-pub-date:2000"
    st, t, _ = get("ds", q); js = jparse(t) or {}
    items = js.get("message", {}).get("items", [])
    elig = [it for it in items if it.get("author") and it.get("page")]
    meta, recs = ncl_table()
    ec = [r for r in recs if "earlychina" in nrm(r.get("刊名"))]
    meta["early_china_rows"] = len(ec)
    rows = []
    for it in elig[:8]:
        pii = it["DOI"].split("/")[-1].upper()
        s, tx, n = get("ds", f"https://www.cambridge.org/core/product/identifier/{pii}/type/journal_article")
        A = camb(tx); ct = nrm(it["title"][0])
        hits = [r for r in ec if nrm(r.get("篇名")) and (nrm(r["篇名"]) == ct or ct.startswith(nrm(r["篇名"])) or nrm(r["篇名"]).startswith(ct))]
        B = hits[0] if len(hits) == 1 else {}
        Bd = {"title": B.get("篇名"), "author": B.get("著者"), "venue": B.get("刊名"), "year": B.get("出版年")}
        row = {"id": it["DOI"], "vol": it.get("volume"), "A_status": s, "A_tries": n, "A_full": FULL(A), "A_missing": [k for k in A if not A[k]],
               "B_hits": len(hits), "B_full": FULL(Bd), "_A": A, "_B": Bd}
        if row["A_full"] and row["B_full"]:
            row["title_agree"] = nrm(A["title"]) == nrm(Bd["title"]); row["year_agree"] = str(A["year"])[:4] == re.sub(r"\D", "", Bd["year"])[:4]
        rows.append(row)
    return {"enum_status": st, "enum_total": js.get("message", {}).get("total-results"), "returned": len(items), "eligible": len(elig), "ncl": meta, "rows": rows}

def kyoto_gate():
    B = "https://corpus.kanji.zinbun.kyoto-u.ac.jp/gitlab/api/v4/projects"
    out = []
    for pid, name in ((17, "JOURNAL1.txt"), (17, "RUI001.txt"), (10, "CHU001.txt"), (15, "09journals.txt"), (14, "journal2.txt"), (14, "rjnl.txt")):
        s, t, n = get("ms", f"{B}/{pid}/repository/files/{name}/raw?ref=main")
        whole = s == 200 and len(t) > 1024 and "security risk" not in t[:300] and not any(l.strip() == "..." for l in t.splitlines())
        out.append({"project": pid, "file": name, "status": s, "tries": n, "len": len(t), "whole": whole, "head": t[:300] if whole else ""})
    return out

def c_old():
    rows, enums = [], []
    for y, i in ((1996, 1), (1998, 1)):
        s, t, _ = get("ds", f"https://www.cnki.com.cn/Journal/F-F5-ZYJY-{y}-{i:02d}.htm")
        enums.append({"issue": f"{y}-{i:02d}", "status": s, "toc_lines": len(re.findall(r"^.+\|.+;\s*$", t, re.M))})
        for nn in range(1, 5):
            aid = f"ZYJY{y}{i:02d}0{nn:02d}"
            s2, tx, n = get("ds", f"https://www.cnki.com.cn/Article/CJFDTotal-{aid}.htm")
            h1 = re.search(r"^#\s+(.+)$", tx, re.M); sim = tx.find("相似文献")
            m = CNKI_SELF.search(tx[sim:].replace("|", "\n")) if sim >= 0 else None
            parts = [x.strip() for x in m.group(1).split(";") if x.strip()] if m else []
            same = bool(m and (m.group(3), int(m.group(4))) == (str(y), i))
            A = {"title": h1.group(1).strip() if h1 else None, "author": ";".join(parts[:-1]) if len(parts) >= 2 and same else None,
                 "venue": m.group(2).strip() if m and same else None, "year": m.group(3) if m and same else None}
            rows.append({"id": aid, "status": s2, "tries": n, "len": len(tx), "has_sim": sim >= 0, "A_full": FULL(A),
                         "title_eq_selfcite": bool(h1 and parts and nrm(parts[-1]) == nrm(h1.group(1)))})
    return {"enumerations": enums, "rows": rows}

if __name__ == "__main__":
    part = sys.argv[1]
    if part == "books":
        zh = book_arms("Z-new", [f"subject=%E6%98%93%E7%B5%8C&lang=chi&year_from=2000&year_to=2025&format=json&count=50",
                                 f"subject=%E5%91%A8%E6%98%93&lang=chi&year_from=2000&year_to=2025&format=json&count=50",
                                 f"clas=123.1&lang=chi&year_from=2000&year_to=2025&format=json&count=50"])
        en = book_arms("N-en", ["subject=%E6%98%93%E7%B5%8C&lang=eng&format=json&count=50", "subject=Yi%20jing&lang=eng&format=json&count=50",
                                "subject=I%20ching&lang=eng&format=json&count=50", "clas=123.1&lang=eng&format=json&count=50"])
        res = {"Z-new": zh, "N-en": en}
    elif part == "articles":
        res = {"E": early_china(), "E-kyoto": kyoto_gate(), "C-old": c_old()}
    json.dump(res, open(f"p2_{part}_result.json", "w"), ensure_ascii=False, indent=1)
    print(json.dumps(res, ensure_ascii=False, default=str)[:200])
