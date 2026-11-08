### add host_of after parse_json_obj
```python
def host_of(url):
    """Lower-cased host without port or leading 'www.'; '' if the URL cannot be parsed."""
    from urllib.parse import urlsplit
    try:
        h = urlsplit(str(url)).hostname or ""
    except ValueError:
        h = ""
    h = h.lower().rstrip(".")
    return h[4:] if h.startswith("www.") else h
```

### add load_host_stats after host_of
```python
def load_host_stats(extra_paths, min_attempts=3):
    """Hosts with >= min_attempts uncached DeepSeek fetches and none with status 200, counted over this
    workdir's tools.jsonl plus any --host-stats files (each file read once, by real path)."""
    paths, seen_real = [], set()
    for p in [os.path.join(W, "tools.jsonl")] + list(extra_paths or []):
        rp = os.path.realpath(p)
        if rp in seen_real or not os.path.exists(p):
            continue
        seen_real.add(rp)
        paths.append(p)
    att, ok = collections.Counter(), collections.Counter()
    for p in paths:
        for t in read_jsonl(p):
            if not isinstance(t, dict) or t.get("tool") != "fetch" or t.get("cached") or "status" not in t:
                continue
            h = host_of(t.get("url", ""))
            if not h:
                continue
            att[h] += 1
            if t.get("status") == 200:
                ok[h] += 1
    blocked = {h: {"fetch_attempts": att[h], "fetch_200": 0} for h in att if att[h] >= min_attempts and ok[h] == 0}
    return blocked, paths
```

### replace harvest_hit
```python
def harvest_hit(r, idx, sfile, q, cell, meta, rank, offset, allowed, seen, seed_from=None, blocked=None):
    """Register one search hit as a candidate if it is an item record; returns 'added', 'listing', 'skipped' or None."""
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
    h = host_of(u)
    if blocked and h in blocked:            # host steering: not a candidate, logged for the sampling-frame report
        jlog(os.path.join(W, "harvest_skips.jsonl"),
             {"ts": nowiso(), "reason": "host_unfetchable", "host": h, "url": u, "hint_title": hint,
              "cell": list(cell), "query": q, "search_snapshot": sfile, "hit_index": idx, "seed_from": seed_from,
              "fetch_attempts": blocked[h]["fetch_attempts"], "fetch_200": blocked[h]["fetch_200"], "date": today()})
        return "skipped"
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
    blocked, stat_paths = load_host_stats(getattr(args, "host_stats", None))
    print(f"[a] host steering: {len(blocked)} unfetchable hosts from {len(stat_paths)} tools log(s)"
          + (": " + ", ".join(sorted(blocked)[:12]) if blocked else ""))
    n_skipped = 0
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
            added, skipped, listings = 0, 0, []
            for k, r in enumerate(window):
                out = harvest_hit(r, eff + k, sfile, q, cell, meta, eff + k + 1, eff, allowed, seen, blocked=blocked)
                if out == "added":
                    added += 1
                    have[cell] += 1
                elif out == "skipped":
                    skipped += 1
                elif out == "listing":
                    listings.append(r)
            for r in listings[:3]:              # a listing only seeds item queries; it is never a record
                for sq in seed_queries(r, cell, meta):
                    if sq in seeded or have[cell] >= quota:
                        continue
                    seeded.add(sq)
                    res2, sf2 = ds_search(sq, 10, route=f"listing_seed: {r_url(r)}")
                    n2, s2 = 0, 0
                    for j, r2 in enumerate(res2):
                        out2 = harvest_hit(r2, j, sf2, sq, cell, meta, j + 1, 0, allowed, seen,
                                           seed_from=r_url(r), blocked=blocked)
                        if out2 == "added":
                            n2 += 1
                        elif out2 == "skipped":
                            s2 += 1
                    have[cell] += n2
                    added += n2
                    skipped += s2
                    jlog(seed_log, {"cell": list(cell), "listing_url": r_url(r), "harvest_query": q, "seed_query": sq,
                                    "search_snapshot": sf2, "added": n2, "skipped_host": s2, "date": today()})
            n_skipped += skipped
            jlog(os.path.join(W, "harvest_queries.jsonl"), {"cell": list(cell), "query": q, "count": offset + 10,
                                                           "offset_requested": offset, "offset_used": eff,
                                                           "returned": len(res), "listings_seen": len(listings),
                                                           "added": added, "skipped_host": skipped, "date": today()})
            nq[cell] += 1
    print(f"[a] candidates: {dict(have)}; hits skipped on unfetchable hosts this run: {n_skipped}")
```

