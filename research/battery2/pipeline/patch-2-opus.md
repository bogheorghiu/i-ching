## Diagnosis

**`no_second_record` (9).** The query list was not empty. If `b_queries` had returned nothing, `stage_b` would have dropped with `"no route to a second record"`. The detail `"(0 tried)"` means searches did run, but every hit was discarded by the pre-filters before `tried += 1`. The pre-filters are: unclassified, same custodian class as A, same domain, listing, title absent. Those skips were not counted, so the detail could not say which filter was responsible.

Both samples have a **library** record A: the UIBE OPAC and the Kyoto KULINE OPAC. Every query in the zh set routes toward other library catalogues:
- title + author
- title + publisher + year
- `CiNii {t}`, which is a union catalogue of libraries.

Results from those queries are either the same class (library, skipped by the independence rule) or bookstores and portals, which `classify` rejects. Nothing remains to try.

The ISBN route is also weak:
- **UIBE sample:** the ISBN is a hyphenated ISBN-10 after `ISBN/价格： |`, `7-301-10179-1`. It likely escapes `find_isbns`, and no ISBN-13 form, `9787301101792`, is searched.
- **Kyoto sample:** the ISBN-13 is present, `9787532564545`, but an ISBN search alone mostly returns libraries and bookstores.

**`field_unverified` (17).** `snapshot_A_head` is null because the drop happens before `recA` is saved. Nothing about record A's attempt is persisted: no hit-snapshot name, no dropped fields, no fetch status. So the per-candidate cause cannot be proven from this run. What the evidence does show:

- **c0378cdc5b5:** the page is a journal-information page (`hint_title` "期刊介绍", `qkjs.htm`). It was reached by an issue-TOC query (`…2019年第1期 目录`). It describes no single work, so rejecting it is correct.
- **c1c20e53b75:** the hit is titled only with the journal name "周易研究". The URL `…202401001` looks like an article record, so the hit text carries no article-level fields. The page fallback then either failed to fetch or yielded nothing verifiable. `record_from_hit` reports a failed fetch as `field_unverified` whenever a hit existed, which masks the real cause.
- **Pattern:** journal-level harvest queries (`目录`, `周易研究 2024 周易 论文`) produce journal pages rather than item records.

**Verification leak.** I also found a leak in the verbatim check. `extract`/`verify_entry` read `snapshot_text(hit file)`. That is the whole saved hit JSON, including `query`, `route`, `url`, `date` and `site_name`. A year or a journal name typed into *our own query* could therefore "verify" a field. JSON escaping also turns line breaks into literal `n` characters after `norm`, which can break multi-line matches.

**`listing_page` (2).** No samples were provided, so this cannot be diagnosed. The rule is left unchanged.

## Fixes

### add verify_source after hit_text
```python
def verify_source(snapfile):
    """The only text a record may be extracted from and verified against. For a saved search hit this is the hit's
    own title/snippet/summary/content/description (hit_text) - never the query, route, URL, crawl date or site name
    we stored alongside it, so nothing we typed can verify a field. Other snapshots: their page text."""
    d = read_json(os.path.join(SNAP, snapfile)) if str(snapfile).endswith(".json") else None
    if isinstance(d, dict) and d.get("kind") == "search_hit":
        return hit_text(d.get("response"))
    return snapshot_text(snapfile)
```

### replace extract
```python
def extract(snapfile, url, mode, target=None):
    # v2: verification source changed (verify_source), so old cached extractions are not reused
    key = f"{snapfile}__{mode}__v2__{sha(json.dumps(target, ensure_ascii=False) if target else '')}"
    path = os.path.join(EXTRACT_DIR, key + ".json")
    cached = read_json(path)
    if cached is not None:
        return cached
    raw = verify_source(snapfile)
    user = f"URL: {url}\n\nPAGE TEXT (may be truncated):\n{raw[:MAX_PAGE_CHARS]}"
    if mode == "B" and target:
        user += ("\n\nReturn ONLY the entry (if any) for the work whose title is close to: " + target["title"] +
                 (" (author: " + target["author"] + ")" if target.get("author") else "") +
                 "\nUse exactly this page's own wording, which may differ from the hint. If no such entry is on the page, return \"entries\": [].")
    txt = openrouter_chat(EXTRACT_MODEL, [{"role": "system", "content": EXTRACT_SYSTEM}, {"role": "user", "content": user}],
                          purpose=f"extract:{mode}", anthropic=False)
    parsed = parse_json_obj(txt) if txt is not None else None
    entries = []
    if parsed and isinstance(parsed.get("entries"), list):
        for e in parsed["entries"][:30]:
            if isinstance(e, dict):
                v, d = verify_entry(e, raw)
                entries.append({"verified": v, "dropped_fields": d})
    res = {"snapshot_file": snapfile, "mode": mode, "target": target, "date": today(), "raw_output": txt,
           "parse_ok": parsed is not None, "call_rejected": txt is None, "entries": entries}
    write_json(path, res)
    return res
```

