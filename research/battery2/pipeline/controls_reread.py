"""Battery 2 negative controls: the evidence of CONTROLS-RULE.md 15.2.7a-b for the flagged issues. Not blind. It
replaces neither controls.py nor any verdict of sections 7 and 12.

  reread: the six issues of 15.2.7a judged again from the saved pages of the re-run, by the frozen controls.py with
          the three faults of section 12 fixed; also replayed without the fixes, to compare with verdicts.json.
          Fetches nothing: a page the results folder does not hold stops that issue.
  third:  the third-source search of 15.2.7b for the three issues it names.

Usage: python3 -I controls_reread.py reread RESULTS --workdir DIR --cass YEAR=URL [--cass ...] [--issue Y/N ...]
       python3 -I controls_reread.py third RESULTS --workdir DIR [--issue Y/N ...]
RESULTS holds the re-run's verdicts.json, whose sha256 the addendum fixes (label verdicts-sha256, as in
control_topics.py), and snapshots/. Detail goes to DIR, which must not lie inside a git work tree of this repository
(15.1.4); standard output carries counts only.
"""
import argparse
import hashlib
import importlib.util
import os
import re
import sys
import types

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import build_keys as bk  # noqa: E402
import control_topics  # noqa: E402
import controls  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
REREAD_ISSUES = ((2012, 2), (2012, 5), (2014, 4), (2014, 6), (2015, 6), (2016, 1))
THIRD_ISSUES = ((2016, 6), (2017, 5), (2018, 1))
FIXES = ("blocks", "catalogue", "napstic")
# Section 12, "What the failures are": in page order, the blocks of the 2012 page fall on these issues. Only what
# section 12 describes is fixed; another year's page is read by the frozen cass_issues unchanged.
BLOCK_ORDER = {2012: (6, 1, 2, 3, 4, 5)}
NEWS_COLUMN = "信息动态"
QUERIES = ("周易研究 {y}年第{n}期 目录", "Zhouyi Yanjiu {y} No.{n}")
TOP, MAX_SEARCHES, MAX_FETCHES = 5, 6, 30
LEFTOVER_CJK = (4, 40)
ROUTE = "controls: third source"
PART = re.compile(r"[\s/／|｜·•.．…、，,;；:：()（）\[\]【】<>《》\d—–~～-]+")
NOT_BLIND = ("not blind (15.2.7a): these pages were read before this reader was written, after the result; the fault 3 "
             "exemption is a rule written after the result")
SHORTENED = "a page that DeepSeek's fetch shortened can understate what its source holds (RERUN-PROTOCOL section 4)"


class FetchAttempt(Exception):
    """The reader needs a page that the results folder does not hold: reading it would take a fetch."""


class ShapeMismatch(Exception):
    """The page lacks the shape section 12 describes, so the fix written from that description does not apply."""


class CapReached(Exception):
    pass


# ----------------------------------------------------------------------------- the three faults of section 12
def _split(ln):
    """The title part of a line, as the frozen cass_issues splits it."""
    t = ln.partition("//")[0] if "//" in ln else ln.rpartition("/")[0]
    return (t.rpartition("/")[0] if "/" in t else t).strip()


def _cjk_slash(ln):
    return "/" in ln and bk.has_cjk(ln)


