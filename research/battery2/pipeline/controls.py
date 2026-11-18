"""Battery 2 negative controls: decide in code whether an issue of 周易研究 is completely listed, by the rule
of pipeline/CONTROLS-RULE.md (PREREG deviation 6). Fetches only; no model call.

Usage: python3 -I controls.py --workdir DIR --year Y --cass URL [--year Y --cass URL ...]
Writes DIR/verdicts.json (per issue: verdict, failures, the listing and CNKI abstracts) and DIR/snapshots/.
"""
import argparse
import difflib
import json
import os
import re
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import build_keys as bk  # noqa: E402

JOURNAL, CNKI_CODE, NAPSTIC_CODE, ISSUES = "周易研究", "ZYJY", "zhouyyj", range(1, 7)
SIM_MATCH = 0.85          # final-design §D, "Correct": title character similarity; here also "same article"
SIM_FLOOR = 0.5           # §D: below this an answer's title is unrelated to every listed title
CNKI_MARGIN, CNKI_TAIL, CNKI_CAP = 5, 4, 40
NAPSTIC_PAGES = 5
MOONSHOT_TRIES, MOONSHOT_WAIT_S = 3, 600
# Not research articles: such an entry may be missing from one custodian without breaking agreement.
# It stays in the listing that answers and topics are checked against.
NONRESEARCH = re.compile("书讯|简介|新书架|选题|征订|稿约|目录|启事|悼念|纪念|讣告|综述|会议|论坛|研讨会|致辞|"
                         "开幕|闭幕|贺信|题词|合影|编者|编后|获奖|名单|更正|勘误")
ISSUE_HEAD = re.compile(rf"《{JOURNAL}》\s*(\d{{4}})\s*年\s*第\s*0?(\d)\s*期")
START_PAGE = re.compile(r"(?://|[（(])\s*(\d{1,3})\s*[)）]?\s*$")
ENGLISH_PART = re.compile(r"TABLE OF CONTENTS|STUDIES OF ZHOUYI\s*/", re.I)
NAP_HEAD = re.compile(r"(\d{4})年0?(\d)\s*期")
NAP_ART = re.compile(r"^####\s+(.+?)\s*$", re.M)


def sim(a, b):
    a, b = bk.norm(a), bk.norm(b)
    return difflib.SequenceMatcher(None, a, b).ratio() if a and b else 0.0


def best(forms, listing):
    return max((sim(f, g) for f in forms for e in listing for g in e["forms"]), default=0.0)


# ----------------------------------------------------------------------------- fetch, with snapshots
def fetch(api, url, prefix, route, force=False):
    """A stored 200 snapshot is reused unless force; a failed one is tried again. A refetch keeps the earlier
    snapshot under "previous"."""
    fn = f"{prefix}_{bk.sha(url)}.json"
    path = os.path.join(bk.SNAP, fn)
    snap = bk.read_json(path)
    if snap is None or snap.get("status") != 200 or force:
        endpoint = bk.DS_FETCH_URL if api == "deepseek" else bk.MOONSHOT_FETCH_URL
        status, js, raw = bk.http_post(endpoint, {"Authorization": "Bearer placeholder"}, {"url": url}, timeout=180)
        snap = {"kind": "fetch", "url": url, "route": route, "date": bk.today(), "status": status, "fetcher": api,
                "response": js if js is not None else raw[:20000], "tries": (snap or {}).get("tries", 0) + 1,
                "previous": snap}
        bk.write_json(path, snap)
        bk.jlog(os.path.join(bk.SNAP, "index.jsonl"), {"ts": bk.nowiso(), "kind": "fetch", "url": url, "route": route,
                                                     "fetcher": api, "status": status, "file": fn})
    text = bk.fetch_text(snap.get("response"))
    return text if snap.get("status") == 200 and len(bk.norm(text)) > 30 else None