### add record_excerpts after drop
```python
def record_excerpts(st):
    """Sanitised record blocks (A, B) with excerpts around the key fields; shared by pre-screen and verification."""
    k, forms = st["key"], st.get("key_forms", {})
    recs = []
    for tag, r in zip(("A", "B"), st["records"]):
        f = forms.get(tag) or k
        txt = snapshot_text(r["snapshot_file"])
        recs.append({"url": r["url"], "custodian_class": r["custodian_class"], "route": sanitize(r["route"])[:200],
                     "snapshot_kind": r.get("snapshot_kind", "fetch"),
                     "excerpt": excerpt(txt, [f.get("title"), f.get("venue"), f.get("author"), f.get("volume_issue")])})
    return recs
```

### replace unit_block
```python
def unit_block(st, w, uid):
    k = st["key"]
    return {"id": uid, "key": {x: k.get(x) for x in ("author", "title", "venue", "year", "volume_issue")},
            "work_type": st["stratum"]["type"], "records": record_excerpts(st), "clue": st["clues"][w]["clue"]}
```

### add prescreen_system after unit_block
```python
def prescreen_system():
    return (
        "You screen candidate bibliographic items before a more expensive check. You see one work: its key fields "
        "(author, title, venue, year, volume_issue), excerpts from the catalogue or journal records it was taken from, "
        "the target cell (type and language) and the field the harvest query was aimed at. Answer two questions.\n\n"
        "(a) on_topic: Is this work about the target field: Yijing/Zhouyi studies, excavated or transmitted early "
        "Chinese texts, early China, or Chinese philosophy of that period? A work on another region, on modern or "
        "contemporary society, or on an unrelated subject is not on topic.\n"
        "(b) type_match: Does the work's type match the cell?\n"
        "  - article = one article in a journal issue, or one article or chapter in an edited volume.\n"
        "  - book = a monograph, or a single edition of a text.\n"
        "  - An edited serial volume as a whole (one numbered volume of a series of collected papers, e.g. a "
        "volume titled like 《…研究》第六輯) is NOT an article. A journal issue as a whole is neither an article nor a book.\n\n"
        "Answer each question with \"yes\", \"no\" or \"unsure\", plus a one-line reason. Answer \"no\" only when "
        "the key and excerpts make it clear; if the evidence is thin, answer \"unsure\". Do not judge whether the "
        "record is accurate or whether the key is correct.\n\n"
        "Output only this JSON object:\n"
        "{\"on_topic\": \"yes|no|unsure\", \"on_topic_reason\": \"...\", "
        "\"type_match\": \"yes|no|unsure\", \"type_reason\": \"...\"}")
```

### add prescreen_call after prescreen_system
```python
def prescreen_call(st, cand):
    """One cheap call per item (cid), cached on disk with its raw output. Runs in a worker thread: no state writes."""
    path = os.path.join(W, "prescreen", f"{st['cid']}.json")
    saved = read_json(path)
    if saved is not None and "raw_output" in saved:
        return saved
    k = st["key"]
    cell = list(cand.get("cell") or st.get("cell") or [st["stratum"]["type"], st["stratum"].get("language")])
    meta = cand.get("meta") or st.get("meta") or {}
    req = {"key": {x: k.get(x) for x in ("author", "title", "venue", "year", "volume_issue")},
           "records": record_excerpts(st),
           "cell": {"type": cell[0], "language": cell[1] if len(cell) > 1 else None},
           "harvest_field": meta.get("field")}
    user = json.dumps(req, ensure_ascii=False, indent=1)
    txt = openrouter_chat(EXTRACT_MODEL, [{"role": "system", "content": prescreen_system()},
                                          {"role": "user", "content": user}],
                          purpose="prescreen", anthropic=False)
    saved = {"cid": st["cid"], "date": today(), "model": EXTRACT_MODEL, "request": req, "raw_output": txt,
             "request_rejected": txt is None}
    write_json(path, saved)
    return saved
```

