ue_unparseable")
            else:
                clue = re.sub(r"\s+", " ", clue).strip()
                rec["clue"] = clue
                bad = clue_format_check(clue, st, payload)
                if bad:
                    rec.update(status="format_failed", reason="clue_format:" + bad)
                else:
                    rec.update(status="written", reason=None)
        st["clues"][w] = rec
        save_state(st)


# ----------------------------------------------------------------------------- stage f: leakage + identifiability
FINAL = {"call_rejected", "unparseable", "format_failed", "leak_failed", "ident_failed", "accepted", "flagged"}
PRE_G_FAIL = {"call_rejected", "unparseable", "format_failed", "leak_failed", "ident_failed"}
_CJK3 = re.compile(r"^[\u3400-\u9fff\uf900-\ufaff]{3}$")


def _words(s):
    return re.findall(r"[a-z0-9']+", deaccent(t2s(unicodedata.normalize("NFKC", str(s or ""))).lower()))


def leak_reason(clue, title):
    """Design C2: any shared 3-char Chinese substring or any shared 2-word English phrase with the title."""
    nt, nc = norm(title), norm(clue)
    for i in range(len(nt) - 2):
        g = nt[i:i + 3]
        if _CJK3.match(g) and g in nc:
            return f"zh3gram:{g}"
    wt, wc = _words(title), _words(clue)
    gt = {(wt[i], wt[i + 1]) for i in range(len(wt) - 1)}
    gc = {(wc[i], wc[i + 1]) for i in range(len(wc) - 1)}
    common = sorted(gt & gc)
    if common:
        return "en2gram:" + " ".join(common[0])
    return None


def stage_f(st, args):
    if st.get("drop") or not st.get("key") or not st.get("clues"):
        return
    for w, rec in st["clues"].items():
        if rec.get("status") != "written":
            continue
        lr = leak_reason(rec["clue"], st["key"]["title"])
        if lr:
            rec.update(status="leak_failed", reason="leakage:" + lr)
            save_state(st)
            continue
        res, sf = ds_search(rec["clue"], 10, route=f"identifiability:{w}")
        rank = hit_rank(res, st["key"]["title"], [r["url"] for r in st["records"]])
        rec["identifiability"] = {"query": rec["clue"], "rank": rank, "search_snapshot": sf}
        if rank:
            rec.update(status="passed_f", reason=None)
        else:
            rec.update(status="ident_failed", reason="identifiability_failed")
        save_state(st)
    decide_item(st, args)


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


# ----------------------------------------------------------------------------- stage g: blind Opus verification
VERIFY_SYSTEM = """You audit candidate answer keys and clues for a bibliographic recall test (Chinese scholarship on the Yijing/Zhouyi, excavated manuscripts, early Chinese texts). You never approve or repair anything: you only raise flags. Code drops every flagged unit.
Each unit gives: key fields, two record URLs with their custodian class, a short excerpt from each saved record, and a search clue. (Numbers of 9+ digits were masked as [number].)
Flags (use only these names):
- field_not_in_excerpt: a key field (author, title, venue, year, volume_issue) is contradicted by, or clearly absent from, the excerpts.
- records_not_independent: the two URLs look like the same custodian, a mirror/copy of each other, or two aggregators (CNKI/VIP/Wanfang).
- not_primary: a URL is not a primary record (search snippet, citing paper, reference list, encyclopedia, blog, shop, forum).
- clue_misdescribes: the clue states something about the work (type, field, topic, decade, anchor value) not supported by the key/excerpts.
- clue_leaks: the clue gives the title or part of it, the exact year, volume, issue or pages.
- anchor_rule: the clue names neither or both of the author and the venue.
- other_fitting_work: you know another work that fits the clue about as well as the key.
- other: any other serious problem (explain in note).
Return only JSON: {"verdicts": [{"id": "<unit id>", "flags": [], "note": "<short>"}]} with exactly one verdict per unit id; an empty flags list means you found no problem."""


def excerpt(text, needles, width=300, cap=1200):
    pieces, covered = [], []
    for nd in needles:
        nd = str(nd or "").strip()
        if not nd:
            continue
        pos = text.find(nd)
        if pos < 0 and len(nd) > 8:
            pos = text.find(nd[:8])
        if pos < 0 or any(a <= pos <= b for a, b in covered):
            continue
        a, b = max(0, pos - width), min(len(text), pos + len(nd) + width)
        covered.append((a, b))
        pieces.append(text[a:b])
    if not pieces:
        pieces = [text[:600]]
    return sanitize(" … ".join(pieces))[:cap]