def cass_copies(url):
    ds = fetch("deepseek", url, "cd", "controls: cass page")
    ms = None
    for k in range(MOONSHOT_TRIES):
        ms = fetch("moonshot", url, "cm", "controls: cass page")
        if ms is not None or k == MOONSHOT_TRIES - 1:
            break
        time.sleep(MOONSHOT_WAIT_S)
    return ds, ms


# ----------------------------------------------------------------------------- custodian A: CASS yearly page
def _clean(line):
    return re.sub(r"^[^\w《“\"（(＂]+", "", line.replace("\\|", "|").replace("**", "").strip())


def latin_line(t):
    n = bk.norm(t)
    return bool(n) and sum(bk.has_cjk(ch) for ch in n) < 0.3 * len(n)


def cass_issues(text):
    """{(year, issue): [entry]} from one copy, in page order. An entry is {forms, page, line}; a title the page
    wraps over two lines also gets the joined reading as a second form. A line that is mostly Latin script starts
    the English list, which repeats the issue and is not read."""
    out, cur, prev = {}, None, None
    for raw in text.splitlines():
        ln = _clean(raw)
        if not ln:
            continue
        if ENGLISH_PART.search(ln):
            cur = None
            continue
        m = ISSUE_HEAD.search(ln)
        if m:
            cur, prev = (int(m.group(1)), int(m.group(2))), None
            out.setdefault(cur, [])
            continue
        if cur is None:
            continue
        if "/" in ln and bk.has_cjk(ln):
            t, _, rest = ln.partition("//") if "//" in ln else ln.rpartition("/")
            if "/" in t:                              # "title/authors//page"
                t, _, names = t.rpartition("/")
                rest = names + "//" + rest
            t = t.strip()
            if latin_line(t):                         # the English list has begun
                cur = None
                continue
            p = START_PAGE.search(rest)
            author = START_PAGE.sub("", rest).strip(" /")
            forms = [t] + ([prev + t] if prev else [])
            out[cur].append({"forms": [f for f in forms if bk.norm(f)], "page": int(p.group(1)) if p else None,
                             "line": ln, "notice": not bk.norm(author)})
            prev = None
        else:
            prev = ln if bk.has_cjk(ln) and len(ln) < 80 else None
            if prev and NONRESEARCH.search(prev):     # notices listed without "/"
                out[cur].append({"forms": [prev], "page": None, "line": prev, "notice": True})
                prev = None
    return out


def union(*listings):
    """Merged on exact title (after norm) only: near-identical titles stay separate entries."""
    seen, out = set(), []
    for lst in listings:
        for e in lst:
            k = bk.norm(e["forms"][0])
            if k not in seen:
                seen.add(k)
                out.append(e)
    return out


def page_order_breaks(entries):
    pages = [e["page"] for e in entries if e["page"] is not None and not e.get("notice")]
    return [f"{a}->{b}" for a, b in zip(pages, pages[1:]) if b < a]


# ----------------------------------------------------------------------------- custodian B: CNKI id run
CNKI_SELF = re.compile(r"\[J\];([^;\n]+);(\d{4})年(\d{1,2})期")


def cnki_page(year, issue, seq, force=False):
    """(kind, entry): kind is "article", "not_found" (CNKI's own frame page for an id it does not hold),
    "untitled" (an article page whose title cannot be read) or "unopened" (the fetch failed)."""
    url = f"https://www.cnki.com.cn/Article/CJFDTotal-{CNKI_CODE}{year}{issue:02d}{seq:03d}.htm"
    text = fetch("deepseek", url, "cd", "controls: cnki id", force)
    if text is None:
        return "unopened", None
    if "【引证文献】" not in text and "【摘要】" not in text:
        return "not_found", None
    h1 = re.search(r"^#\s+(.+)$", text, re.M)
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    first = lines[0] if len(lines) > 1 and lines[1].startswith("【摘要】") and lines[0][0] not in "【#" else None
    title = h1.group(1).strip() if h1 else first                     # first: the converter left out the "#"
    if not title:
        return "untitled", None
    e = {"forms": [title], "seq": seq, "url": url}
    ab = re.search(r"【摘要】[:：]?\s*(.*)", text)
    e["abstract"] = ab.group(1).strip() if ab else ""
    # CNKI marks a body excerpt standing in for a missing abstract with <正>: news, book notices, plates.
    e["notice"] = not e["abstract"] or e["abstract"].startswith("<正>")
    k = text.find("相似文献")
    m = CNKI_SELF.search(text[k:].replace("|", "\n")) if k >= 0 else None
    e["catalogue_issue"] = (int(m.group(2)), int(m.group(3))) if m else None
    return "article", e


