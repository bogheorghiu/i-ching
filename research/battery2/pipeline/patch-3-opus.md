Some of these fixes depend on code you didn't send. Those dependencies are listed in **Hooks needed** after the code.

### add JOURNAL_PAGE_TITLE after reg_domain
```python
# Journal-introduction / journal-home pages are listings, not records (owner rule 4).
JOURNAL_PAGE_TITLE = re.compile(
    r"期刊介绍|期刊简介|期刊概况|本刊简介|本刊介绍|刊物简介|杂志简介|关于本刊|期刊首页|投稿须知|投稿指南|征稿启事|编委会|"
    r"about\s+(?:the|this)\s+journal|journal\s+(?:home(?:page)?|information|overview)|aims\s+(?:and|&)\s+scope|"
    r"editorial\s+board", re.I)
JOURNAL_PAGE_PATH = re.compile(
    r"/(?:qkjs|qkjj|qkgk|bkjj|bkjs|gybk|kwjj|tgxz|tgzn|zgqs|bwh)(?:[./?_#-]|$)"
    r"|/(?:about(?:[-_]?(?:us|the[-_]?journal|journal))?|aims[-_]?(?:and|&)[-_]?scope|editorial[-_]?board|"
    r"journal[-_]?(?:info|information|intro|introduction|home))(?:[./?#]|$)", re.I)
SITE_HOME_PATH = re.compile(r"/?(?:(?:index|default|home)\.(?:s?html?|aspx?|php|jsp))?/?", re.I)
JOURNAL_BODY_MARKS = [re.compile(x, re.I) for x in (
    r"主办单位|主办[:：]", r"主管单位|主管[:：]", r"创刊于|创刊时间|创刊年",
    r"国际标准连续出版物号|ISSN\s*[:：]?\s*\d{4}\s*-?\s*\d{3}[\dX]",
    r"国内统一连续出版物号|CN\s*[:：]?\s*\d{2}\s*-\s*\d{4}", r"刊期|出版周期", r"邮发代号",
    r"aims\s+(?:and|&)\s+scope", r"editorial\s+board", r"about\s+(?:the|this)\s+journal",
    r"submission\s+guidelines|instructions\s+for\s+authors|submit\s+(?:an|your)\s+(?:article|manuscript)",
    r"call\s+for\s+papers")]
ARTICLE_BODY_MARK = re.compile(r"摘要|关键词|关键字|abstract|keywords|doi\s*[:：]?\s*10\.", re.I)
```

### replace is_listing_url
```python
def is_listing_url(url):
    """True if the URL is a listing (search result, TOC/issue index, hotword/wiki page, column, journal
    introduction/home page, site root) rather than one work's own item page. Hosts with a known item-URL form
    must match it; other hosts are judged by listing patterns only."""
    hp = url_hp(url)
    host = host_of(url)
    path = hp[len(hp.split("/")[0]):]
    if host.startswith("wiki.") or ".wiki." in host or "wiki.cnki" in hp:
        return True
    if LISTING_PATH.search(path) or JOURNAL_PAGE_PATH.search(path):
        return True
    if SITE_HOME_PATH.fullmatch(path):            # a site/journal root is never one work's record
        return True
    for dom, pat in ITEM_URL:
        if host == dom or host.endswith("." + dom):
            return not re.search(pat, path)
    return False
```

### replace is_listing_text
```python
def is_listing_text(text, title=""):
    """Content test on a search hit: listing or journal-page markers in its title, listing markers in its text,
    a journal-introduction profile (>=3 journal markers and no article markers), more than one year/issue, or
    several different 《》 titles mean the hit describes a listing, not one work."""
    if title:
        tn = unicodedata.normalize("NFKC", str(title))
        if LIST_TITLE_MARK.search(tn) or JOURNAL_PAGE_TITLE.search(tn):
            return True
    t = unicodedata.normalize("NFKC", str(text or ""))
    if LIST_BODY_MARK.search(t):
        return True
    if sum(1 for rx in JOURNAL_BODY_MARKS if rx.search(t)) >= 3 and not ARTICLE_BODY_MARK.search(t):
        return True
    issues = {(m.group(1), m.group(2)) for m in re.finditer(r"((?:19|20)\d\d)\s*年\s*第?\s*0?(\d{1,2})\s*期", t)}
    if len(issues) > 1:
        return True
    quoted = {norm(x) for x in re.findall(r"《([^《》]{2,60})》", t) if norm(x)}
    return len(quoted) >= 3
```