def unit_block(st, w, uid):
    k, forms = st["key"], st.get("key_forms", {})
    recs = []
    for tag, r in zip(("A", "B"), st["records"]):
        f = forms.get(tag) or k
        txt = snapshot_text(r["snapshot_file"])
        recs.append({"url": r["url"], "custodian_class": r["custodian_class"], "route": sanitize(r["route"])[:200],
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
    for i in range(0, len(units), 10):
        batch = units[i:i + 10]
        bid = "batch_" + sha("|".join(u[0] for u in batch), 12)
        bpath = os.path.join(VERIFY_DIR, bid + ".json")
        saved = read_json(bpath)
        if saved is None or "raw_output" not in saved:
            blocks = [unit_block(st, w, uid) for uid, st, w in batch]
            user = json.dumps({"units": blocks}, ensure_ascii=False, indent=1)
            txt = openrouter_chat(OPUS, [{"role": "system", "content": VERIFY_SYSTEM}, {"role": "user", "content": user}],
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


# ----------------------------------------------------------------------------- candidate pipeline (b-f)
FN = {"b": stage_b, "c": stage_c, "d": stage_d, "e": stage_e, "f": stage_f}


def process(cid, args, stages):
    st = load_state(cid)
    if st.get("drop"):
        return st
    try:
        for s in stages:
            FN[s](st, args)
            save_state(st)
            if st.get("drop"):
                break
    except InfraError as e:
        jlog(os.path.join(W, "errors.jsonl"), {"ts": nowiso(), "cid": cid, "error": str(e)[:500]})
    finally:
        save_state(st)
    return st


def is_good(st):
    if st.get("drop"):
        return False
    return bool(st.get("accepted")) or any(c.get("status") in ("passed_f", "accepted")
                                           for c in (st.get("clues") or {}).values())


def run_candidates(args, stages):
    cids = sorted(_CANDS)
    random.Random(f"{args.seed}:order").shuffle(cids)
    states = {s["cid"]: s for s in all_states()}
    goal = math.ceil(args.target * args.overshoot)
    gate = len(stages) > 1
    budget_hit = None
    chunk = max(1, args.workers * 2)
    with ThreadPoolExecutor(max(1, args.workers)) as ex:
        for i in range(0, len(cids), chunk):
            if gate and sum(is_good(s) for s in states.values()) >= goal:
                print(f"[b-f] reached {goal} candidates with a passing clue; stopping intake")
                break
            futs = {ex.submit(process, cid, args, stages): cid for cid in cids[i:i + chunk]}
            for f, cid in futs.items():
                try:
                    states[cid] = f.result()
                except BudgetExceeded as e:
                    budget_hit = e
            done = sum(1 for s in states.values() if s.get("drop") or s.get("accepted") or is_good(s))
            print(f"[b-f] {min(i + chunk, len(cids))}/{len(cids)} processed; settled {done}; "
                  f"good {sum(is_good(s) for s in states.values())}; spent ${LEDGER.spent:.4f}")
            if budget_hit:
                raise budget_hit


# ----------------------------------------------------------------------------- outputs
def primary_clue(st, writers):
    acc = [w for w, c in (st.get("clues") or {}).items() if c.get("status") == "accepted"]
    order = list(writers) + [w for w in WRITERS if w not in writers]
    for w in order:
        if w in acc:
            return w
    return None


def item_record(st, writers):
    pw = primary_clue(st, writers)
    clues = st.get("clues") or {}
    return {"id": "B2-" + st["cid"], "stratum": st["stratum"], "key": st["key"],
            "key_forms": st.get("key_forms"), "records": st["records"],
            "clue": clues[pw]["clue"] if pw else None, "clue_writer": pw,
            "clues_by_writer": {w: {"clue": c.get("clue"), "status": c.get("status"), "anchor": c.get("anchor"),
                                    "identifiability": c.get("identifiability")} for w, c in clues.items()},
            "extra_acceptable_keys": [], "recoverability": st.get("recover"),
            "topic_source": st.get("topic_source"), "harvest": {"query": st["cand"]["query"],
                                                                "search_snapshot": st["cand"]["search_snapshot"],
                                                                "rank": st["cand"]["rank"], "offset": st["cand"]["offset"]}}


def write_jsonl(path, rows):
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    os.replace(tmp, path)


def finalize(args, note=""):
    load_cands()
    states = all_states()
    accepted = sorted([s for s in states if s.get("accepted") and not s.get("drop")], key=lambda s: s["cid"])
    by_cell = collections.defaultdict(list)
    for s in accepted:
        by_cell[(s["stratum"]["type"], s["stratum"]["language"])].append(s)
    chosen, rest = [], []
    for cell, share in CELLS.items():
        q = round(args.target * share)
        chosen += by_cell[cell][:q]
        rest += by_cell[cell][q:]
    for cell, lst in by_cell.items():
        if cell not in CELLS:
            rest += lst
    rest.sort(key=lambda s: s["cid"])
    while len(chosen) < args.target and rest:
        chosen.append(rest.pop(0))
    write_jsonl(os.path.join(W, "items.jsonl"), [item_record(s, args.writers) for s in chosen])
    write_jsonl(os.path.join(W, "reserve.jsonl"), [item_record(s, args.writers) for s in rest])
    dropped = [{"cid": s["cid"], "url": s["cand"]["url"], "cell": s["cand"]["cell"], **s["drop"],
                "key": s.get("key"), "clues": {w: {k: c.get(k) for k in ("status", "reason", "clue")}
                                               for w, c in (s.get("clues") or {}).items()}}
               for s in states if s.get("drop")]
    write_jsonl(os.path.join(W, "dropped.jsonl"), dropped)
    write_report(args, states, chosen, rest, dropped, note)
    print(f"[out] items {len(chosen)} (target {args.target}), reserve {len(rest)}, dropped {len(dropped)}; "
          f"spent ${LEDGER.spent:.4f}")


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


# ----------------------------------------------------------------------------- setup + main
def setup(args):
    global W, SNAP, STATE, CANDS_DIR, EXTRACT_DIR, CLUE_DIR, VERIFY_DIR, LEDGER, ARGS
    ARGS = args
    W = os.path.abspath(args.workdir)
    SNAP = os.path.join(W, "snapshots")
    STATE = os.path.join(W, "state")
    CANDS_DIR = os.path.join(STATE, "cands")
    EXTRACT_DIR = os.path.join(W, "extractions")
    CLUE_DIR = os.path.join(W, "clues")
    VERIFY_DIR = os.path.join(W, "verify")
    for d in (W, SNAP, STATE, CANDS_DIR, EXTRACT_DIR, CLUE_DIR, VERIFY_DIR):
        os.makedirs(d, exist_ok=True)
    LEDGER = Ledger(os.path.join(W, "calls.jsonl"), args.max_usd)
    load_cands()
    for s in all_states():
        k = s.get("key")
        if k and s.get("drop", {}).get("rule") != "duplicate":
            _DUPS.setdefault(norm(k["title"]) + "|" + norm(k["author"]), s["cid"])


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


if __name__ == "__main__":
    main()
```

**How to run**

- **Setup.** Put the script in `research/battery2/keys/` and run it from there. Python 3 standard library only; `opencc` is used only if it is already installed. Set `OPENROUTER_API_KEY` and `DEEPSEEK_API_KEY`; placeholders work behind the key-injecting proxy.
- **Full run.** `python3 build_keys.py --target 300 --max-usd 20`
  - This runs harvest (a), then b–f per candidate, then the blind Opus verification (g).
  - It always writes `items.jsonl`, `reserve.jsonl`, `dropped.jsonl` and `REPORT.md`.
- **Resuming.** Rerun the same command after any crash or restart. Snapshots, extractions, clues, per-candidate state (`state/cands/`) and verify batches are reused, so finished work is never redone.
- **Cost cap.** `--max-usd` is cumulative over every call logged in `calls.jsonl`.
- **Single stages.** Run one stage with `--stage a|b|…|g`, or rebuild the outputs only with `--stage report`.
- **DeepSeek-only writing.** `--writers deepseek` runs clue writing without OpenRouter. Two stages still need OpenRouter and cannot run without it:
  - extraction (c) uses DeepSeek Flash 1017 through OpenRouter;
  - verification (g) uses Opus.
  - If OpenRouter is down, the affected items stay pending, are logged in `errors.jsonl`, and resume on the next run.
- **DeepSeek native pricing.** Pass `--ds-price-in/--ds-price-out` (USD per 1M tokens) to cost the native DeepSeek writer. Otherwise its calls are logged with tokens only, and `REPORT.md` says so.