def cnki_run(year, issue, n_cass):
    """Walk ids from 001 to at least n_cass + CNKI_MARGIN, and on until CNKI_TAIL ids after the last article
    (at most CNKI_CAP). Between the first and the last article every id must be an article: any other id is
    fetched once more, and is a gap if it still is not. A not-found id before the first article is allowed:
    CNKI's numbering of an issue can start above 001."""
    kinds, hits, last, seq = {}, {}, 0, 0
    while seq < CNKI_CAP:
        seq += 1
        if seq > max(n_cass + CNKI_MARGIN, last + CNKI_TAIL):
            break
        kinds[seq], e = cnki_page(year, issue, seq)
        if e:
            hits[seq], last = e, seq
    first = min(hits) if hits else 0
    gaps = []
    for s in range(1, last + 1):
        if s in hits or (s < first and kinds[s] == "not_found"):
            continue
        kinds[s], e = cnki_page(year, issue, s, force=True)
        if e:
            hits[s] = e
        elif not (s < first and kinds[s] == "not_found"):
            gaps.append(f"{s:03d}:{kinds[s]}")
    return [hits[s] for s in sorted(hits)], gaps, seq >= CNKI_CAP


# ----------------------------------------------------------------------------- napstic: a subset, a falsifier
def napstic_titles(year, issue):
    titles, seen = [], set()
    for page in range(1, NAPSTIC_PAGES + 1):
        url = f"https://search.napstic.cn/literature/oaj/{NAPSTIC_CODE}?page={page}&activeYear={year}&activeIssue={issue}"
        text = fetch("deepseek", url, "cd", "controls: napstic issue")
        h = NAP_HEAD.search(text or "")
        if not h or (int(h.group(1)), int(h.group(2))) != (year, issue):
            break
        new = [t.strip() for t in NAP_ART.findall(text) if bk.norm(t) not in seen]
        if not new:
            break
        seen.update(bk.norm(t) for t in new)
        titles += new
    return titles


# ----------------------------------------------------------------------------- the verdict
def research(e):
    """A notice: an entry with no author on the CASS page, a CNKI page whose abstract is CNKI's <正> excerpt, or a
    marker title."""
    return not e.get("notice") and not NONRESEARCH.search(e["forms"][0])


def unmatched(a, b):
    return [e["forms"][0] for e in a if research(e) and best(e["forms"], b) < SIM_MATCH]


def usable_copies(copies):
    """copies: {fetcher: entries of this issue, or None when the page did not open}. A copy serves the issue when
    it has the issue's header and its start pages never decrease (a lost header merges two issues, which shows
    as a decrease). Returns (entries of the serving copies, failures)."""
    fails, serving = {}, []
    shut = [n for n, c in copies.items() if c is None]
    if shut:
        fails["cass_page_not_opened"] = shut
    for name, entries in copies.items():
        if entries and not page_order_breaks(entries):
            serving.append(entries)
        elif entries:
            fails.setdefault("cass_copy_set_aside", []).append(f"{name}: " + ",".join(page_order_breaks(entries)))
    if not serving:
        fails["cass_no_usable_copy"] = list(copies)
    return union(*serving), fails


