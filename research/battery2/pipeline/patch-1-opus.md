### add hit_text after r_text
```python
def hit_text(r):
    """Text of ONE search hit as saved: its own title/snippet/summary/content/description, no URL and no crawl date
    (so a year or digits inside a URL can never verify a field)."""
    if not isinstance(r, dict):
        return ""
    out = []
    for k in ("title", "snippet", "summary", "content", "description"):
        v = r.get(k)
        if isinstance(v, str) and v.strip() and v.strip() not in out:
            out.append(v.strip())
    return "\n".join(out)
```

### add save_hit_snapshot after ds_search
```python
def save_hit_snapshot(hit, parent_file, idx, query, route):
    """Snapshot of one search hit: the hit's own JSON from the saved search response, with a pointer to that response."""
    fn = f"h_{sha(str(parent_file) + '|' + str(idx))}.json"
    path = os.path.join(SNAP, fn)
    if read_json(path) is None:
        write_json(path, {"kind": "search_hit", "parent_snapshot": parent_file, "hit_index": idx, "query": query,
                          "route": route, "url": r_url(hit), "date": today(), "response": hit})
        jlog(os.path.join(SNAP, "index.jsonl"), {"kind": "search_hit", "parent": parent_file, "hit_index": idx,
                                                 "query": query, "route": route, "date": today(), "file": fn})
    return fn
```

### replace snapshot_text
```python
def snapshot_text(fn):
    snap = read_json(os.path.join(SNAP, fn), {}) or {}
    if snap.get("kind") == "search_hit":
        return hit_text(snap.get("response"))
    return fetch_text(snap.get("response"))
```

### add is_listing_url after classify
```python
LISTING_PATH = re.compile(
    r"(?:[?&](?:q|query|kw|keyword|keywords|key|searchword|wd|word|lookfor|search|term|txt)=|/search|/s\?|/browse|"
    r"hotword|/toc\b|tableofcontents|/issues?(?:/|$|\?)|/all-issues|/listissue|/navi|kns8?/(?:brief|defaultresult)|"
    r"func=(?:find|short|scan)|/column|/catalog\?|/results)", re.I)
ITEM_URL = [
    ("cnki.net", r"(kcms2?/(article/abstract|detail)|detail\.aspx|/kcms/detail/)"),
    ("cnki.com.cn", r"/article/"),
    ("cqvip.com", r"(/qk/[\w-]+/\d+/[\w-]+\.html|/doc/journal/\d+|/article/detail)"),
    ("wanfangdata.com.cn", r"(/details/detail\.do\?_type=(perio|degree|conference)|/(periodical|thesis|conference)/[a-z0-9%=+_-]{10,})"),
    ("nssd.cn", r"(article_detail|/articles/)"),
    ("airitilibrary.com", r"(aldetailedmesh|/article/detail)"),
    ("jstor.org", r"/stable/"),
    ("muse.jhu.edu", r"/(article|book)/\d+"),
    ("ci.nii.ac.jp", r"/(ncid|naid|crid)/"),
    ("cir.nii.ac.jp", r"/crid/"),
    ("opac.nlc.cn", r"func=(full|direct)"),
    ("worldcat.org", r"/(title|oclc)/"),
    ("searchworks.stanford.edu", r"/view/"),
    ("hollis.harvard.edu", r"fulldisplay"),
    ("catalog.hathitrust.org", r"/record/"),
    ("cambridge.org", r"/core/(journals/[^/]+/article/|books/[^/?]+)"),
    ("brill.com", r"(/view/journals/\w+/\d+/[\w.-]+/article|/view/title/|/display/title/|/edcollbook/title/)"),
]


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
```

### add is_listing_text after is_listing_url
```python
LIST_TITLE_MARK = re.compile(r"(目录|目次|总目|索引|检索|搜索|热词|导航|栏目|期刊简介|过刊|往期|期刊浏览|search|\bresults?\b|"
                             r"table of contents|\bcontents\b|all issues|\bissue \d+|\bvolume \d+\b|\bvol\. ?\d+\s*(?:,|no))", re.I)
LIST_BODY_MARK = re.compile(r"(检索结果|搜索结果|共找到|找到约|条记录|条结果|共\s*\d+\s*条|相关搜索|本期目录|往期目录|期刊目录|"
                            r"search results|results for|showing \d+|\d+\s*[-–]\s*\d+\s+of\s+\d+)", re.I)


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
```

