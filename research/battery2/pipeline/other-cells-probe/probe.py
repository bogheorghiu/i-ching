"""Other-cells probe, per OTHER-CELLS-DESIGN.md section 1 (commit c630f58). Reads fields by code only."""
import sys, json, re, time, concurrent.futures as cf
sys.path.insert(0, ".")
import f

def get(which, url):
    """up to 3 tries on non-200; auth/billing statuses abort."""
    for i in range(3):
        s = f.fetch(which, url, force=(i > 0))
        if s["status"] in (401, 402, 429):
            sys.exit(f"VOID: {which} status {s['status']}")
        t = f.text(s)
        if s["status"] == 200 and "failed to fetch" not in t[:200] and "No Connections" not in t[:200]:
            return s["status"], t, i + 1
        time.sleep(3)
    return s["status"], "", 3

def jparse(t):
    t = t.strip()
    t = re.sub(r"^```\w*\n|\n```$", "", t).strip()
    try: return json.loads(t)
    except Exception: return None

def nrm(x): return re.sub(r"[\W_]+", "", (x or "").lower())

def tags(t, name):
    return [re.sub(r"\s+", " ", m).strip() for m in re.findall(rf"<{name}[^>]*>(.*?)</{name}>", t, re.S)]

def book_arm(arm, lang, y0, y1):
    q = f"https://ci.nii.ac.jp/books/opensearch/search?clas=123.1&lang={lang}" + (f"&year_from={y0}&year_to={y1}" if y0 else "") + "&format=json&count=20"
    st, t, _ = get("ds", q); js = jparse(t)
    items = (js or {}).get("@graph", [{}])[0].get("items", []) if js else []
    total = (js or {}).get("@graph", [{}])[0].get("opensearch:totalResults") if js else None
    elig = []
    for it in items:
        isbns = [p["@id"].split(":")[-1] for p in it.get("dcterms:hasPart", []) if "isbn" in p.get("@id", "")]
        if isbns: elig.append((it["@id"].rsplit("/", 1)[-1], isbns[0]))
    out = {"arm": arm, "enum_status": st, "enum_total": total, "enum_returned": len(items), "eligible": len(elig), "rows": []}
    def one(c):
        ncid, isbn = c
        r = {"id": ncid, "isbn": isbn}
        sa, ta, _ = get("ds", f"https://ci.nii.ac.jp/ncid/{ncid}.json"); ja = jparse(ta)
        g = (ja or {}).get("@graph", [{}])[0] if ja else {}
        A = {"title": (g.get("dc:title") or [{}])[0].get("@value"), "author": g.get("dc:creator"),
             "publisher": (g.get("dc:publisher") or [{}])[0].get("@value") if g.get("dc:publisher") else None, "year": g.get("dc:date")}
        sb, tb, _ = get("ms", f"https://sru.k10plus.de/opac-de-627?version=1.1&operation=searchRetrieve&query=pica.isb%3D{isbn}&maximumRecords=1&recordSchema=dc")
        B = {"title": (tags(tb, "dc:title") or [None])[-1 if lang == "chi" and len(tags(tb, "dc:title")) > 1 else 0],
             "author": "; ".join(tags(tb, "dc:creator") + tags(tb, "dc:contributor")) or None,
             "publisher": (tags(tb, "dc:publisher") or [None])[0], "year": (tags(tb, "dc:date") or [None])[0]}
        B["all_titles"] = tags(tb, "dc:title")
        sn, tn, _ = get("ms", f"https://ndlsearch.ndl.go.jp/api/opensearch?cnt=1&isbn={isbn}&dpid=iss-ndl-opac")
        N = {"hits": (tags(tn, "openSearch:totalResults") or [None])[0], "title": (tags(tn, "dc:title") or [None])[0],
             "author": (tags(tn, "dc:creator") or tags(tn, "author") or [None])[0], "publisher": (tags(tn, "dc:publisher") or [None])[0],
             "year": (tags(tn, "dcterms:issued") or tags(tn, "dc:date") or [None])[0]}
        full = lambda d: all(d.get(k) for k in ("title", "author", "publisher", "year"))
        r.update(A_status=sa, B_status=sb, N_status=sn, A_full=full(A), B_full=full(B), N_full=full(N), N_hits=N["hits"],
                 A_missing=[k for k in ("title", "author", "publisher", "year") if not A.get(k)],
                 B_missing=[k for k in ("title", "author", "publisher", "year") if not B.get(k)])
        if full(A) and full(B):
            r["title_agree"] = any(nrm(A["title"]) == nrm(x) or nrm(A["title"]).startswith(nrm(x)) or nrm(x).startswith(nrm(A["title"])) for x in B["all_titles"] if nrm(x))
            r["year_agree"] = A["year"][:4] == B["year"][:4]
        r["_A"], r["_B"], r["_N"] = A, B, N
        return r
    with cf.ThreadPoolExecutor(4) as ex:
        out["rows"] = list(ex.map(one, elig[:8]))
    return out

if __name__ == "__main__":
    res = [book_arm("B-zh-new", "chi", 2000, 2025), book_arm("B-zh-old", "chi", 1987, 1999), book_arm("B-en", "eng", None, None)]
    json.dump(res, open("books_result.json", "w"), ensure_ascii=False, indent=1)
    for a in res:
        print(f"\n## {a['arm']}: enum status {a['enum_status']} total {a['enum_total']} returned {a['enum_returned']} eligible {a['eligible']}")
        for r in a["rows"]:
            print(" ", r["id"], r["isbn"], "A", r["A_status"], r["A_full"], r["A_missing"], "| B", r["B_status"], r["B_full"], r["B_missing"], "| agree t/y", r.get("title_agree"), r.get("year_agree"), "| NDL", r["N_status"], r["N_hits"], r["N_full"])
        rows = a["rows"]
        print("  both:", sum(r["A_full"] and r["B_full"] for r in rows), "of", len(rows), "| A:", sum(r["A_full"] for r in rows), "| B:", sum(r["B_full"] for r in rows), "| NDL full:", sum(r["N_full"] for r in rows))