### add apply_prescreen after prescreen_call
```python
def apply_prescreen(st, saved):
    """Drop-only. An explicit 'no' drops; 'yes', 'unsure', missing or unparseable output never drops."""
    def yn(v):
        if isinstance(v, bool):
            return "yes" if v else "no"
        if isinstance(v, str):
            s = v.strip().strip(".").lower()
            if s in ("yes", "no", "unsure"):
                return s
        return None
    obj = parse_json_obj(saved.get("raw_output"))
    obj = obj if isinstance(obj, dict) else {}
    a, b = yn(obj.get("on_topic")), yn(obj.get("type_match"))
    ra, rb = str(obj.get("on_topic_reason", ""))[:240], str(obj.get("type_reason", ""))[:240]
    st["prescreen"] = {"file": f"prescreen/{st['cid']}.json", "parsed": bool(obj), "on_topic": a,
                       "on_topic_reason": ra, "type_match": b, "type_reason": rb, "date": today()}
    if a == "no":
        rule, detail = "prescreen:off_topic", ra + (f" | type_match=no: {rb}" if b == "no" else "")
    elif b == "no":
        rule, detail = "prescreen:type_mismatch", rb
    else:
        return None
    st.pop("accepted", None)
    drop(st, rule, "g_pre", detail)
    return rule
```

### add stage_prescreen after apply_prescreen
```python
def stage_prescreen(args, states):
    """Cheap pre-screen of every item that has a unit about to go to Opus. One call per cid covers all its units
    (the inputs do not include the clue). Can only drop."""
    from concurrent.futures import ThreadPoolExecutor
    cmap = {c["cid"]: c for c in read_jsonl(cand_path())}
    todo = [st for st in states if not st.get("drop") and st.get("key")
            and any(r.get("status") == "passed_f" for r in (st.get("clues") or {}).values())]
    os.makedirs(os.path.join(W, "prescreen"), exist_ok=True)
    print(f"[g0] pre-screen: {len(todo)} items")
    dropped = collections.Counter()
    with ThreadPoolExecutor(max_workers=max(1, args.workers)) as ex:
        futs = [(st, ex.submit(prescreen_call, st, cmap.get(st["cid"], {}))) for st in todo]
        for st, fut in futs:
            saved = fut.result()          # InfraError / BudgetExceeded propagate; finished calls are already cached
            rule = apply_prescreen(st, saved)
            save_state(st)
            if rule:
                dropped[rule] += 1
    print(f"[g0] pre-screen drops: {dict(dropped) or 'none'}")
```