def file_blocks(text, year):
    """Fault 1 (2012/2, 2012/5): put the header of its issue before each block of entries that has none, so that the
    frozen cass_issues files every block. A block is the run of lines that the frozen reader would read under one
    issue, or would skip because an English list set the issue to none; it starts at its first CJK line and counts
    only if an entry line follows before the next header or English list."""
    order = BLOCK_ORDER.get(year)
    if order is None:
        return text
    lines = text.splitlines()
    state, cand, head, blocks = "pre", None, None, []
    for i, raw in enumerate(lines):
        ln = controls._clean(raw)
        if not ln:
            continue
        if controls.ENGLISH_PART.search(ln) or (_cjk_slash(ln) and controls.latin_line(_split(ln))):
            state, cand = ("pre" if state == "pre" else "out"), None
            continue
        m = controls.ISSUE_HEAD.search(ln)
        if m:
            if int(m.group(1)) != year:
                raise ShapeMismatch(f"a header of {m.group(1)} on the page of {year}")
            state, cand, head = "head", None, int(m.group(2))
            continue
        if state in ("head", "out"):
            if cand is None and bk.has_cjk(ln):
                cand = (i, head if state == "head" else None)
            if cand is not None and _cjk_slash(ln):
                blocks.append(cand)
                state, cand = "in", None
    if len(blocks) != len(order) or any(h not in (None, k) for (_, h), k in zip(blocks, order)):
        raise ShapeMismatch(f"{year}: blocks headed {[h for _, h in blocks]}, section 12 gives {list(order)}")
    for (i, h), k in reversed(list(zip(blocks, order))):
        if h is None:
            lines.insert(i, f"《{controls.JOURNAL}》{year}年第{k}期")
    return "\n".join(lines)


def own_catalogue(text, title):
    """Fault 2 (2014/4, 2014/6): CNKI's own catalogue line is the first line under 相似文献 that has this title and
    names this journal; the frozen cnki_page does not check the journal."""
    k = (text or "").find("相似文献")
    if k < 0:
        return None
    for m in bk.CNKI_SELF.finditer(text[k:].replace("|", "\n")):
        if bk.norm(m.group(1).split(";")[-1]) == bk.norm(title) and bk.norm(m.group(2)) == bk.norm(controls.JOURNAL):
            return int(m.group(3)), int(m.group(4))
    return None


def napstic_notice(title):
    """Fault 3 (2015/6, 2016/1): the news column that section 12 names, as the whole title, is exempt from the napstic
    check, as a notice is from agreement. Section 12 names no other notice that napstic lists, and the marker words of
    the custodians' notice test would exempt titles (综述, 会议) that it does not mention. A rule written after the
    result, so not blind."""
    return bk.norm(title) == bk.norm(NEWS_COLUMN)


# ----------------------------------------------------------------------------- 15.2.7a: judging from saved pages
def saved_fetch(snapdir):
    """controls.fetch on saved pages only. A saved page is used as the run left it: the run made its tries, forced or
    not, and the snapshot holds the last, so force changes nothing here."""
    def fetch(api, url, prefix, route, force=False):
        snap = bk.read_json(os.path.join(snapdir, f"{prefix}_{bk.sha(url)}.json"))
        if snap is None:
            raise FetchAttempt(url)
        return bk.fetch_text(snap.get("response")) if controls._ok(snap) else None
    return fetch


def frozen_copy(snapdir):
    """A private copy of the frozen module, so that replacing its fetch touches nothing else in this process."""
    spec = importlib.util.spec_from_file_location("controls_frozen_copy", os.path.join(HERE, "controls.py"))
    c = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(c)
    c.fetch = saved_fetch(snapdir)
    c.time = types.SimpleNamespace(sleep=lambda s: None)      # the run's waits were for the network
    return c


def read_issue(c, year, issue, cass_url, fixes=FIXES):
    """One issue judged as controls.main judges it, on c (a frozen_copy), with the named fixes."""
    texts = dict(zip(("deepseek", "moonshot"), c.cass_copies(cass_url)))
    parsed = {n: (c.cass_issues(file_blocks(t, year) if "blocks" in fixes else t) if t else None)
              for n, t in texts.items()}
    copies = {n: (None if p is None else p.get((year, issue), [])) for n, p in parsed.items()}
    cnki, gaps, capped = c.cnki_run(year, issue, len(c.usable_copies(copies)[0]))
    if "catalogue" in fixes:
        for e in cnki:
            e["catalogue_issue"] = own_catalogue(c.fetch("deepseek", e["url"], "cd", "reread"), e["forms"][0])
    nap, health = c.napstic_titles(year, issue)
    exempt = [t for t in nap if "napstic" in fixes and napstic_notice(t)]
    v = c.issue_verdict(year, issue, copies, cnki, gaps, capped, [t for t in nap if t not in exempt], health)
    v["napstic_exempt"] = exempt
    return v