### add seed_queries after make_query
```python
def seed_queries(r, cell, meta):
    """Up to two item queries seeded from a listing hit's text (the listing itself is never a record)."""
    txt = hit_text(r)
    venue = meta.get("journal") or meta.get("publisher") or ""
    if cell[1] == "zh":
        segs = re.findall(r"《([^《》]{6,40})》", txt)
        segs += [s for s in re.split(r"[\s|｜;；/／•·]+|\.\.\.|…", txt)
                 if 8 <= len(s) <= 40 and has_cjk(s) and not re.search(r"目录|目次|期刊|检索|搜索|第\d+期|\d{4}年", s)]
    else:
        segs = [s.strip() for s in re.split(r"\s[|·•–—-]\s|;|\.\s|…", txt) if 4 <= len(s.split()) <= 18]
    out, seen = [], {venue_key(venue)}
    for s in segs:
        n = norm(s)
        if not n or n in seen:
            continue
        seen.add(n)
        out.append(f"{s} {venue}".strip())
        if len(out) >= 2:
            break
    return out
```

### add harvest_hit after seed_queries
```python
def harvest_hit(r, idx, sfile, q, cell, meta, rank, offset, allowed, seen, seed_from=None):
    """Register one search hit as a candidate if it is an item record; returns 'added', 'listing' or None."""
    if not isinstance(r, dict):
        return None
    u = r_url(r).split("#")[0]
    hint = str(r.get("title", ""))
    if not u or classify(u) not in allowed:
        return None
    if (cell[1] == "zh") != has_cjk(hint):
        return None
    if is_listing_url(u) or is_listing_text(hit_text(r), hint):
        return "listing"
    if u in seen:
        return None
    c = {"cid": "c" + sha(u, 10), "url": u, "hint_title": hint, "query": q, "search_snapshot": sfile, "hit_index": idx,
         "cell": list(cell), "meta": meta, "rank": rank, "offset": offset, "seed_from": seed_from, "date": today()}
    jlog(cand_path(), c)
    seen.add(u)
    return "added"
```

### replace stage_a
```python
def stage_a(args):
    cands = read_jsonl(cand_path())
    seen = {c["url"] for c in cands}
    have = collections.Counter(tuple(c["cell"]) for c in cands)
    nq = collections.Counter(tuple(q["cell"]) for q in read_jsonl(os.path.join(W, "harvest_queries.jsonl")))
    seed_log = os.path.join(W, "listing_seeds.jsonl")
    seeded = {s.get("seed_query") for s in read_jsonl(seed_log)}
    for cell, share in CELLS.items():
        quota = math.ceil(args.target * share * args.harvest_factor)
        maxq = math.ceil(quota / 3) + 5
        allowed = {"journal_own", "aggregator"} if cell[0] == "article" else {"publisher", "library"}
        while have[cell] < quota and nq[cell] < maxq:
            rng = random.Random(f"{args.seed}:{cell}:{nq[cell]}")
            q, meta = make_query(cell, rng)
            offset = rng.choice([10, 20])
            res, sfile = ds_search(q, offset + 10, route="harvest")
            if len(res) > offset:
                window, eff = res[offset:offset + 10], offset
            elif len(res) > 10:
                window, eff = res[10:], 10
            else:
                window, eff = res, 0
            added, listings = 0, []
            for k, r in enumerate(window):
                out = harvest_hit(r, eff + k, sfile, q, cell, meta, eff + k + 1, eff, allowed, seen)
                if out == "added":
                    added += 1
                    have[cell] += 1
                elif out == "listing":
                    listings.append(r)
            for r in listings[:3]:              # a listing only seeds item queries; it is never a record
                for sq in seed_queries(r, cell, meta):
                    if sq in seeded or have[cell] >= quota:
                        continue
                    seeded.add(sq)
                    res2, sf2 = ds_search(sq, 10, route=f"listing_seed: {r_url(r)}")
                    n2 = 0
                    for j, r2 in enumerate(res2):
                        if harvest_hit(r2, j, sf2, sq, cell, meta, j + 1, 0, allowed, seen, seed_from=r_url(r)) == "added":
                            n2 += 1
                    have[cell] += n2
                    added += n2
                    jlog(seed_log, {"cell": list(cell), "listing_url": r_url(r), "harvest_query": q, "seed_query": sq,
                                    "search_snapshot": sf2, "added": n2, "date": today()})
            jlog(os.path.join(W, "harvest_queries.jsonl"), {"cell": list(cell), "query": q, "count": offset + 10,
                                                           "offset_requested": offset, "offset_used": eff,
                                                           "returned": len(res), "listings_seen": len(listings),
                                                           "added": added, "date": today()})
            nq[cell] += 1
    print(f"[a] candidates: {dict(have)}")
```

