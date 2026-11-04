Fourth change to your build_keys.py. Test 4 (writers sonnet,opus,deepseek): 29 candidates, 1 accepted, $0.52. Test 5 (--writers sonnet): 42 candidates, 0 accepted, $0.40. Per-call logs show the cost is dominated by Opus verification (~$0.13 per unit verified), and in test 5 Opus correctly rejected both units: one was off-topic ('Family in contemporary Egypt', Syracuse UP 1984, harvested in the book/en cell) and one was a type mismatch (an edited serial volume 《簡帛語言文字研究》第六輯 filed in the article/zh cell; flagged not_primary). Fix these, returning whole functions in the same format as before (`### replace <name>` / `### add <name> after <name>`, each in its own ```python block), then a short paragraph per fix.

1. PRE-SCREEN before stage g, using EXTRACT_MODEL (cheap). For each unit about to be verified, one call with the key fields, the record excerpt, the cell and meta['field'], asking two yes/no questions with a one-line reason: (a) is this work about the cell's field (Yijing/Zhouyi studies, excavated or transmitted early Chinese texts, early China, Chinese philosophy of that period)? (b) does its type match the cell (article = one article in a journal issue or an edited volume; book = a monograph or a single edition; an edited serial volume as a whole is NOT an article, and a journal issue as a whole is neither)? A 'no' on either drops the item with rule prescreen:off_topic or prescreen:type_mismatch. The pre-screen can only drop, never accept, and its raw output is saved like other calls. Unparseable output = no drop (Opus still sees it). Cache by cid so reruns cost nothing.
2. HOST STEERING in harvest. Before stage a registers a candidate, look up the host's DeepSeek fetch record in this workdir's tools.jsonl plus any files given by a new repeatable flag --host-stats PATH (other runs' tools.jsonl). If a host has >=3 uncached fetch attempts and 0 with status 200, skip the hit and log it to a new harvest_skips.jsonl with reason host_unfetchable (do not count it as a candidate). In REPORT.md add a section 'Sampling frame' listing skipped hosts and counts, stating that items on those hosts cannot enter the set.
3. REPORT: add per-stage cost (extraction, pre-screen, writing, verification) and cost per accepted item.
Keep every other rule, including that no model ever approves a key. Code below.

=== CONSTANTS ===
OR_URL = "https://openrouter.ai/api/v1/chat/completions"
DS_SEARCH_URL = "https://api.deepseek.com/v1/tools/search"
DS_FETCH_URL = "https://api.deepseek.com/v1/tools/fetch"
DS_ANTH_URL = "https://api.deepseek.com/anthropic/v1/messages"
EXTRACT_MODEL = "deepseek/deepseek-v4.1-flash-1017:exacto"
SONNET = "anthropic/claude-sonnet-5.5"
OPUS = "anthropic/claude-opus-5.5"
DS_NATIVE_MODEL = "deepseek-flash"
WRITERS = {"sonnet": ("openrouter", SONNET), "opus": ("openrouter", OPUS), "deepseek": ("deepseek_native", DS_NATIVE_MODEL)}
DS_THINK_CANDIDATES = [65536, 32768, 16384, 8192, 4096, 2048, 1024]   # largest first; first accepted is kept
MAX_PAGE_CHARS = 40000
CELLS = {("article", "zh"): 0.48, ("article", "en"): 0.12, ("book", "zh"): 0.32, ("book", "en"): 0.08}
PERIODS = [(1975, 1999), (2000, 2015), (2016, 2025)]
FAME_CIT = (50, 5)       # citations >=50 famous, >=5 mid, else obscure (script's operationalisation)
FAME_HOLD = (100, 10)    # catalogue holdings >=100 famous, >=10 mid, else obscure
KEY_FLAGS = {"field_not_in_excerpt", "records_not_independent", "not_primary"}
ALLOWED_FLAGS = KEY_FLAGS | {"clue_misdescribes", "clue_leaks", "anchor_rule", "other_fitting_work", "other"}


=== CODE ===
def openrouter_chat(model, messages, purpose, anthropic, max_tokens=None):
    body = {"model": model, "messages": messages, "reasoning": {"effort": "max"}, "usage": {"include": True}}
    if anthropic:
        body["provider"] = {"only": ["anthropic"]}
        body["cache_control"] = {"type": "ephemeral"}
    else:
        body["provider"] = {"zdr": True}
    if max_tokens:
        body["max_tokens"] = max_tokens
    LEDGER.check()
    t0 = time.time()
    status, js, raw = http_post(OR_URL, {"Authorization": "Bearer " + os.environ.get("OPENROUTER_API_KEY", "placeholder")},
                                body, timeout=1200)
    js = js if isinstance(js, dict) else {}
    usage = js.get("usage") or {}
    cost, src = or_cost(usage)
    ok = status == 200 and bool(js.get("choices"))
    rec = {"ts": nowiso(), "api": "openrouter", "model": model, "purpose": purpose, "generation_id": js.get("id"),
           "status": status, "prompt_tokens": usage.get("prompt_tokens"),
           "completion_tokens": usage.get("completion_tokens"),
           "reasoning_tokens": (usage.get("completion_tokens_details") or {}).get("reasoning_tokens"),
           "cached_tokens": (usage.get("prompt_tokens_details") or {}).get("cached_tokens"),
           "cost_usd": cost, "cost_source": src, "cost_known": True, "secs": round(time.time() - t0, 1)}
    if not ok:
        rec["error"] = raw[:400]
    LEDGER.add(rec)
    if ok:
        c = (js["choices"][0].get("message") or {}).get("content")
        if isinstance(c, list):
            c = "".join(p.get("text", "") for p in c if isinstance(p, dict))
        return c or ""
    err = js.get("error") or {}
    code = err.get("code", status) if isinstance(err, dict) else status
    if status == 400 or code == 400:
        return None          # request rejected for this item (e.g. context too long): item-level drop
    raise InfraError(f"OpenRouter {model} status={status} code={code}: {raw[:300]}")

def ds_fetch(url, route):
    if "ctext.org" in url.lower():
        return {"ok": False, "file": None, "text": "", "url": url}
    fn = f"f_{sha(url)}.json"
    path = os.path.join(SNAP, fn)
    snap = read_json(path)
    if snap is None:
        status, js, raw = http_post(DS_FETCH_URL, {"Authorization": "Bearer " + os.environ.get("DEEPSEEK_API_KEY", "placeholder")},
                                    {"url": url}, timeout=180)
        jlog(os.path.join(W, "tools.jsonl"), {"ts": nowiso(), "tool": "fetch", "url": url, "cached": False, "status": status})
        if status in (401, 402):
            raise InfraError(f"fetch auth/billing status={status}")
        snap = {"kind": "fetch", "url": url, "route": route, "date": today(), "status": status,
                "response": js if js is not None else raw[:20000]}
        write_json(path, snap)
        jlog(os.path.join(SNAP, "index.jsonl"), {"kind": "fetch", "url": url, "route": route, "date": today(), "file": fn, "status": status})
    else:
        jlog(os.path.join(W, "tools.jsonl"), {"ts": nowiso(), "tool": "fetch", "url": url, "cached": True})
    text = fetch_text(snap.get("response"))
    ok = snap.get("status", 200) == 200 and len(norm(text)) > 30
    return {"ok": ok, "file": fn, "text": text, "url": url, "date": snap.get("date")}

def parse_json_obj(text):
    if not text:
        return None
    t = re.sub(r"```(?:json)?", "", text)
    dec = json.JSONDecoder()
    for m in re.finditer(r"\{", t):
        try:
            obj, _ = dec.raw_decode(t[m.start():])
            if isinstance(obj, dict):
                return obj
        except ValueError:
            continue
    return None

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

def drop(st, rule, stage, detail=""):
    st["drop"] = {"rule": rule, "stage": stage, "detail": str(detail)[:500], "date": today()}

def decide_item(st, args):
    """Item-level decision from clue statuses. Key flags drop the item; otherwise >=1 accepted clue accepts it."""
    if st.get("drop") or not st.get("key"):
        return
    clues = st.get("clues", {}) or {}
    kf = [w for w, c in clues.items() if c.get("key_flagged")]
    if kf:
        st.pop("accepted", None)
        flags = sorted({f for w in kf for f in clues[w].get("verify", {}).get("flags", []) if f in KEY_FLAGS})
        return drop(st, "verification_flag:key", "g", ",".join(flags))
    if any(c.get("status") == "accepted" for c in clues.values()):
        st["accepted"] = True
        return
    pending = [w for w in args.writers if w not in clues or clues[w].get("status") not in FINAL]
    pending += [w for w, c in clues.items() if c.get("status") == "passed_f"]
    if pending:
        return
    if not clues:
        return
    if all(c.get("status") in PRE_G_FAIL for c in clues.values()):
        reasons = sorted({str(c.get("reason")) for c in clues.values()})
        return drop(st, "clue_check_failed", "f", "; ".join(reasons))
    return drop(st, "verification_flag:clue", "g", "all clues flagged by verifier")

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
    args = p.parse_args()
    args.writers = [w.strip() for w in args.writers.split(",") if w.strip()]
    bad = [w for w in args.writers if w not in WRITERS]
    if bad or not args.writers:
        p.error(f"unknown writers {bad}; choose from {list(WRITERS)}")
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