def reread(results, cass, issues):
    c = frozen_copy(os.path.join(results, "snapshots"))
    frozen = bk.read_json(os.path.join(results, "verdicts.json"), {}) or {}
    out = {}
    for y, n in issues:
        key, rec = f"{y}/{n}", {}
        for label, fixes in (("replay", ()), ("reread", FIXES)):
            try:
                rec[label] = read_issue(c, y, n, cass[y], fixes)
            except (FetchAttempt, ShapeMismatch) as exc:
                rec[label] = {"complete": False, "error": f"{type(exc).__name__}: {exc}"}
        old = frozen.get(key, {})
        rec["replay_matches_frozen"] = all(rec["replay"].get(k) == old.get(k) for k in ("complete", "fails", "listing"))
        have = {bk.norm(f) for forms in old.get("listing", []) for f in forms}
        rec["new_titles"] = [forms for forms in rec["reread"].get("listing", [])
                             if not any(bk.norm(f) in have for f in forms)]
        out[key] = rec
        r = rec["reread"]
        print(key, "reread:", "complete" if r["complete"] else "NOT complete",
              r.get("counts", {}), list(r.get("fails", {})), r["error"].split(":")[0] if "error" in r else "",
              "napstic_exempt:", len(r.get("napstic_exempt", [])), "new_titles:", len(rec["new_titles"]),
              "replay_matches_frozen:", rec["replay_matches_frozen"])
    return out


# ----------------------------------------------------------------------------- 15.2.7b: the third source
def _take(used, kind, cap):
    if used[kind] >= cap:
        raise CapReached(f"{kind}: {cap}")
    used[kind] += 1


def page_lines(text):
    return [ln for ln in (controls._clean(r) for r in (text or "").splitlines()) if ln]


def page_forms(ln):
    """The line, and its parts of at least FLOOR characters: a contents page puts an author or a page number beside
    the title, and a whole line with them fits no title at SIM_MATCH. A shorter part (目录) would match any notice
    in the listing, the reason 15.4.4 gives for its floor; a whole line is compared as it is."""
    return [ln] + [p for p in PART.split(ln) if p != ln and len(bk.norm(p)) >= control_topics.FLOOR]


def line_holds(ln, form):
    """A form of at least FLOOR characters (15.4.4's reason: a short notice such as 目录 would match any page) that
    the line, read whole or as its parts, fits by controls.best at controls.SIM_MATCH, or that the line contains: so
    many characters in a row are strong evidence, and the similarity drops them when authors and pages share the
    line."""
    n = bk.norm(form)
    return len(n) >= control_topics.FLOOR and (
        n in bk.norm(ln) or controls.best([form], [{"forms": page_forms(ln)}]) >= controls.SIM_MATCH)


def held_and_left(text, listing):
    """listing: the issue's entries as verdicts.json holds them (a list of forms). Returns the entries the page holds
    and the page's lines that fit none of them."""
    lines = page_lines(text)
    entries = [{"forms": f} for f in listing]
    held = [f for f in listing if any(line_holds(ln, t) for t in f for ln in lines)]
    lo, hi = LEFTOVER_CJK
    left = [ln for ln in lines if lo <= sum(map(bk.has_cjk, ln)) <= hi
            and controls.best(page_forms(ln), entries) < controls.SIM_MATCH
            and not any(line_holds(ln, t) for f in listing for t in f)]
    return held, left