### add item_entry after complete
```python
def item_entry(snapfile, url, mode, target=None):
    """Extract + verbatim-verify one snapshot and accept it only as an ITEM record. Returns (entry, None) or
    (None, reason). A page the extractor calls a list, or with complete verified entries for more than one distinct
    title, is a listing and is rejected (never repaired, never narrowed to one entry)."""
    ex = extract(snapfile, url, mode, target)
    if ex["call_rejected"] or not ex["parse_ok"]:
        return None, "extraction_failed"
    parsed = parse_json_obj(ex.get("raw_output")) or {}
    full = [e["verified"] for e in ex["entries"] if complete(e["verified"])]
    if parsed.get("page_kind") == "list" or len({norm(v["title"]) for v in full}) > 1:
        return None, "listing_page"
    if not full:
        return None, "field_unverified"
    return full[0], None
```

### add cand_hit after item_entry
```python
def cand_hit(c):
    """The candidate's own hit inside its saved search response: (index, hit) or (None, None)."""
    snap = read_json(os.path.join(SNAP, c.get("search_snapshot") or "-"), {}) or {}
    res = results_of(snap.get("response"))
    i = c.get("hit_index")
    if isinstance(i, int) and 0 <= i < len(res) and r_url(res[i]).split("#")[0] == c["url"]:
        return i, res[i]
    for j, r in enumerate(res):
        if r_url(r).split("#")[0] == c["url"]:
            return j, r
    return None, None
```

### add record_from_hit after cand_hit
```python
def record_from_hit(hit, idx, sfile, query, route, url, mode, target=None):
    """Record from a search hit: the hit's JSON is the snapshot; the page is fetched only if the hit lacks a field.
    Returns (entry, record_dict, None) or (None, None, reason)."""
    why = "field_unverified"
    if hit is not None:
        if is_listing_text(hit_text(hit), str(hit.get("title", ""))):
            return None, None, "listing_page"
        if len(norm(hit_text(hit))) >= 8:
            hfn = save_hit_snapshot(hit, sfile, idx, query, route)
            e, why = item_entry(hfn, url, mode, target)
            if e is not None:
                return e, {"url": url, "snapshot_file": hfn, "snapshot_kind": "search_hit", "search_snapshot": sfile,
                           "hit_index": idx, "query": query, "route": route, "date": today()}, None
            if why == "listing_page":
                return None, None, why
    F = ds_fetch(url, route)                      # optional fallback for a missing field
    if not F["ok"]:
        return None, None, ("unfetchable_source" if hit is None else why)
    if target and not loose_title_in(target["title"], F["text"]):
        return None, None, why
    e, why2 = item_entry(F["file"], url, mode, target)
    if e is not None:
        return e, {"url": url, "snapshot_file": F["file"], "snapshot_kind": "fetch", "search_snapshot": sfile,
                   "hit_index": idx, "query": query, "route": route, "date": F["date"] or today()}, None
    return None, None, (why2 if why2 == "listing_page" else why)
```

