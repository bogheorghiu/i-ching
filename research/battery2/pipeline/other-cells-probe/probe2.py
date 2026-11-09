"""Follow-up book probe, OTHER-CELLS-DESIGN.md section 2 (commit 6e096e0)."""
import sys, json, re, concurrent.futures as cf
sys.path.insert(0, ".")
import f
from probe import get, jparse, nrm

def sub(field_text, code):
    return [re.sub(r"\s+", " ", x).strip() for x in re.findall(rf'<subfield\s*code="{code}">(.*?)</subfield>', field_text, re.S)]
def fields(t, tag):
    return re.findall(rf'<datafield\s*tag="{tag}".*?</datafield>', t, re.S)
def linked(t, tag):
    return [x for x in fields(t, "880") if any(s.startswith(tag) for s in sub(x, "6"))]
def marc(t):
    def first(tags, code, pool):
        for tg in tags:
            for fl in pool(t, tg):
                v = sub(fl, code)
                if v: return v[0]
        return None
    out = {}
    for name, pool in (("rom", fields), ("orig", linked)):
        out[name] = {"title": first(["245"], "a", pool), "author": first(["100", "700"], "a", pool) or first(["245"], "c", pool),
                     "publisher": first(["264", "260"], "b", pool), "year": first(["264", "260"], "c", pool)}
    return out

def arm(name, q, skip):
    st, t, _ = get("ds", q); js = jparse(t)
    items = (js or {}).get("@graph", [{}])[0].get("items", []) if js else []
    elig = []
    for it in items:
        isbns = [p["@id"].split(":")[-1] for p in it.get("dcterms:hasPart", []) if "isbn" in p.get("@id", "")]
        if isbns: elig.append((it["@id"].rsplit("/", 1)[-1], isbns[0]))
    cands = elig[skip:skip + 8]
    def one(c):
        ncid, isbn = c
        sa, ta, _ = get("ds", f"https://ci.nii.ac.jp/ncid/{ncid}.json"); ja = jparse(ta)
        g = (ja or {}).get("@graph", [{}])[0] if ja else {}
        A = {"title": (g.get("dc:title") or [{}])[0].get("@value"), "author": g.get("dc:creator"),
             "publisher": (g.get("dc:publisher") or [{}])[0].get("@value") if g.get("dc:publisher") else None, "year": g.get("dc:date")}
        sb, tb, tries = get("ms", f"https://sru.k10plus.de/opac-de-627?version=1.1&operation=searchRetrieve&query=pica.isb%3D{isbn}&maximumRecords=1&recordSchema=marcxml")
        M = marc(tb); B = {k: M["rom"][k] or M["orig"][k] for k in M["rom"]}
        full = lambda d: all(d.get(k) for k in ("title", "author", "publisher", "year"))
        r = {"id": ncid, "isbn": isbn, "A_status": sa, "B_status": sb, "B_tries": tries, "B_len": len(tb), "A_full": full(A), "B_full": full(B),
             "B_missing": [k for k in B if not B[k]], "B_has_orig_script": bool(M["orig"]["title"]), "_A": A, "_M": M}
        if r["A_full"] and r["B_full"]:
            ta_, tbs = nrm(A["title"].split(" : ")[0]), [nrm(M[x]["title"]) for x in M if M[x]["title"]]
            r["title_agree"] = any(ta_ and (ta_ == x or ta_.startswith(x) or x.startswith(ta_)) for x in tbs)
            r["year_agree"] = re.sub(r"\D", "", A["year"])[:4] == re.sub(r"\D", "", B["year"])[:4]
        return r
    with cf.ThreadPoolExecutor(4) as ex:
        rows = list(ex.map(one, cands))
    return {"arm": name, "enum_status": st, "eligible": len(elig), "rows": rows}

if __name__ == "__main__":
    base = "https://ci.nii.ac.jp/books/opensearch/search?"
    res = [arm("B-zh-new/2", base + "clas=123.1&lang=chi&year_from=2000&year_to=2025&format=json&count=20", 8),
           arm("B-zh-old/2", base + "clas=123.1&lang=chi&year_from=1987&year_to=1999&format=json&count=20", 8),
           arm("B-en/2", base + "subject=%E6%98%93%E7%B5%8C&lang=eng&format=json&count=20", 0)]
    json.dump(res, open("books2_result.json", "w"), ensure_ascii=False, indent=1)
    for a in res:
        print(f"\n## {a['arm']}: enum {a['enum_status']} eligible {a['eligible']}")
        for r in a["rows"]:
            print(" ", r["id"], r["isbn"], "A", r["A_status"], r["A_full"], "| B", r["B_status"], "tries", r["B_tries"], "len", r["B_len"], r["B_full"], r["B_missing"], "orig", r["B_has_orig_script"], "| agree t/y", r.get("title_agree"), r.get("year_agree"))
        rows = a["rows"]; both = [r for r in rows if r["A_full"] and r["B_full"]]
        print("  both:", len(both), "of", len(rows), "| title agree", sum(bool(r.get("title_agree")) for r in both), "| year agree", sum(bool(r.get("year_agree")) for r in both))