### add authors_match after author_key
```python
NAME_DROP = {"author", "authors", "editor", "editors", "ed", "eds", "edited", "by", "translator", "translators",
             "trans", "tr", "compiler", "comp", "contributor", "illustrator", "writer", "joint", "introduction",
             "foreword", "preface", "jr", "sr", "dr", "prof", "professor"}
NAME_PARTICLES = {"van", "von", "der", "den", "de", "du", "di", "da", "del", "della", "dos", "das", "la", "le",
                  "ter", "ten", "bin", "al"}
LIFE_DATES = re.compile(
    r"\b(?:b|d|fl|ca|c|born|died|active|approximately)\.?\s*\d{3,4}\??"
    r"|\d{3,4}\??\s*[-–—]\s*(?:\d{3,4}\??)?"
    r"|\b\d{1,2}(?:st|nd|rd|th)\s+cent(?:ury|\.)?"
    r"|\d+", re.I)

def _name_tokens(seg):
    seg = LIFE_DATES.sub(" ", seg)
    return [t for t in re.findall(r"[a-z]+", seg) if t not in NAME_DROP and t not in ROLE_EN]

def _latin_people(a):
    """Alternative parses of a Latin-script author string into persons (surname_set_or_None, tokens).
    'Surname, Given, dates, role' gives a known surname; a 2-segment comma chunk is also tried as two persons."""
    s = deaccent(unicodedata.normalize("NFKC", str(a or "")).lower())
    chunks = [ch for ch in re.split(r"[;；|/&+]|\band\b|\bwith\b", s) if _name_tokens(ch)]
    options = []
    for ch in chunks:
        segs = [t for t in (_name_tokens(x) for x in re.split(r"[,，]", ch)) if t]
        opts = [[(None, tuple(t)) for t in segs]]
        if len(segs) == 2:
            opts.insert(0, [(frozenset(segs[0]), tuple(segs[0] + segs[1]))])
        options.append(opts)
    if not options:
        return []
    return [[p for grp in combo for p in grp] for combo in itertools.islice(itertools.product(*options), 32)]

def _person_match(p, q):
    """Surname plus at least one given name shared, order-insensitive."""
    shared = set(p[1]) & set(q[1])
    if len(shared) < 2:
        return False
    for x, y in ((p, q), (q, p)):
        if x[0] is None:
            continue
        core = {t for t in x[0] if t not in NAME_PARTICLES} or set(x[0])
        if not core <= shared or not (shared - x[0]):
            return False
        if y[0] is None and not core & {y[1][0], y[1][-1]}:    # surname must sit at an end of the other name
            return False
    if p[0] is None and q[0] is None and not ({p[1][0], p[1][-1]} & {q[1][0], q[1][-1]} & shared):
        return False
    return True

def authors_match(a, b):
    """Author equality for cross-record checks. Exact author_key equality always matches. Strings containing CJK
    keep the exact rule only (no loosening). Latin-script names: catalogue forms ('Eyferth, Jan Jacob Karl,
    1962-') match 'Jacob Eyferth' when surname + >=1 given name agree, every person on each side matched."""
    sa = "; ".join(map(str, a)) if isinstance(a, list) else str(a or "")
    sb = "; ".join(map(str, b)) if isinstance(b, list) else str(b or "")
    if author_key(sa) == author_key(sb):
        return True
    if has_cjk(sa) or has_cjk(sb):
        return False
    for pa in _latin_people(sa):
        for pb in _latin_people(sb):
            if pa and pb and all(any(_person_match(p, q) for q in pb) for p in pa) \
                    and all(any(_person_match(q, p) for p in pa) for q in pb):
                return True
    return False
```