### replace b_queries
```python
def b_queries(entry, a_text, cand):
    """Queries for an independent ITEM record (not issue browses, which return listings)."""
    typ, lang = cand["cell"]
    t, v, y = entry["title"], entry["venue"], entry["year"]
    parts = [ROLE_ZH.sub("", p) for p in author_parts(entry.get("author"))]
    a0 = parts[0] if parts else ""
    qs = []
    if typ == "book":
        qs += [(f"ISBN {d}", "isbn") for d in find_isbns(a_text)[:2]]
    if lang == "zh":
        qs += [(f"{t} {a0}".strip(), "title_author"), (f"{t} {v} {y}", "title_venue"), (f"CiNii {t}", "catalogue_title")]
    else:
        qs += [(f"\"{t}\" {a0}".strip(), "title_author"), (f"{t} {v} {y}", "title_venue"),
               (f"CiNii {t}", "catalogue_title"), (f"WorldCat {t} {a0}".strip(), "catalogue_title")]
    out, seen = [], set()
    for q, r in qs:
        if norm(q) not in seen:
            seen.add(norm(q))
            out.append((q, r))
    return out
```

### replace stage_b
```python
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
        entry, rec, why = record_from_hit(hit, idx, c["search_snapshot"], c["query"], route, c["url"], "A")
        if entry is None:
            return drop(st, why, "b" if why in ("unfetchable_source", "listing_page") else "c", "record A")
        st["recA"] = dict(rec, custodian_class=cls)
        st["entryA"] = entry
        st["extract_files"] = {"A": rec["snapshot_file"]}
        save_state(st)
    entry = st["entryA"]
    a_cls = st["recA"]["custodian_class"]
    a_text = snapshot_text(st["recA"]["snapshot_file"])
    qs = b_queries(entry, a_text, c)
    if not qs:
        return drop(st, "no_second_record", "b", "no route to a second record")
    target = {"title": entry["title"], "author": entry.get("author")}
    used_q = {norm(c["query"])}                 # record B must be reached by a different query
    tried = 0
    for q, route in qs:
        if norm(q) in used_q or tried >= 4:
            continue
        used_q.add(norm(q))
        rt = f"{route}: {q}"
        res, sfile = ds_search(q, 10, route=rt)
        for i, r in enumerate(res):
            if tried >= 4:
                break
            u = r_url(r).split("#")[0]
            cl = classify(u)
            if not u or not cl or cl == a_cls or reg_domain(host_of(u)) == reg_domain(host_of(c["url"])):
                continue   # different custodian class required; two aggregators never pair (same class)
            if is_listing_url(u) or is_listing_text(hit_text(r), str(r.get("title", ""))):
                continue
            if not loose_title_in(entry["title"], hit_text(r)):
                continue
            tried += 1
            e, rec, why = record_from_hit(r, i, sfile, q, rt, u, "B", target)
            if e is not None:
                st["recB"] = dict(rec, custodian_class=cl)
                return
    drop(st, "no_second_record", "b", f"no independent item record found ({tried} tried)")
```

### replace stage_c
```python
def stage_c(st, args):
    if st.get("drop") or not st.get("recB") or st.get("entryB"):
        return
    rb, ea = st["recB"], st["entryA"]
    e, why = item_entry(rb["snapshot_file"], rb["url"], "B", target={"title": ea["title"], "author": ea.get("author")})
    if e is None:
        return drop(st, why, "c", "record B")
    st["entryB"] = e
```

### replace unit_block
```python
def unit_block(st, w, uid):
    k, forms = st["key"], st.get("key_forms", {})
    recs = []
    for tag, r in zip(("A", "B"), st["records"]):
        f = forms.get(tag) or k
        txt = snapshot_text(r["snapshot_file"])
        recs.append({"url": r["url"], "custodian_class": r["custodian_class"], "route": sanitize(r["route"])[:200],
                     "snapshot_kind": r.get("snapshot_kind", "fetch"),
                     "excerpt": excerpt(txt, [f.get("title"), f.get("venue"), f.get("author"), f.get("volume_issue")])})
    return {"id": uid, "key": {x: k.get(x) for x in ("author", "title", "venue", "year", "volume_issue")},
            "work_type": st["stratum"]["type"], "records": recs, "clue": st["clues"][w]["clue"]}
```

### add verify_system after unit_block
```python
def verify_system():
    old = ("- not_primary: a URL is not a primary record (search snippet, citing paper, reference list, encyclopedia, "
           "blog, shop, forum).")
    new = ("- not_primary: a URL is not one work's own item record (article page or catalogue record): e.g. a listing, "
           "table of contents, search-result page, citing paper, reference list, encyclopedia, blog, shop, forum. "
           "snapshot_kind=search_hit means the excerpt is the search engine's result entry for that URL; it counts as "
           "the item record if the URL is the item's own page and the entry describes only that work.")
    return VERIFY_SYSTEM.replace(old, new) if old in VERIFY_SYSTEM else VERIFY_SYSTEM + "\n" + new
```