def issue_verdict(year, issue, copies, cnki, gaps, capped, nap):
    cass, notes = usable_copies(copies)
    fails = {k: v for k, v in notes.items() if k != "cass_copy_set_aside"}
    if not cnki:
        fails["cnki_run_empty"] = []
    if gaps:
        fails["cnki_gap"] = gaps
    if capped:
        fails["cnki_cap_reached"] = [CNKI_CAP]
    wrong = [e["url"] for e in cnki if e["catalogue_issue"] not in (None, (year, issue))]
    if wrong:
        fails["cnki_catalogue_issue_mismatch"] = wrong
    for name, (a, b) in {"cass_not_in_cnki": (cass, cnki), "cnki_not_in_cass": (cnki, cass)}.items():
        u = unmatched(a, b)
        if u:
            fails[name] = u
    listing = union(cass, cnki)
    miss = [t for t in nap if best([t], listing) < SIM_MATCH]
    if miss:
        fails["napstic_not_in_listing"] = miss
    return {"complete": not fails, "fails": fails, "set_aside": notes.get("cass_copy_set_aside", []),
            "counts": {**{n: len(c or []) for n, c in copies.items()}, "cass": len(cass), "cnki": len(cnki),
                       "napstic": len(nap)},
            "listing": [e["forms"] for e in listing], "abstracts": [e["abstract"] for e in cnki if not e["notice"]]}


# ----------------------------------------------------------------------------- scoring a control answer (§D)
def score_control(answer, decade_listing, decade):
    """answer: extracted fields {title, venue, year, issue}; decade_listing: every issue's listing forms."""
    if not bk.norm(answer.get("title")):
        return "abstain"
    venue_hit = bk.norm(answer.get("venue")) == bk.norm(JOURNAL)
    year = answer.get("year")
    if venue_hit and answer.get("issue") is not None and answer["issue"] not in ISSUES:
        return "invented"                         # impossible issue
    if not (venue_hit and isinstance(year, int) and decade <= year < decade + 10):
        return "score_as_real_item"               # §D's protocol; a wrong-real or invented verdict is a failure
    s = best([answer["title"]], [{"forms": f} for f in decade_listing])
    if s >= SIM_MATCH:
        return "wrong_real"                       # a listed article, which does not fit the absent topic
    if s >= SIM_FLOOR:
        return "ambiguous"                        # sensitivity rule, adjudication queue
    return "invented"                             # excluded by the complete listing


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--workdir", required=True)
    p.add_argument("--year", type=int, action="append", required=True)
    p.add_argument("--cass", action="append", required=True, help="CASS yearly page, one per --year, same order")
    a = p.parse_args()
    bk.W = os.path.abspath(a.workdir)
    bk.SNAP = os.path.join(bk.W, "snapshots")
    os.makedirs(bk.SNAP, exist_ok=True)
    path = os.path.join(bk.W, "verdicts.json")
    out = bk.read_json(path, {}) or {}
    for year, url in zip(a.year, a.cass):
        ds, ms = cass_copies(url)
        parsed = {n: (cass_issues(t) if t else None) for n, t in (("deepseek", ds), ("moonshot", ms))}
        for issue in ISSUES:
            copies = {n: (None if c is None else c.get((year, issue), [])) for n, c in parsed.items()}
            cnki, gaps, capped = cnki_run(year, issue, len(usable_copies(copies)[0]))
            v = issue_verdict(year, issue, copies, cnki, gaps, capped, napstic_titles(year, issue))
            out[f"{year}/{issue}"] = v
            bk.write_json(path, out)
            print(year, issue, "complete" if v["complete"] else "NOT complete", v["counts"], list(v["fails"]))
    done = [k for k in out if k.split("/")[0] in {str(y) for y in a.year}]
    print("complete:", sum(out[k]["complete"] for k in done), "of", len(done))


if __name__ == "__main__":
    main()
