Your patched build_keys.py ran again: 28 candidates, 0 kept. Drops: field_unverified 17, no_second_record 9 (detail always 'no independent item record found (0 tried)', i.e. b_queries produced no query), listing_page 2.
Below: the current code of the relevant functions, then real samples (drop row, candidate state, head of record A's snapshot). Diagnose the cause of each failure mode from the evidence, then return fixes in the same format as before: each changed or new function whole, in its own ```python block preceded by `### replace <name>` or `### add <name> after <name>`. Then a short paragraph: cause of each failure mode and what changed. Do not weaken any rule (verbatim check, independence, no repair).

=== CODE ===
def norm(s):
    s = unicodedata.normalize("NFKC", str(s or ""))
    s = deaccent(t2s(s).lower())
    return re.sub(r"[\W_]+", "", s)

def t2s(s):
    s = s or ""
    if _OCC is not None:
        try:
            return _OCC.convert(s)
        except Exception:
            pass
    return s.translate(_T2S)

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

def extract(snapfile, url, mode, target=None):
    key = f"{snapfile}__{mode}__{sha(json.dumps(target, ensure_ascii=False) if target else '')}"
    path = os.path.join(EXTRACT_DIR, key + ".json")
    cached = read_json(path)
    if cached is not None:
        return cached
    raw = snapshot_text(snapfile)
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

=== SAMPLES ===
[
 {
  "drop": {
   "cid": "c0378cdc5b5",
   "url": "http://zhouyi.sdu.edu.cn/zyyjxk/qkjs.htm",
   "cell": [
    "article",
    "zh"
   ],
   "rule": "field_unverified",
   "stage": "c",
   "detail": "record A",
   "date": "2026-11-04",
   "key": null,
   "clues": {}
  },
  "state": "{\"cid\": \"c0378cdc5b5\", \"cand\": {\"cid\": \"c0378cdc5b5\", \"url\": \"http://zhouyi.sdu.edu.cn/zyyjxk/qkjs.htm\", \"hint_title\": \"期刊介绍\", \"query\": \"《周易研究》2019年第1期 目录\", \"search_snapshot\": \"s_e10defeca2a4a9f5.json\", \"hit_index\": 28, \"cell\": [\"article\", \"zh\"], \"meta\": {\"journal\": \"周易研究\", \"year_target\": 2019, \"topic\": \"卦爻辞\", \"field\": \"易学（《周易》研究）\"}, \"rank\": 29, \"offset\": 20, \"seed_from\": null, \"date\": \"2026-11-04\"}, \"drop\": {\"rule\": \"field_unverified\", \"stage\": \"c\", \"detail\": \"record A\", \"date\": \"2026-11-04\"}}",
  "snapshot_A_head": null
 },
 {
  "drop": {
   "cid": "c1c20e53b75",
   "url": "https://search.napstic.cn/literature/periodical/010zhouyyj202401001",
   "cell": [
    "article",
    "zh"
   ],
   "rule": "field_unverified",
   "stage": "c",
   "detail": "record A",
   "date": "2026-11-04",
   "key": null,
   "clues": {}
  },
  "state": "{\"cid\": \"c1c20e53b75\", \"cand\": {\"cid\": \"c1c20e53b75\", \"url\": \"https://search.napstic.cn/literature/periodical/010zhouyyj202401001\", \"hint_title\": \"周易研究\", \"query\": \"周易研究 2024 周易 论文\", \"search_snapshot\": \"s_fd75e6672c161921.json\", \"hit_index\": 18, \"cell\": [\"article\", \"zh\"], \"meta\": {\"journal\": \"周易研究\", \"year_target\": 2024, \"topic\": \"周易\", \"field\": \"易学（《周易》研究）\"}, \"rank\": 19, \"offset\": 10, \"seed_from\": null, \"date\": \"2026-11-04\"}, \"drop\": {\"rule\": \"field_unverified\", \"stage\": \"c\", \"detail\": \"record A\", \"date\": \"2026-11-04\"}}",
  "snapshot_A_head": null
 },
 {
  "drop": {
   "cid": "c1648bc9cc5",
   "url": "http://opac.lib.uibe.edu.cn/opac/book/245cab5b411f7cea5653766fd0e10bbb",
   "cell": [
    "book",
    "zh"
   ],
   "rule": "no_second_record",
   "stage": "b",
   "detail": "no independent item record found (0 tried)",
   "date": "2026-11-04",
   "key": null,
   "clues": {}
  },
  "state": "{\"cid\": \"c1648bc9cc5\", \"cand\": {\"cid\": \"c1648bc9cc5\", \"url\": \"http://opac.lib.uibe.edu.cn/opac/book/245cab5b411f7cea5653766fd0e10bbb\", \"hint_title\": \"书目信息 机读格式(MARC)\", \"query\": \"中文图书7.易象论 北京大学出版社\", \"search_snapshot\": \"s_5910f87c25c0b2e7.json\", \"hit_index\": 4, \"cell\": [\"book\", \"zh\"], \"meta\": {\"publisher\": \"北京大学出版社\", \"year_target\": 2012, \"topic\": \"易学\", \"field\": \"易学\"}, \"rank\": 5, \"offset\": 0, \"seed_from\": \"http://opac.lib.jhun.edu.cn:8080/opac/openlink.php?location=ALL&keyword=%E5%91%A8%E6%98%93&callno=B&doctype=ALL&lang_code=ALL&match_flag=forward&displaypg=20&showmode=list&orderby=DESC&sort=CATA_DATE&onlylendable=no&with_ebook=off&hist_cont=hist&subject=%E8%B1%A1%E6%95%B0%E4%B9%8B%E5%AD%A6\", \"date\": \"2026-11-04\"}, \"recA\": {\"url\": \"http://opac.lib.uibe.edu.cn/opac/book/245cab5b411f7cea5653766fd0e10bbb\", \"snapshot_file\": \"h_371132b2b31d5c02.json\", \"snapshot_kind\": \"search_hit\", \"search_snapshot\": \"s_5910f87c25c0b2e7.json\", \"hit_index\": 4, \"query\": \"中文图书7.易象论 北京大学出版社\", \"route\": \"harvest search: 中文图书7.易象论 北京大学出版社\", \"date\": \"2026-11-04\", \"custodian_class\": \"library\"}, \"entryA\": {\"author\": \"侯敏\", \"title\": \"易象论\", \"venue\": \"北京大学出版社\", \"year\": 2006, \"keywords\": [\"象数之学 研究\"], \"work_type_llm\": \"book\"}, \"extract_files\": {\"A\": \"h_371132b2b31d5c02.json\"}, \"drop\": {\"rule\": \"no_second_record\", \"stage\": \"b\", \"detail\": \"no independent item record found (0 tried)\", \"date\": \"2026-11-04\"}}",
  "snapshot_A_head": "{\n \"kind\": \"search_hit\",\n \"parent_snapshot\": \"s_5910f87c25c0b2e7.json\",\n \"hit_index\": 4,\n \"query\": \"中文图书7.易象论 北京大学出版社\",\n \"route\": \"harvest search: 中文图书7.易象论 北京大学出版社\",\n \"url\": \"http://opac.lib.uibe.edu.cn/opac/book/245cab5b411f7cea5653766fd0e10bbb\",\n \"date\": \"2026-11-04\",\n \"response\": {\n  \"title\": \"书目信息 机读格式(MARC)\",\n  \"site_name\": \"对外经济贸易大学\",\n  \"site_icon\": \"https://cdn.deepseek.com/site-icons/uibe.edu.cn\",\n  \"authority\": 3,\n  \"rerank_score\": 1.53125,\n  \"date\": null,\n  \"url\": \"http://opac.lib.uibe.edu.cn/opac/book/245cab5b411f7cea5653766fd0e10bbb\",\n  \"summary\": \"书目详细信息 ： 易象论\\n\\n### 书目信息 机读格式(MARC)\\n\\nISBN/价格： | 7-301-10179-1:CNY28.00 \\n---|---\\n作品语种： | chi \\n出版国别： | CN 110000 \\n题名责任者项： | 易象论/.侯敏著 \\n出版发行项： | 北京:,北京大学出版社:,2006 \\n载体形态项： | 228页:;+24cm \\n丛编项： | 中青年学者文库 \\n并列题名： | Diseassion on the intention of the book of change eng \\n题名主题： | 象数之学 研究 \\n索书号： | B221.5/H55\\n个人名称等同： | 侯敏, 著 \\n记录来源： | CN GLFXJ 20060117 \\n记录来源： | CN 20060609\",\n  \"snippet\": \"易象论 ... ISBN/价格：: 题名责任者项：; 7-301-10179-1:CNY28.00: 易象论/.侯敏著 ... ISBN/价格：: 出版发行项：; 7-301-10179-1:CNY28.00: 北京:,北京大学出版社:,2006 ... ISBN/价格：: 载体形态项：; 7-301-10179-1:CNY28.00: 228页:;+24cm\",\n  \"content\": \"\"\n }\n}"
 },
 {
  "drop": {
   "cid": "c25272ff878",
   "url": "https://kuline.kulib.kyoto-u.ac.jp/opac/opac_details/?lang=0&amode=11&bibid=BB04622887",
   "cell": [
    "book",
    "zh"
   ],
   "rule": "no_second_record",
   "stage": "b",
   "detail": "no independent item record found (0 tried)",
   "date": "2026-11-04",
   "key": null,
   "clues": {}
  },
  "state": "{\"cid\": \"c25272ff878\", \"cand\": {\"cid\": \"c25272ff878\", \"url\": \"https://kuline.kulib.kyoto-u.ac.jp/opac/opac_details/?lang=0&amode=11&bibid=BB04622887\", \"hint_title\": \"京都大学 KULINE\", \"query\": \"中华书局 郭店楚简 2012年 出版 ISBN\", \"search_snapshot\": \"s_caefcf4a5c2ff44a.json\", \"hit_index\": 25, \"cell\": [\"book\", \"zh\"], \"meta\": {\"publisher\": \"中华书局\", \"year_target\": 2012, \"topic\": \"郭店楚简\", \"field\": \"简帛学\"}, \"rank\": 26, \"offset\": 20, \"seed_from\": null, \"date\": \"2026-11-04\"}, \"recA\": {\"url\": \"https://kuline.kulib.kyoto-u.ac.jp/opac/opac_details/?lang=0&amode=11&bibid=BB04622887\", \"snapshot_file\": \"h_f17c097cd11c92a1.json\", \"snapshot_kind\": \"search_hit\", \"search_snapshot\": \"s_caefcf4a5c2ff44a.json\", \"hit_index\": 25, \"query\": \"中华书局 郭店楚简 2012年 出版 ISBN\", \"route\": \"harvest search: 中华书局 郭店楚简 2012年 出版 ISBN\", \"date\": \"2026-11-04\", \"custodian_class\": \"library\"}, \"entryA\": {\"author\": \"(美)顾史考著\", \"title\": \"郭店楚简先秦儒书宏微观\", \"venue\": \"上海古籍出版社\", \"year\": 2012, \"work_type_llm\": \"book\"}, \"extract_files\": {\"A\": \"h_f17c097cd11c92a1.json\"}, \"drop\": {\"rule\": \"no_second_record\", \"stage\": \"b\", \"detail\": \"no independent item record found (0 tried)\", \"date\": \"2026-11-04\"}}",
  "snapshot_A_head": "{\n \"kind\": \"search_hit\",\n \"parent_snapshot\": \"s_caefcf4a5c2ff44a.json\",\n \"hit_index\": 25,\n \"query\": \"中华书局 郭店楚简 2012年 出版 ISBN\",\n \"route\": \"harvest search: 中华书局 郭店楚简 2012年 出版 ISBN\",\n \"url\": \"https://kuline.kulib.kyoto-u.ac.jp/opac/opac_details/?lang=0&amode=11&bibid=BB04622887\",\n \"date\": \"2026-11-04\",\n \"response\": {\n  \"title\": \"京都大学 KULINE\",\n  \"site_name\": \"Kuline\",\n  \"site_icon\": \"https://cdn.deepseek.com/site-icons/kyoto-u.ac.jp\",\n  \"authority\": 3,\n  \"rerank_score\": 0.13330437242984772,\n  \"date\": null,\n  \"url\": \"https://kuline.kulib.kyoto-u.ac.jp/opac/opac_details/?lang=0&amode=11&bibid=BB04622887\",\n  \"summary\": \"## guo dian chu jian xian qin ru shu hong wei guan カクテン ソカン センシン ジュショ コウビカン\\n郭店楚简先秦儒书宏微观 / (美)顾史考著\\n(早期中国研究丛书 ; 第3辑)\\n\\nデータ種別 | 図書 \\n---|---\\n著者標目 | Cook, Scott(1964-) \\n出版情報 | 上海 : 上海古籍出版社 , 2012.10\\n...\\n大きさ | 5, 249p ; 21cm \\n巻冊次 | ISBN:9787532564545 ; PRICE:36.00元 \\n一般注記 | 参考书目: p[235]-249\\n再版序言に「本书原由台湾学生书局出版(台北:2006年6月)」と記載\\n...\\nISBN | 9787532564545\",\n  \"snippet\": \"郭店楚简先秦儒书宏微观 / (美)顾史考著 ... 図書: 上海 : 上海古籍出版社 , 2012.10 ... 巻冊次 | ISBN:9787532564545 ; PRICE...\",\n  \"content\": \"\"\n }\n}"
 }
]