### replace stage_g
```python
def stage_g(args, states):
    stage_prescreen(args, states)                            # drop-only; dropped items are skipped below
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

### replace write_report
```python
def write_report(args, states, chosen, rest, dropped, note):
    L = []
    L.append("# Battery 2 key building: REPORT\n")
    L.append(f"Generated {nowiso()} by build_keys.py (seed `{args.seed}`, target {args.target}, writers "
             f"{','.join(args.writers)}, --max-usd {args.max_usd}).\n")
    if note:
        L.append(f"**Run note:** {note}\n")
    cands = read_jsonl(cand_path())
    L.append("## Funnel\n")
    fun = collections.OrderedDict([
        ("harvested candidates", len(cands)),
        ("processed (state saved)", len(states)),
        ("record A fetched + fields verified", sum(1 for s in states if s.get("entryA"))),
        ("independent record B found", sum(1 for s in states if s.get("recB"))),
        ("key verified by code comparison", sum(1 for s in states if s.get("key"))),
        ("recoverable (search finds key)", sum(1 for s in states if (s.get("recover") or {}).get("rank"))),
        ("≥1 clue passed leakage + identifiability", sum(1 for s in states if any(
            c.get("status") in ("passed_f", "accepted", "flagged") for c in (s.get("clues") or {}).values()))),
        ("accepted after Opus verification", sum(1 for s in states if s.get("accepted") and not s.get("drop"))),
        ("written to items.jsonl", len(chosen)), ("surplus in reserve.jsonl", len(rest)),
        ("pending (no decision yet)", sum(1 for s in states if not s.get("drop") and not s.get("accepted")))])
    for k, v in fun.items():
        L.append(f"- {k}: {v}")
    proc = len(states)
    L.append(f"\nYield: {len(chosen) + len(rest)} accepted / {proc} processed candidates"
             f" = {((len(chosen) + len(rest)) / proc * 100 if proc else 0):.1f}%.\n")
    # --- sampling frame (host steering)
    L.append("## Sampling frame\n")
    srcs = ["tools.jsonl (this workdir)"] + [f"`{p}`" for p in (getattr(args, "host_stats", None) or [])]
    L.append("Host steering in harvest: a search hit that would otherwise be registered is skipped when its host has "
             "≥3 uncached DeepSeek fetch attempts and none returned status 200, counted over "
             + ", ".join(srcs) + " at harvest time. Skips are logged in harvest_skips.jsonl and are not counted as "
             "candidates.\n")
    skips = read_jsonl(os.path.join(W, "harvest_skips.jsonl"))
    if not skips:
        L.append("No hits were skipped.\n")
    else:
        hs = {}
        for s in skips:
            h = hs.setdefault(s.get("host"), {"hits": 0, "urls": set(), "cells": collections.Counter(), "att": 0})
            h["hits"] += 1
            h["urls"].add(s.get("url"))
            h["cells"]["/".join(s.get("cell") or [])] += 1
            h["att"] = max(h["att"], int(s.get("fetch_attempts") or 0))
        L.append("| host | skipped hits | distinct URLs | by cell | uncached fetch attempts (none 200) |")
        L.append("|---|---|---|---|---|")
        for host, h in sorted(hs.items(), key=lambda x: (-x[1]["hits"], str(x[0]))):
            cells = ", ".join(f"{c} {n}" for c, n in sorted(h["cells"].items()))
            L.append(f"| {host} | {h['hits']} | {len(h['urls'])} | {cells} | {h['att']} |")
        n_urls = len({s.get("url") for s in skips})
        L.append(f"\nItems on these {len(hs)} hosts cannot enter the set: {len(skips)} hits ({n_urls} distinct URLs) "
                 "were skipped. The item set therefore samples works whose records sit on hosts the DeepSeek fetch "
                 "tool can read, not every work the searches return.")
        early = [c for c in cands if host_of(c.get("url", "")) in hs]
        if early:
            acc_ids = {s["cid"] for s in chosen + rest}
            L.append(f"Exception: {len(early)} candidates on these hosts were registered before steering applied and "
                     f"were processed normally ({sum(1 for c in early if c['cid'] in acc_ids)} accepted).")
        L.append("")
    L.append("## Items by stratum (items.jsonl)\n")
    for dim in ("fame", "type", "language", "decade"):
        c = collections.Counter(s["stratum"][dim] for s in chosen)
        L.append(f"- {dim}: " + (", ".join(f"{k} {v}" for k, v in sorted(c.items())) or "none"))
    L.append(f"- post-cutoff (year ≥ {args.cutoff_year}): {sum(1 for s in chosen if s['stratum'].get('post_cutoff'))}")
    tgt = ", ".join(f"{t}/{l} {round(args.target * sh)}" for (t, l), sh in CELLS.items())
    L.append(f"- type×language targets: {tgt}")
    L.append("\nFame is set only from a citation count or holdings count stated on a primary record "
             f"(citations ≥{FAME_CIT[0]} famous, ≥{FAME_CIT[1]} mid; holdings ≥{FAME_HOLD[0]}/≥{FAME_HOLD[1]}); "
             "otherwise `unknown`. Fame and decade strata are reported, not enforced by quota.\n")
    L.append("## Drops by rule (item level)\n")
    dc = collections.Counter(d["rule"] for d in dropped)
    for k, v in dc.most_common():
        L.append(f"- {k}: {v}")
    L.append("\nDrops by rule and type×language:\n")
    dcc = collections.Counter((d["rule"], "/".join(d["cell"])) for d in dropped)
    for (r, c), v in sorted(dcc.items()):
        L.append(f"- {r} | {c}: {v}")
    L.append("\n`prescreen:*` drops come from a cheap EXTRACT_MODEL screen run before Opus; it can only drop "
             "(an explicit 'no'), never accept. Raw outputs: prescreen/<cid>.json.")
    # --- per-writer table
    calls = read_jsonl(os.path.join(W, "calls.jsonl"))
    L.append("\n## Writer comparison (same verified candidates)\n")
    L.append("| writer | clues produced | passed leakage | passed identifiability | flagged by Opus | accepted | writer cost | cost / accepted clue |")
    L.append("|---|---|---|---|---|---|---|---|")
    for w in WRITERS:
        recs = [(s, s["clues"][w]) for s in states if w in (s.get("clues") or {})]
        prod = [c for _, c in recs if c.get("clue")]
        pl = [c for c in prod if c.get("status") in ("passed_f", "ident_failed", "accepted", "flagged")]
        pi = [c for c in prod if c.get("status") in ("passed_f", "accepted", "flagged")]
        fl = [c for c in prod if c.get("status") == "flagged"]
        ac = [c for c in prod if c.get("status") == "accepted"]
        wc = [c for c in calls if c.get("purpose") == f"write:{w}"]
        known = all(c.get("cost_known", True) for c in wc)
        cost = sum(float(c.get("cost_usd") or 0) for c in wc)
        toks = (sum(c.get("prompt_tokens") or 0 for c in wc), sum(c.get("completion_tokens") or 0 for c in wc))
        cstr = f"${cost:.4f}" if known else f"tokens only: in {toks[0]}, out {toks[1]}"
        per = (f"${cost / len(ac):.4f}" if ac else "n/a") if known else "n/a (no price)"
        L.append(f"| {w} | {len(prod)} | {len(pl)} | {len(pi)} | {len(fl)} | {len(ac)} | {cstr} | {per} |")
    cfg = read_json(ds_native_cfg_path(), {}) or {}
    if cfg:
        L.append(f"\nDeepSeek native request: model `{DS_NATIVE_MODEL}`, thinking budget sent "
                 f"{cfg.get('budget')} (max_tokens {cfg.get('max_tokens')}); probe log: "
                 + "; ".join(f"{p['budget_tokens']}→{p['status']}" for p in cfg.get("probes", [])))
    if any(c.get("api") == "deepseek_native" and not c.get("cost_known") for c in calls):
        L.append("\nDeepSeek's own API returned no cost and no --ds-price-* prices were given: those calls are "
                 "logged with tokens only and counted as $0 against --max-usd.")
    L.append("\n### Examples of writer disagreement on the same item\n")
    ex = 0
    for s in states:
        cl = s.get("clues") or {}
        if len(cl) < 2 or not s.get("key"):
            continue
        if len({c.get("status") for c in cl.values()}) < 2:
            continue
        L.append(f"- **{s['key']['title']}** ({s['key']['year']})")
        for w, c in cl.items():
            L.append(f"  - {w}: {c.get('status')} {('(' + str(c.get('reason')) + ')') if c.get('reason') else ''} — "
                     f"{(c.get('clue') or '')[:160]}")
        ex += 1
        if ex >= 6:
            break
    if not ex:
        L.append("(none yet)")
    # --- cost
    L.append("\n## Cost\n")
    bym = collections.defaultdict(lambda: [0, 0.0, 0, 0, 0])
    for c in calls:
        m = bym[(c.get("api"), c.get("model"))]
        m[0] += 1
        m[1] += float(c.get("cost_usd") or 0)
        m[2] += c.get("prompt_tokens") or 0
        m[3] += c.get("completion_tokens") or 0
        m[4] += 0 if c.get("cost_known", True) else 1
    L.append("| api | model | calls | cost USD | prompt tok | completion tok | calls without cost |")
    L.append("|---|---|---|---|---|---|---|")
    for (api, model), m in sorted(bym.items(), key=lambda x: str(x[0])):
        L.append(f"| {api} | {model} | {m[0]} | {m[1]:.4f} | {m[2]} | {m[3]} | {m[4]} |")
    # --- cost by stage
    def stage_of(c):
        p = str(c.get("purpose") or "")
        if p.startswith("write:"):
            return "writing"
        if p == "verify":
            return "verification"
        if p == "prescreen":
            return "pre-screen"
        return "extraction"
    sc = collections.OrderedDict((k, {"n": 0, "usd": 0.0, "unk": 0, "purp": set()})
                                 for k in ("extraction", "pre-screen", "writing", "verification"))
    for c in calls:
        s = sc[stage_of(c)]
        s["n"] += 1
        s["usd"] += float(c.get("cost_usd") or 0)
        s["unk"] += 0 if c.get("cost_known", True) else 1
        s["purp"].add(str(c.get("purpose") or "?").split(":")[0][:30])
    n_acc = len(chosen) + len(rest)
    tot = sum(s["usd"] for s in sc.values())
    L.append("\n### Cost by stage\n")
    L.append("| stage | calls | cost USD | share | cost / accepted item | calls without cost | purposes |")
    L.append("|---|---|---|---|---|---|---|")
    for k, s in sc.items():
        share = f"{s['usd'] / tot * 100:.0f}%" if tot else "n/a"
        per = f"${s['usd'] / n_acc:.4f}" if n_acc else "n/a"
        purp = ", ".join(sorted(s["purp"])[:6])
        L.append(f"| {k} | {s['n']} | {s['usd']:.4f} | {share} | {per} | {s['unk']} | {purp} |")
    L.append(f"| **total** | {sum(s['n'] for s in sc.values())} | {tot:.4f} | 100% | "
             f"{('$' + format(tot / n_acc, '.4f')) if n_acc else 'n/a (0 accepted)'} | "
             f"{sum(s['unk'] for s in sc.values())} | |")
    n_units = sum(1 for s in states for c in (s.get("clues") or {}).values() if c.get("verify"))
    if n_units:
        L.append(f"\nOpus verification: {n_units} units verified, ${sc['verification']['usd'] / n_units:.4f} per unit. "
                 "'extraction' covers every model call not tagged prescreen, write:* or verify.")
    L.append(f"\nTotal model cost: ${LEDGER.spent:.4f} (OpenRouter: usage.cost plus "
             "cost_details.upstream_inference_cost for BYOK). Per-call log: calls.jsonl.")
    tools = read_jsonl(os.path.join(W, "tools.jsonl"))
    tc = collections.Counter((t.get("tool"), t.get("cached")) for t in tools)
    L.append(f"DeepSeek tool calls (not in model cost): search {tc[('search', False)]} live / "
             f"{tc[('search', True)]} cached; fetch {tc[('fetch', False)]} live / {tc[('fetch', True)]} cached.\n")
    # --- failures and gaps
    errs = read_jsonl(os.path.join(W, "errors.jsonl"))
    L.append("## What failed or was not done\n")
    L.append(f"- Infrastructure errors (items left pending, retried on rerun): {len(errs)}"
             + (f"; last: `{errs[-1]['error'][:200]}`" if errs else ""))
    if len(chosen) < args.target:
        L.append(f"- Shortfall: {len(chosen)} items of {args.target} targeted. No open-ended re-harvest is done; "
                 "rerun with a larger --harvest-factor to add candidates.")
    L.append("- extra_acceptable_keys is empty: the design's different-family comparison of the clue's top 10 (C3) "
             "is not run here; Opus may only flag `other_fitting_work`, which drops the clue.")
    L.append("- Negative controls (section B) and the six 50-item blocks are not built by this script.")
    L.append("- Clue-level drops keep the item if another writer's clue was accepted; a key-level flag from Opus drops "
             "the item for every writer.")
    with open(os.path.join(W, "REPORT.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(L) + "\n")
```

### replace main
```python
def main():
    p = argparse.ArgumentParser(description="Build verified answer keys for Battery 2.")
    p.add_argument("--target", type=int, default=300, help="items to keep")
    p.add_argument("--max-usd", type=float, default=None, help="cumulative model-cost cap (all runs in workdir)")
    p.add_argument("--stage", default="all", choices=["a", "b", "c", "d", "e", "f", "g", "report", "all"])
    p.add_argument("--writers", default="sonnet,opus,deepseek", help="subset of sonnet,opus,deepseek")
    p.add_argument("--workdir", default=".")
    p.add_argument("--seed", default="battery2")
    p.add_argument("--harvest-factor", type=float, default=6.0, help="candidates harvested per target item")
    p.add_argument("--overshoot", type=float, default=1.25, help="stop intake at target*overshoot passing items")
    p.add_argument("--cutoff-year", type=int, default=2025, help="year from which items count as post-cutoff")
    p.add_argument("--workers", type=int, default=4)
    p.add_argument("--ds-price-in", type=float, default=None, help="DeepSeek native USD per 1M input tokens")
    p.add_argument("--ds-price-out", type=float, default=None, help="DeepSeek native USD per 1M output tokens")
    p.add_argument("--ds-price-cache", type=float, default=None, help="DeepSeek native USD per 1M cached input tokens")
    p.add_argument("--host-stats", action="append", default=[], metavar="PATH",
                   help="another run's tools.jsonl used for host steering in harvest (repeatable)")
    args = p.parse_args()
    args.writers = [w.strip() for w in args.writers.split(",") if w.strip()]
    bad = [w for w in args.writers if w not in WRITERS]
    if bad or not args.writers:
        p.error(f"unknown writers {bad}; choose from {list(WRITERS)}")
    missing = [h for h in args.host_stats if not os.path.isfile(h)]
    if missing:
        p.error(f"--host-stats file(s) not found: {missing}")
    args.host_stats = [os.path.abspath(h) for h in args.host_stats]
    setup(args)
    note = ""
    try:
        if args.stage in ("a", "all"):
            stage_a(args)
            load_cands()
        if args.stage in ("b", "c", "d", "e", "f"):
            run_candidates(args, [args.stage])
        elif args.stage == "all":
            run_candidates(args, ["b", "c", "d", "e", "f"])
        if args.stage in ("g", "all"):
            stage_g(args, all_states())
    except BudgetExceeded as e:
        note = f"stopped cleanly at the cost cap: {e}"
        print("[budget] " + note)
    except InfraError as e:
        note = f"stopped on an infrastructure error (rerun to resume): {e}"
        print("[infra] " + note)
    except KeyboardInterrupt:
        note = "interrupted by user (rerun to resume)"
        print("[stop] " + note)
    finally:
        finalize(args, note)
```

**Fix 1: pre-screen.** `stage_g` now calls `stage_prescreen` first. It sends one EXTRACT_MODEL call per item that has a `passed_f` clue. The request contains the key fields, the A/B record excerpts, the cell and `meta['field']`. One call per item is enough because the clue is not part of the input, so every writer's unit for that item would get the same answer. The call itself goes through the existing `openrouter_chat`. Its result is cached by cid in `prescreen/<cid>.json`, together with the request and raw output, so reruns cost nothing. A 400-rejected or empty reply is cached as well and is not retried.

The rules for dropping:
- **Explicit "no" drops.** The item is dropped with `prescreen:off_topic` or `prescreen:type_mismatch` (off_topic wins if both are "no"), and stage `g_pre`.
- **Everything else passes through to Opus.** That covers "yes", missing fields and unparseable output.
- **I added an "unsure" option.** The prompt says to answer "no" only when the evidence is clear. Without this, a cheap model's false negatives would silently shrink the sample.

To share the excerpt logic I split `record_excerpts` out of `unit_block`. The Opus request is unchanged. One edge case: if an item already accepted in an earlier run gets a new unit, the pre-screen can still drop it. That is drop-only behaviour, consistent with the rule that no model approves.

**Fix 2: host steering.** `stage_a` builds the blocked-host set once with `load_host_stats`. It counts fetches over this workdir's `tools.jsonl` plus each `--host-stats` file, reading each file once by real path so passing your own log twice doesn't double-count:
- an attempt is an uncached fetch, identified by its `status` entry;
- hosts are compared without "www." and port;
- a host is blocked at ≥3 attempts with no 200.

`harvest_hit` applies the check only after all other filters, so a skip means a real lost candidate. Skipped hits go to `harvest_skips.jsonl` and are not added to `seen` or to the cell count. Listings on blocked hosts still seed queries, since that uses only search text. Missing `--host-stats` paths are rejected at startup. The new "Sampling frame" section in REPORT.md lists each host with:
- skipped hits;
- distinct URLs;
- per-cell counts;
- the fetch-attempt count.

It states that items on those hosts cannot enter the set. It also reports, honestly, any candidates on those hosts that were registered before steering existed, since those were processed normally.

**Fix 3: report costs.** A "Cost by stage" table groups calls.jsonl by purpose:
- `prescreen` → pre-screen;
- `write:*` → writing;
- `verify` → verification;
- everything else → extraction. I don't see your extraction purpose strings, so the table lists the purposes that landed in each bucket.

Each row shows calls, USD, share, cost per accepted item (items + reserve), and calls without a known cost. A total row and an Opus cost-per-verified-unit line follow, which makes the pre-screen's savings visible directly.