### add author_gap after verify_entry
```python
def author_gap(d):
    """From an item_entry diag: the single verified hit entry if it has title, venue and year but no author
    (owner rule 3). Returns (entry_or_None, note)."""
    ents = d.get("verified")
    if not isinstance(ents, list):
        return None, "no_verified_dicts_in_diag"
    if len(ents) != 1:
        return None, "not_single_entry"
    v = ents[0]
    if v.get("author"):
        return None, "author_present"
    if not (v.get("title") and v.get("venue") and v.get("year")):
        return None, "title_venue_year_incomplete"
    if venue_key(v["title"]) == venue_key(v["venue"]):
        return None, "title_is_venue"
    return dict(v), "author_gap"

def merge_author(gap, d, F):
    """Take the author from the hit's own fetched page (fields verified on that page) into the hit entry.
    Same work required: the hit title is on the page; the page entry's title matches; year and venue do not conflict.
    Returns (merged_entry_or_None, result)."""
    if not loose_title_in(gap["title"], F["text"]):
        return None, "hit_title_absent_on_page"
    auths = {}
    for v in d.get("verified") or []:
        if not v.get("author") or not v.get("title"):
            continue
        if not (loose_title_in(gap["title"], v["title"]) or loose_title_in(v["title"], gap["title"])):
            continue
        if v.get("year") and v["year"] != gap["year"]:
            return None, "year_conflict"
        if v.get("venue"):
            a, b = venue_key(v["venue"]), venue_key(gap["venue"])
            if a != b and a not in b and b not in a:
                return None, "venue_conflict"
        auths[author_key(v["author"])] = v["author"]
    if not auths:
        return None, "author_not_on_page"
    if len(auths) > 1:
        return None, "ambiguous_author"
    return dict(gap, author=next(iter(auths.values()))), "ok"
```

### replace record_from_hit
```python
def record_from_hit(hit, idx, sfile, query, route, url, mode, target=None, diag=None):
    """Record from a search hit: the hit's JSON is the snapshot; the page is fetched (once) only if the hit lacks a
    field. If the hit verifies title/venue/year but lacks the author, the author may come from that fetched page
    (record keeps both snapshots; field_sources names the page for 'author').
    Returns (entry, record_dict, None) or (None, None, reason). diag (optional dict) receives a 'steps' log."""
    diag = {} if diag is None else diag
    steps = diag.setdefault("steps", [])
    why = "field_unverified"
    hfn, gap = None, None
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
            if why == "field_unverified":
                gap, d["author_gap"] = author_gap(d)
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
    F = ds_fetch(url, route)                      # single fetch: missing-field fallback and author check
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
    if why2 != "listing_page" and gap is not None:
        m, res = merge_author(gap, d, F)
        steps.append({"step": "author_from_page", "result": res, "snapshot": F["file"]})
        if m is not None:
            return m, {"url": url, "snapshot_file": hfn, "snapshot_kind": "search_hit+page_author",
                       "author_snapshot_file": F["file"], "field_sources": {"author": F["file"]},
                       "search_snapshot": sfile, "hit_index": idx, "query": query, "route": route,
                       "date": F["date"] or today()}, None
    return None, None, (why2 if why2 == "listing_page" else why)
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
    a_dom = reg_domain(host_of(c["url"]))
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
                skip("unclassified"); continue          # includes booksellers (BANNED): never records
            classes_seen[cl] = classes_seen.get(cl, 0) + 1
            # Different custodian class required (CNKI/VIP/Wanfang = one aggregator class, never pair), EXCEPT
            # owner deviation: library catalogues of different institutions (registered domains) pair.
            if cl == a_cls and cl != "library":
                skip("same_class"); continue
            if reg_domain(host_of(u)) == a_dom:
                skip("same_domain"); continue
            if is_listing_url(u) or is_listing_text(hit_text(r), str(r.get("title", ""))):
                skip("listing"); continue
            if not loose_title_in(entry["title"], hit_text(r)):
                skip("title_absent"); continue
            tried += 1
            e, rec, why = record_from_hit(r, i, sfile, q, rt, u, "B", target)
            if e is not None:
                lib_pair = cl == a_cls
                st["recB"] = dict(rec, custodian_class=cl,
                                  pairing="cross_institution_library" if lib_pair else "cross_class",
                                  prereg_deviation="owner: library catalogues of different institutions"
                                  if lib_pair else None,
                                  institutions=[a_dom, reg_domain(host_of(u))])
                return
            fails[why] = fails.get(why, 0) + 1
    drop(st, "no_second_record", "b",
         f"no independent item record found ({tried} tried; {searches} searches, {n_hits} hits; "
         f"A class={a_cls}; skipped={json.dumps(skips, ensure_ascii=False)}; "
         f"classes_seen={json.dumps(classes_seen, ensure_ascii=False)}; failed={json.dumps(fails, ensure_ascii=False)})")
```

