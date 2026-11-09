"""Article arms, OTHER-CELLS-DESIGN.md section 1 + deviation 1."""
import sys, json, re, concurrent.futures as cf
sys.path.insert(0, ".")
import f
from probe import get, jparse, nrm
CNKI_SELF = re.compile(r"^([^\[\]\n|]+?)\[J\];([^;\n]+);(\d{4})年(\d{1,2})期", re.M)   # as in build_keys.py

def camb(t):
    first = t.strip().split("\n", 1)[0]
    m = re.match(r"(.+?) \| (Early China) \| Cambridge Core", first)
    a = re.search(r"Published online by Cambridge University Press:[^\n]*\n\s*\n- ([^\n*]+)", t)
    y = re.search(r"Copyright ©[^\n]*?((?:19|20)\d\d)", t) or re.search(r"Early China\s*,?\s*Volume\s*\d+[^\n]{0,40}?((?:19|20)\d\d)", t)
    return {"title": m.group(1) if m else None, "venue": m.group(2) if m else None, "author": a.group(1).strip() if a else None, "year": y.group(1) if y else None}

def en_arm():
    rows = []
    for w0, w1 in ((1990, 1995), (2010, 2012)):
        q = f"https://api.crossref.org/journals/0362-5028/works?rows=20&select=DOI,title,author,issued,volume,page&filter=from-pub-date:{w0},until-pub-date:{w1}"
        st, t, _ = get("ds", q); js = jparse(t) or {}
        items = js.get("message", {}).get("items", [])
        elig = [it for it in items if it.get("author") and it.get("page")]
        print(f"enum {w0}-{w1}: status {st} total {js.get('message', {}).get('total-results')} returned {len(items)} eligible {len(elig)}")
        for it in elig[:4]:
            pii = it["DOI"].split("/")[-1].upper()
            url = f"https://www.cambridge.org/core/product/identifier/{pii}/type/journal_article"
            r = {"id": it["DOI"], "window": f"{w0}-{w1}", "vol": it.get("volume"), "page": it.get("page")}
            for w in ("ms", "ds"):
                s, tx, n = get(w, url); c = camb(tx)
                r[w] = {"status": s, "tries": n, "len": len(tx), "full": all(c.values()), "missing": [k for k in c if not c[k]],
                        "title_eq_crossref": nrm(c["title"]) == nrm(it["title"][0]) if c["title"] else None}
            rows.append(r)
    return rows

def zh_arm():
    rows = []
    def one(i):
        url = f"https://www.cnki.com.cn/Article/CJFDTotal-ZYJY1995010{i:02d}.htm"
        r = {"id": f"ZYJY1995010{i:02d}"}
        for w in ("ms", "ds"):
            s, tx, n = get(w, url)
            h1 = re.search(r"^#\s+(.+)$", tx, re.M); sim = tx.find("相似文献")
            m = CNKI_SELF.search(tx[sim:].replace("|", "\n")) if sim >= 0 else None
            parts = [x.strip() for x in m.group(1).split(";") if x.strip()] if m else []
            ok = bool(h1 and m and len(parts) >= 2 and nrm(parts[-1]) == nrm(h1.group(1)) and (m.group(3), int(m.group(4))) == ("1995", 1))
            r[w] = {"status": s, "tries": n, "len": len(tx), "has_h1": bool(h1), "has_sim": sim >= 0, "full": ok}
        return r
    with cf.ThreadPoolExecutor(4) as ex:
        rows = list(ex.map(one, range(1, 9)))
    return rows

if __name__ == "__main__":
    en, zh = en_arm(), zh_arm()
    json.dump({"A-en": en, "A-zh-old": zh}, open("articles_result.json", "w"), ensure_ascii=False, indent=1)
    print("\n## A-en record A")
    for r in en: print(" ", r["id"], r["window"], "vol", r["vol"], "| ms", r["ms"]["status"], r["ms"]["len"], r["ms"]["full"], r["ms"]["missing"], "| ds", r["ds"]["status"], r["ds"]["len"], r["ds"]["full"], r["ds"]["missing"], r["ds"]["title_eq_crossref"])
    print("  A full via ms:", sum(r["ms"]["full"] for r in en), "| via ds:", sum(r["ds"]["full"] for r in en), "of", len(en))
    print("\n## A-zh-old record A")
    for r in zh: print(" ", r["id"], "| ms", r["ms"], "| ds", r["ds"])
    print("  A full via ms:", sum(r["ms"]["full"] for r in zh), "| via ds:", sum(r["ds"]["full"] for r in zh), "of", len(zh))
