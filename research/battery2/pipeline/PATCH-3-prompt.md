Third run of your build_keys.py: 35 candidates, 0 kept. Drops with your new per-step logs are below. Fix these, returning whole functions in the same format as before (`### replace <name>` / `### add <name> after <name>`, each in its own ```python block), then a short paragraph per fix.
1. OWNER DECISION (recorded as a pre-registration deviation): two library catalogues from DIFFERENT institutions (different registered domains) count as independent records. CNKI/VIP/Wanfang still count as one class; booksellers are never records.
2. Author matching: catalogue-style names ('Eyferth, Jan Jacob Karl, 1962-') must match 'Jacob Eyferth': strip dates and roles, compare surname plus at least one given name, order-insensitive. Do not loosen Chinese name matching.
3. A search hit with title/venue/year but no author: before dropping, fetch the hit's own page once (if fetchable) and verify the author there; if that fails, drop as now.
4. Journal-introduction pages ('期刊介绍', journal home pages) are listing pages, not records.
Keep every other rule. Code below, then drop samples.

=== CODE ===
def norm(s):
    s = unicodedata.normalize("NFKC", str(s or ""))
    s = deaccent(t2s(s).lower())
    return re.sub(r"[\W_]+", "", s)

def author_parts(a):
    return [p.strip() for p in AUTH_SPLIT.split(str(a or "")) if norm(p)]

def author_key(a):
    s = deaccent(t2s(unicodedata.normalize("NFKC", str(a or ""))).lower())
    cjk = set()
    for p in author_parts(s):
        if has_cjk(p):
            q = ROLE_ZH.sub("", re.sub(r"[^\u3400-\u9fff\uf900-\ufaff]", "", p))
            if q:
                cjk.add(q)
    latin = sorted(t for t in re.findall(r"[a-z]+", re.sub(r"[\u3400-\u9fff]", " ", s)) if t not in ROLE_EN)
    return (frozenset(cjk), tuple(latin))

def venue_key(v):
    n = norm(v)
    return n[3:] if n.startswith("the") else n

def classify(url):
    hp = url_hp(url)
    if not hp or any(b in hp for b in BANNED):
        return None
    for cls, pats in CLASS_RULES:
        if any(p in hp for p in pats):
            return cls
    return None

def reg_domain(host):
    p = host.split(".")
    if len(p) >= 3 and p[-2] in ("edu", "com", "ac", "org", "gov", "net") and len(p[-1]) == 2:
        return ".".join(p[-3:])
    return ".".join(p[-2:])

def is_listing_url(url):
    """True if the URL is a listing (search result, TOC/issue index, hotword/wiki page, column) rather than one work's
    own item page. Hosts with a known item-URL form must match it; other hosts are judged by listing patterns only."""
    hp = url_hp(url)
    host = host_of(url)
    path = hp[len(hp.split("/")[0]):]
    if host.startswith("wiki.") or ".wiki." in host or "wiki.cnki" in hp:
        return True
    if LISTING_PATH.search(path):
        return True
    for dom, pat in ITEM_URL:
        if host == dom or host.endswith("." + dom):
            return not re.search(pat, path)
    return False

def is_listing_text(text, title=""):
    """Content test on a search hit: listing markers in its title or text, more than one year/issue, or several
    different 《》 titles mean the hit describes a listing, not one work."""
    if title and LIST_TITLE_MARK.search(unicodedata.normalize("NFKC", str(title))):
        return True
    t = unicodedata.normalize("NFKC", str(text or ""))
    if LIST_BODY_MARK.search(t):
        return True
    issues = {(m.group(1), m.group(2)) for m in re.finditer(r"((?:19|20)\d\d)\s*年\s*第?\s*0?(\d{1,2})\s*期", t)}
    if len(issues) > 1:
        return True
    quoted = {norm(x) for x in re.findall(r"《([^《》]{2,60})》", t) if norm(x)}
    return len(quoted) >= 3

def verify_entry(e, raw):
    """Keep only fields that occur verbatim (after normalisation) in the snapshot; return (verified, dropped_fields)."""
    nt, rawn = norm(raw), unicodedata.normalize("NFKC", raw)
    out, dropped = {}, []
    a = e.get("author")
    if isinstance(a, list):
        a = "；".join(str(x) for x in a)
    if a:
        parts = author_parts(a)
        if parts and all(norm(p) in nt for p in parts):
            out["author"] = str(a).strip()
        else:
            dropped.append("author")
    for f in ("title", "venue", "volume_issue"):
        v = e.get(f)
        if v is None or not str(v).strip():
            continue
        v = str(v).strip()
        if norm(v) and norm(v) in nt:
            out[f] = v
        else:
            dropped.append(f)
    y = e.get("year")
    if y is not None:
        m = re.search(r"(1[89]\d\d|20\d\d)", unicodedata.normalize("NFKC", str(y)))
        if m and m.group(1) in rawn:
            out["year"] = int(m.group(1))
        else:
            dropped.append("year")
    ab = e.get("abstract")
    if isinstance(ab, str) and ab.strip():
        sents = [s for s in re.split(r"(?<=[。！？.!?；;])\s*", ab) if len(norm(s)) >= 4]
        good = [s for s in sents if norm(s) in nt]
        if good:
            out["abstract"] = " ".join(good)
        if len(good) < len(sents):
            dropped.append(f"abstract_sentences:{len(sents) - len(good)}")
    kws = e.get("keywords") or []
    if isinstance(kws, str):
        kws = re.split(r"[;；,，、]", kws)
    good = [str(k).strip() for k in kws if norm(k) and norm(k) in nt]
    if good:
        out["keywords"] = good
    for f in ("citations", "holdings"):
        v = e.get(f)
        if v is not None:
            d = str(v).replace(",", "").strip()
            if re.fullmatch(r"\d+", d) and d in rawn:
                out[f] = int(d)
            else:
                dropped.append(f)
    out["work_type_llm"] = e.get("work_type")
    return out, dropped

def record_from_hit(hit, idx, sfile, query, route, url, mode, target=None, diag=None):
    """Record from a search hit: the hit's JSON is the snapshot; the page is fetched only if the hit lacks a field.
    Returns (entry, record_dict, None) or (None, None, reason). diag (optional dict) receives a 'steps' log."""
    diag = {} if diag is None else diag
    steps = diag.setdefault("steps", [])
    why = "field_unverified"
    if hit is not None:
        ht = hit_text(hit)
        if is_listing_text(ht, str(hit.get("title", ""))):
            steps.append({"step": "hit", "result": "listing_text", "hit_title": str(hit.get("title", ""))[:80]})
            return None, None, "listing_page"
        if len(norm(ht)) >= 8:
            hfn = save_hit_snapshot(hit, sfile, idx, query, route)
            d = {"step": "hit", "hit_title": str(hit.get("title", ""))[:80]}
            e, why = item_entry(hfn, url, mode, target, d)
            d["result"] = why or "ok"
            steps.append(d)
            if e is not None:
                return e, {"url": url, "snapshot_file": hfn, "snapshot_kind": "search_hit", "search_snapshot": sfile,
                           "hit_index": idx, "query": query, "route": route, "date": today()}, None
            if why == "listing_page":
                return None, None, why
        else:
            steps.append({"step": "hit", "result": "hit_text_too_short", "chars": len(norm(ht))})
    else:
        steps.append({"step": "hit", "result": "hit_not_in_search_snapshot"})
    F = ds_fetch(url, route)                      # optional fallback for a missing field
    if not F["ok"]:
        steps.append({"step": "fetch", "result": "fetch_failed"})
        return None, None, ("unfetchable_source" if hit is None else why)
    if target and not loose_title_in(target["title"], F["text"]):
        steps.append({"step": "fetch", "result": "target_title_absent", "snapshot": F["file"]})
        return None, None, why
    d = {"step": "fetch"}
    e, why2 = item_entry(F["file"], url, mode, target, d)
    d["result"] = why2 or "ok"
    steps.append(d)
    if e is not None:
        return e, {"url": url, "snapshot_file": F["file"], "snapshot_kind": "fetch", "search_snapshot": sfile,
                   "hit_index": idx, "query": query, "route": route, "date": F["date"] or today()}, None
    return None, None, (why2 if why2 == "listing_page" else why)

def b_queries(entry, a_text, cand):
    """Queries for an independent ITEM record (not issue browses, which return listings). Books: the record's own
    ISBNs in both forms, then a publisher-directed query (reaches publisher catalogues, a different custodian class
    from a library record A), then title/author/venue and catalogue queries."""
    typ, lang = cand["cell"]
    t, v, y = entry["title"], entry.get("venue") or "", entry.get("year") or ""
    parts = [ROLE_ZH.sub("", p) for p in author_parts(entry.get("author"))]
    a0 = parts[0].strip() if parts else ""
    qs = []
    if typ == "book":
        qs += [(f"ISBN {d}", "isbn") for d in isbn_variants(a_text)[:4]]
        if v:
            qs.append((f"{v} {t} {a0}".strip(), "publisher_title"))
    if lang == "zh":
        qs += [(f"{t} {a0}".strip(), "title_author"), (f"{t} {v} {y}".strip(), "title_venue"),
               (f"CiNii {t}", "catalogue_title")]
    else:
        qs += [(f"\"{t}\" {a0}".strip(), "title_author"), (f"{t} {v} {y}".strip(), "title_venue"),
               (f"CiNii {t}", "catalogue_title"), (f"WorldCat {t} {a0}".strip(), "catalogue_title")]
    out, seen = [], set()
    for q, r in qs:
        if norm(q) and norm(q) not in seen:
            seen.add(norm(q))
            out.append((q, r))
    return out

def stage_b(st, args):
    if st.get("drop") or st.get("recB"):
        return
    c = st["cand"]
    cls = classify(c["url"])
    if not cls:
        return drop(st, "not_primary_source", "b", c["url"])
    if "entryA" not in st:
        if is_listing_url(c["url"]):
            return drop(st, "listing_page", "b", "record A URL is a listing: " + c["url"])
        idx, hit = cand_hit(c)
        route = f"harvest search: {c['query']}"
        diag = {}
        entry, rec, why = record_from_hit(hit, idx, c["search_snapshot"], c["query"], route, c["url"], "A", diag=diag)
        if entry is None:
            return drop(st, why, "b" if why in ("unfetchable_source", "listing_page") else "c",
                        "record A: " + json.dumps(diag, ensure_ascii=False)[:1500])
        st["recA"] = dict(rec, custodian_class=cls)
        st["entryA"] = entry
        st["extract_files"] = {"A": rec["snapshot_file"]}
        save_state(st)
    entry = st["entryA"]
    a_cls = st["recA"]["custodian_class"]
    a_text = verify_source(st["recA"]["snapshot_file"])      # record A's own text only (not our query/URL)
    qs = b_queries(entry, a_text, c)
    if not qs:
        return drop(st, "no_second_record", "b", "no route to a second record")
    target = {"title": entry["title"], "author": entry.get("author")}
    used_q = {norm(c["query"])}                 # record B must be reached by a different query
    tried, searches, n_hits = 0, 0, 0
    skips, fails, classes_seen = {}, {}, {}
    def skip(k):
        skips[k] = skips.get(k, 0) + 1
    for q, route in qs:
        if norm(q) in used_q or tried >= 4:
            continue
        used_q.add(norm(q))
        rt = f"{route}: {q}"
        res, sfile = ds_search(q, 10, route=rt)
        searches += 1
        if not res:
            skip("search_empty")
            continue
        for i, r in enumerate(res):
            if tried >= 4:
                break
            n_hits += 1
            u = r_url(r).split("#")[0]
            cl = classify(u) if u else None
            if not u:
                skip("no_url"); continue
            if not cl:
                skip("unclassified"); continue
            classes_seen[cl] = classes_seen.get(cl, 0) + 1
            if cl == a_cls:
                skip("same_class"); continue   # different custodian class required; two aggregators never pair
            if reg_domain(host_of(u)) == reg_domain(host_of(c["url"])):
                skip("same_domain"); continue
            if is_listing_url(u) or is_listing_text(hit_text(r), str(r.get("title", ""))):
                skip("listing"); continue
            if not loose_title_in(entry["title"], hit_text(r)):
                skip("title_absent"); continue
            tried += 1
            e, rec, why = record_from_hit(r, i, sfile, q, rt, u, "B", target)
            if e is not None:
                st["recB"] = dict(rec, custodian_class=cl)
                return
            fails[why] = fails.get(why, 0) + 1
    drop(st, "no_second_record", "b",
         f"no independent item record found ({tried} tried; {searches} searches, {n_hits} hits; "
         f"A class={a_cls}; skipped={json.dumps(skips, ensure_ascii=False)}; "
         f"classes_seen={json.dumps(classes_seen, ensure_ascii=False)}; failed={json.dumps(fails, ensure_ascii=False)})")

=== DROP SAMPLES (run 3) ===
{
 "field_unverified": [
  {
   "cid": "c0378cdc5b5",
   "url": "http://zhouyi.sdu.edu.cn/zyyjxk/qkjs.htm",
   "cell": [
    "article",
    "zh"
   ],
   "rule": "field_unverified",
   "stage": "c",
   "detail": "record A: {\"steps\": [{\"step\": \"hit\", \"hit_title\": \"期刊介绍\", \"snapshot\": \"h_d35495597146ec80.json\", \"page_kind\": \"other\", \"n_entries\": 0, \"verified_fields\": [], \"dropped_fields\": [], \"result\": \"field_unverified\"}, {\"step\": \"fetch\", \"snapshot\": \"f_0378cdc5b5da9584.json\", \"page_kind\": \"other\", \"n_entries\": 0, \"verified_fields\": [], \"dropped_fields\": [], \"result\": \"field_unverified\"}]}",
   "date": "2026-11-04",
   "key": null,
   "clues": {}
  },
  {
   "cid": "c1c20e53b75",
   "url": "https://search.napstic.cn/literature/periodical/010zhouyyj202401001",
   "cell": [
    "article",
    "zh"
   ],
   "rule": "field_unverified",
   "stage": "c",
   "detail": "record A: {\"steps\": [{\"step\": \"hit\", \"hit_title\": \"周易研究\", \"snapshot\": \"h_13ef864254a250b9.json\", \"page_kind\": \"single_record\", \"n_entries\": 1, \"verified_fields\": [[\"title\", \"venue\", \"volume_issue\", \"year\"]], \"dropped_fields\": [[]], \"result\": \"field_unverified\"}, {\"step\": \"fetch\", \"result\": \"fetch_failed\"}]}",
   "date": "2026-11-04",
   "key": null,
   "clues": {}
  },
  {
   "cid": "c28839b2c0d",
   "url": "https://www.cnki.com.cn/Article/CJFDTotal-CUWX202301016.htm",
   "cell": [
    "article",
    "zh"
   ],
   "rule": "field_unverified",
   "stage": "c",
   "detail": "record A: {\"steps\": [{\"step\": \"hit\", \"hit_title\": \"《出土文献》 - 《出土文献》\", \"snapshot\": \"h_722eaa8a3c0ae245.json\", \"page_kind\": \"single_record\", \"n_entries\": 1, \"verified_fields\": [[\"title\", \"venue\"]], \"dropped_fields\": [[]], \"result\": \"field_unverified\"}, {\"step\": \"fetch\", \"snapshot\": \"f_28839b2c0d678db6.json\", \"page_kind\": \"single_record\", \"n_entries\": 1, \"verified_fields\": [[\"abstract\", \"title\", \"venue\"]], \"dropped_fields\": [[]], \"result\": \"field_unverified\"}]}",
   "date": "2026-11-04",
   "key": null,
   "clues": {}
  }
 ],
 "field_mismatch:author": [
  {
   "cid": "c10746414fb",
   "url": "https://library.aarome.org/cgi-bin/koha/opac-ISBDdetail.pl?biblionumber=151129",
   "cell": [
    "book",
    "en"
   ],
   "rule": "field_mismatch:author",
   "stage": "d",
   "detail": "Eyferth, Jan Jacob Karl, 1962- | Jacob Eyferth",
   "date": "2026-11-04",
   "key": null,
   "clues": {}
  }
 ],
 "no_second_record": [
  {
   "cid": "c1648bc9cc5",
   "url": "http://opac.lib.uibe.edu.cn/opac/book/245cab5b411f7cea5653766fd0e10bbb",
   "cell": [
    "book",
    "zh"
   ],
   "rule": "no_second_record",
   "stage": "b",
   "detail": "no independent item record found (0 tried; 6 searches, 60 hits; A class=library; skipped={\"unclassified\": 36, \"same_class\": 23, \"listing\": 1}; classes_seen={\"library\": 23, \"aggregator\": 1}; failed={})",
   "date": "2026-11-04",
   "key": null,
   "clues": {}
  },
  {
   "cid": "c25272ff878",
   "url": "https://kuline.kulib.kyoto-u.ac.jp/opac/opac_details/?lang=0&amode=11&bibid=BB04622887",
   "cell": [
    "book",
    "zh"
   ],
   "rule": "no_second_record",
   "stage": "b",
   "detail": "no independent item record found (0 tried; 6 searches, 60 hits; A class=library; skipped={\"unclassified\": 40, \"same_class\": 19, \"listing\": 1}; classes_seen={\"library\": 19, \"aggregator\": 1}; failed={})",
   "date": "2026-11-04",
   "key": null,
   "clues": {}
  },
  {
   "cid": "c4e99fc7d9c",
   "url": "https://find.library.duke.edu/catalog/DUKE006672587",
   "cell": [
    "book",
    "zh"
   ],
   "rule": "no_second_record",
   "stage": "b",
   "detail": "no independent item record found (0 tried; 4 searches, 40 hits; A class=library; skipped={\"same_class\": 35, \"unclassified\": 5}; classes_seen={\"library\": 35}; failed={})",
   "date": "2026-11-04",
   "key": null,
   "clues": {}
  }
 ],
 "listing_page": [
  {
   "cid": "c18febbb10b",
   "url": "https://hermes.lib.hit-u.ac.jp/opac/opac_search/?reqCode=fromsrch&lang=1&amode=2&smode=1&con1_exp=alkey&kywd1_exp=%23Watt%20Lori&con2_exp=alkey&con3_exp=pubkey&disp_exp=20",
   "cell": [
    "book",
    "en"
   ],
   "rule": "listing_page",
   "stage": "b",
   "detail": "record A: {\"steps\": [{\"step\": \"hit\", \"hit_title\": \"HERMES-Catalog\", \"snapshot\": \"h_4653c03401a1fd65.json\", \"page_kind\": \"list\", \"n_entries\": 1, \"verified_fields\": [[\"venue\", \"volume_issue\", \"year\"]], \"dropped_fields\": [[]], \"result\": \"listing_page\"}]}",
   "date": "2026-11-04",
   "key": null,
   "clues": {}
  },
  {
   "cid": "cafd37eaba5",
   "url": "https://zhouyi.sdu.edu.cn/v3/xueshudongtai/zhexuejuan.asp",
   "cell": [
    "article",
    "zh"
   ],
   "rule": "listing_page",
   "stage": "b",
   "detail": "record A: {\"steps\": [{\"step\": \"hit\", \"hit_title\": \"山东大学易学与古代哲学研究中心 学术动态\", \"snapshot\": \"h_141f18c1961aaf73.json\", \"page_kind\": \"list\", \"n_entries\": 2, \"verified_fields\": [[\"author\", \"title\", \"venue\"], [\"author\", \"title\", \"venue\"]], \"dropped_fields\": [[], []], \"result\": \"listing_page\"}]}",
   "date": "2026-11-04",
   "key": null,
   "clues": {}
  }
 ],
 "field_mismatch:venue": [
  {
   "cid": "cf48da8491d",
   "url": "https://kuline.kulib.kyoto-u.ac.jp/opac/opac_authority/?lang=0&amode=11&auid=AU00874834&start=&opkey=B172690138377138&bibid=BB06050940&listnum=",
   "cell": [
    "book",
    "en"
   ],
   "rule": "field_mismatch:venue",
   "stage": "d",
   "detail": "Harvard University Asia Center | Harvard University Press",
   "date": "2026-11-04",
   "key": null,
   "clues": {}
  }
 ]
}