**Fix 1 (library pairs, `stage_b`).** The `same_class` skip now exempts `library`. A library hit then passes only if its registered domain differs from record A's, using the existing `same_domain` check. CNKI/VIP/Wanfang still collapse to one aggregator class and never pair. Booksellers still fail `classify` through `BANNED`. Every such pair is tagged in `recB` with `pairing`, `prereg_deviation` and both institution domains, so the deviation can be counted in the write-up. The three `no_second_record` samples had 19–35 library hits each, and all were skipped as `same_class`; they now go on to the listing and title checks.

**Fix 2 (author matching, `authors_match`).** Exact `author_key` equality still matches as before. If either string contains CJK characters, the old exact rule is the only rule, so Chinese name matching is not loosened. For Latin-script names, life dates (`1962-`, `b. 1962`, `fl.`, centuries) and role words are stripped first. `Surname, Given` is parsed as surname plus given names. A match then needs:
- the surname plus at least one given name shared, in any order;
- the surname at an end of the other form;
- every person on each side matched.

`Eyferth, Jan Jacob Karl, 1962-` therefore matches `Jacob Eyferth`. `J. Eyferth` does not, because initials are not expanded. Romanised (pinyin) Chinese names now tolerate extra given-name tokens on one side; tell me if you want that blocked too.

**Fix 3 (author from the hit's page, `record_from_hit`, `author_gap`, `merge_author`).** This applies when the hit verifies title, venue and year (all three), the title is not just the journal name, and only the author is missing. The single existing fetch is then reused:
- the hit's title must appear on the fetched page;
- a page entry with a matching title must carry a verified author;
- year and venue must not conflict, and there must be exactly one distinct author.

The record keeps the hit as `snapshot_file`, adds `author_snapshot_file`, and sets `field_sources={"author": ...}`. If the fetch fails or any check fails, the drop is the same as before. None of the three run-3 `field_unverified` samples is rescued, which is correct:
- c1c20: the fetch failed, and its "title" was only the journal name.
- c28839: the hit had no year, and the fetched page showed no author.
- c0378: now a listing (fix 4).

**Fix 4 (journal pages, `is_listing_url`, `is_listing_text`).** These are now listings:
- URL paths for journal introduction, contribution and editorial-board pages (`qkjs`, `qkjj`, `tgxz`, `bwh`, `/about`, `/aims-and-scope`, …);
- site roots and `index`/`default` pages;
- hit titles such as `期刊介绍`, `关于本刊` or `About the journal`;
- hit text with at least 3 journal-profile markers (主办/主管单位, ISSN, CN, 刊期, 邮发代号, aims & scope, editorial board, …) and no article marker (摘要/关键词/abstract/DOI).

c0378 (`qkjs.htm`, titled 期刊介绍) now drops as `listing_page` at stage b.

**Hooks needed:**
1. Add `import itertools` at the top of the file.
2. Stage d must call `authors_match(a, b)` where it currently compares authors (presumably `author_key(a) == author_key(b)`). Send stage d if it's different.
3. Fix 3 needs `item_entry` to put the verified dicts it builds into the diag, next to `verified_fields`: `diag.setdefault("verified", []).append(out)`. Without that, the step logs `no_verified_dicts_in_diag` and behaviour is unchanged. Send `item_entry` and I'll do it.
4. Merged entries take their shape from `verify_entry` output. Any check that re-verifies the author against `snapshot_file` must use `field_sources` instead.

**Not changed, but worth looking at:**
- cf48 is a Kyoto `opac_authority` page (an author authority listing), not an item record. It slipped past `ITEM_URL`. Its venue mismatch (Asia Center vs Press) stands.
- Under the new pairing rule, Japanese university OPACs and CiNii often show the same NACSIS-CAT record (`BB…` IDs), and WorldCat mirrors OCLC master records. "Different institution" may then still be one shared record; you may want to tag or exclude union catalogues.