def third_source(issues, listings, search=None, fetch=None):
    """listings: {(year, issue): listing}. search and fetch default to build_keys.ds_search and the DeepSeek fetch of
    controls.py; the caps count every call, cached or not."""
    search = search or bk.ds_search
    fetch = fetch or (lambda url: controls.fetch("deepseek", url, "cd", ROUTE))
    used, out = {"searches": 0, "fetches": 0}, {}
    for y, n in issues:
        pages = []
        for q in QUERIES:
            query = q.format(y=y, n=n)
            _take(used, "searches", MAX_SEARCHES)
            results, _ = search(query, TOP, ROUTE)
            for rank, r in enumerate(results[:TOP], 1):
                url, text = bk.r_url(r), None
                if url:
                    _take(used, "fetches", MAX_FETCHES)
                    text = fetch(url)
                held, left = held_and_left(text, listings[(y, n)])
                pages.append({"query": query, "rank": rank, "url": url, "host": bk.host_of(url),
                              "snapshot": f"cd_{bk.sha(url)}.json" if url else None, "opened": text is not None,
                              "held_count": len(held), "held": held, "leftover": left})
        out[f"{y}/{n}"] = {"pages": pages, "none_found": not any(p["held_count"] for p in pages),
                           "forms_under_floor": sum(len(bk.norm(t)) < control_topics.FLOOR
                                                    for f in listings[(y, n)] for t in f)}
    return out, used


# ----------------------------------------------------------------------------- command line
def parse_issue(s):
    y, _, n = s.partition("/")
    return int(y), int(n)


def write_new(path, obj):
    if os.path.exists(path):
        raise SystemExit(f"exists, not overwritten: {path}")
    bk.write_json(path, obj)


def main(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument("command", choices=("reread", "third"))
    p.add_argument("results")
    p.add_argument("--workdir", required=True)
    p.add_argument("--issue", action="append", type=parse_issue)
    p.add_argument("--cass", action="append", default=[], help="YEAR=URL of the CASS yearly page (reread)")
    a = p.parse_args(argv)
    allowed = REREAD_ISSUES if a.command == "reread" else THIRD_ISSUES
    issues = tuple(a.issue or allowed)
    if not set(issues) <= set(allowed):
        p.error(f"{a.command} takes only {[f'{y}/{n}' for y, n in allowed]}")
    work = os.path.abspath(a.workdir)
    try:
        control_topics.guard_workdir(work)
        control_topics.check_norm_mode()
        control_topics.check_private(os.path.join(a.results, "verdicts.json"), "verdicts-sha256")
    except control_topics.Stop as e:
        raise SystemExit(f"stopped: {e}")
    os.makedirs(work, exist_ok=True)
    with open(os.path.abspath(__file__), "rb") as f:
        stamp = {"ts": bk.nowiso(), "code_sha256": hashlib.sha256(f.read()).hexdigest()}
    if a.command == "reread":
        cass = {int(y): u for y, _, u in (s.partition("=") for s in a.cass)}
        if {y for y, _ in issues} - set(cass):
            p.error("give --cass YEAR=URL for every year of the issues")
        out = reread(os.path.abspath(a.results), cass, issues)
        write_new(os.path.join(work, f"reread-{stamp['ts'].replace(':', '')}.json"),
                  {**stamp, "label": NOT_BLIND, "issues": out})
        return
    verdicts = bk.read_json(os.path.join(a.results, "verdicts.json"), {}) or {}
    bk.W, bk.SNAP = work, os.path.join(work, "snapshots")
    os.makedirs(bk.SNAP, exist_ok=True)
    target = os.path.join(work, "third.json")
    if os.path.exists(target):
        raise SystemExit("the third-source search runs once (15.2.7b); third.json exists")
    out, used = third_source(issues, {(y, n): verdicts[f"{y}/{n}"]["listing"] for y, n in issues})
    bk.write_json(target, {**stamp, "note": SHORTENED, "used": used, "issues": out})
    for key, r in out.items():
        print(key, "pages:", len(r["pages"]), "opened:", sum(x["opened"] for x in r["pages"]),
              "holding an entry:", sum(x["held_count"] > 0 for x in r["pages"]),
              "most entries held:", max((x["held_count"] for x in r["pages"]), default=0),
              "leftover lines:", sum(len(x["leftover"]) for x in r["pages"]), "none found:", r["none_found"],
              "forms under the floor, not counted:", r["forms_under_floor"])
    print("searches:", used["searches"], "fetches:", used["fetches"])


if __name__ == "__main__":
    main()