### replace item_entry
```python
def item_entry(snapfile, url, mode, target=None, diag=None):
    """Extract + verbatim-verify one snapshot and accept it only as an ITEM record. Returns (entry, None) or
    (None, reason). A page the extractor calls a list, or with complete verified entries for more than one distinct
    title, is a listing and is rejected (never repaired, never narrowed to one entry). If diag is a dict it is filled
    with what was seen (for the drop log only; it never affects the decision)."""
    ex = extract(snapfile, url, mode, target)
    parsed = parse_json_obj(ex.get("raw_output")) or {}
    if diag is not None:
        diag.update({"snapshot": snapfile, "page_kind": parsed.get("page_kind"), "n_entries": len(ex["entries"]),
                     "verified_fields": [sorted(k for k in e["verified"] if k != "work_type_llm") for e in ex["entries"][:5]],
                     "dropped_fields": [e["dropped_fields"] for e in ex["entries"][:5]]})
    if ex["call_rejected"] or not ex["parse_ok"]:
        return None, "extraction_failed"
    full = [e["verified"] for e in ex["entries"] if complete(e["verified"])]
    if parsed.get("page_kind") == "list" or len({norm(v["title"]) for v in full}) > 1:
        return None, "listing_page"
    if not full:
        return None, "field_unverified"
    return full[0], None
```

### replace record_from_hit
```python
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
```

### add isbn_variants after record_from_hit
```python
def _isbn10_ok(d):
    if not re.fullmatch(r"\d{9}[\dX]", d):
        return False
    return sum((10 - i) * (10 if c == "X" else int(c)) for i, c in enumerate(d)) % 11 == 0

def _isbn13_ok(d):
    if not re.fullmatch(r"97[89]\d{10}", d):
        return False
    return sum(int(c) * (1 if i % 2 == 0 else 3) for i, c in enumerate(d)) % 10 == 0

def isbn_variants(text):
    """Checksum-valid ISBNs written in the record text (ISBN-10 or -13, hyphenated or not, e.g. 'ISBN/价格： |
    7-301-10179-1'), each with its other form (10<->13). Only numbers the record itself prints are used."""
    t = unicodedata.normalize("NFKC", text or "")
    raw = [m.group(1) for m in re.finditer(r"ISBN[^\dXx]{0,15}([\dXx][\dXx\- ]{8,17})", t, re.I)]
    try:
        raw += list(find_isbns(t))
    except Exception:
        pass
    out = []
    def add(d):
        if d not in out:
            out.append(d)
    for r in raw:
        d = re.sub(r"[\- ]", "", str(r)).upper()
        for cand in (d[:13], d[:10]):
            if len(cand) == 13 and _isbn13_ok(cand):
                add(cand)
                if cand.startswith("978"):
                    core = cand[3:12]
                    c10 = (11 - sum((10 - i) * int(c) for i, c in enumerate(core)) % 11) % 11
                    add(core + ("X" if c10 == 10 else str(c10)))
                break
            if len(cand) == 10 and _isbn10_ok(cand):
                add(cand)
                core = "978" + cand[:9]
                c13 = (10 - sum(int(c) * (1 if i % 2 == 0 else 3) for i, c in enumerate(core)) % 10) % 10
                add(core + str(c13))
                break
    return out
```

### replace b_queries
```python
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
```

## Summary

**`no_second_record`.** The queries did run. Every hit was then excluded before any record attempt, and the skips were uncounted. With a library record A, every zh query led to other libraries (same class, correctly excluded) or to unclassifiable bookstores and portals. The changes:
- Books now get publisher-directed queries, so a different custodian class can actually be reached.
- ISBNs are searched in both forms; the ISBN-10 is checksum-validated and its ISBN-13 form derived.
- The drop detail now counts each skip reason, the classes seen, and the record-attempt failures.

**`field_unverified`.** The run kept no evidence about record A, so the per-candidate cause cannot be proven. The samples point to two causes:
- Journal-level pages (a journal-information page, a hit titled only with the journal name) produced by issue/journal-level harvest queries. Rejecting these is correct.
- Fetch failures reported as `field_unverified`.

The A drop now logs each step: hit title, verified and dropped fields, page kind, and fetch status. The next run will show which cause applies to each candidate. If journal pages dominate, the fix belongs in the harvest queries; that code is not shown here.

**Verification leak.** Extraction and verification now use only the hit's own text (`verify_source`), not the stored query, route, URL or date. This tightens the verbatim rule; the extraction cache is versioned so old results are not reused.

**`listing_page`.** No samples were given, so it was not diagnosed and is unchanged.

Independence, the verbatim check and the no-repair rule are all untouched or stricter.