### replace stage_g
```python
def stage_g(args, states):
    units = []
    for st in states:
        if st.get("drop") or not st.get("key"):
            continue
        for w, rec in (st.get("clues") or {}).items():
            if rec.get("status") == "passed_f":
                units.append((f"u{sha(st['cid'] + '|' + w + '|' + str(args.seed), 10)}", st, w))
    units.sort(key=lambda x: x[0])
    random.Random(f"{args.seed}:verify").shuffle(units)     # mixes writers; labels are never sent
    print(f"[g] units to verify: {len(units)}")
    system = verify_system()
    for i in range(0, len(units), 10):
        batch = units[i:i + 10]
        bid = "batch_" + sha("|".join(u[0] for u in batch), 12)
        bpath = os.path.join(VERIFY_DIR, bid + ".json")
        saved = read_json(bpath)
        if saved is None or "raw_output" not in saved:
            blocks = [unit_block(st, w, uid) for uid, st, w in batch]
            user = json.dumps({"units": blocks}, ensure_ascii=False, indent=1)
            txt = openrouter_chat(OPUS, [{"role": "system", "content": system}, {"role": "user", "content": user}],
                                  purpose="verify", anthropic=True, max_tokens=32000)
            saved = {"batch": bid, "date": today(), "unit_ids": [u[0] for u in batch], "request_units": blocks,
                     "raw_output": txt, "writer_map_private": {uid: w for uid, _, w in batch}}
            write_json(bpath, saved)
        obj = parse_json_obj(saved.get("raw_output"))
        vmap = {}
        if isinstance(obj, dict) and isinstance(obj.get("verdicts"), list):
            for v in obj["verdicts"]:
                if isinstance(v, dict) and isinstance(v.get("id"), str):
                    vmap[v["id"]] = v
        for uid, st, w in batch:
            rec = st["clues"][w]
            v = vmap.get(uid)
            if v is None:
                flags = ["no_verdict"]
            elif not isinstance(v.get("flags"), list):
                flags = ["malformed_verdict"]
            else:
                flags = sorted({(f if f in ALLOWED_FLAGS else "other") for f in v["flags"] if isinstance(f, str)})
            rec["verify"] = {"batch": bid, "uid": uid, "flags": flags, "note": str((v or {}).get("note", ""))[:400]}
            if flags:
                rec.update(status="flagged", reason="verification_flag:" + ",".join(flags))
            else:
                rec.update(status="accepted", reason=None)
            if set(flags) & KEY_FLAGS:
                rec["key_flagged"] = True
            decide_item(st, args)
            save_state(st)
```

**What changed.**

1. **Search hits as records.** Each record is now one search hit. Its JSON is saved as an `h_*.json` snapshot that points back to the full saved search response. `snapshot_text` reads only that hit's own text (no URL, no crawl date). The page is fetched only if the hit does not yield all of author, title, venue and year.

2. **Listings rejected.** Listing pages are rejected at three points, and the drop rule is `listing_page`:
   - by URL: search parameters, TOC, issue, hotword and wiki pages, columns, and host-specific item-URL forms for CNKI, VIP, Wanfang, CiNii, NLC, JSTOR, Cambridge and Brill;
   - by hit content: listing markers, more than one year/issue, or three or more different 《》 titles;
   - after extraction: the extractor calls the page a list, or verified complete entries cover more than one distinct title.

3. **Harvest from items only.** Candidates are built only from item hits. A listing found during harvest seeds at most two item queries (logged in `listing_seeds.jsonl`) and never becomes a record itself.

4. **Record B search.** Record B is found with title+author, title+venue+year, catalogue and ISBN queries instead of issue browses, which returned listings. The query must differ from record A's query. The custodian class must differ, with aggregators counting as one class.

5. **Verifier prompt.** The verifier is told what a `search_hit` snapshot is. Otherwise its old "search snippet = not primary" rule would drop every key.

The verbatim check, the no-repair rule and the drop-on-mismatch rule are unchanged.