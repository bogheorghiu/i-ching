"""Checks of the controls.py amendment (CONTROLS-RULE.md section 8) on synthetic pages: no network, no real page.
Usage: python3 -I check_controls_amendment.py [PIPELINE_DIR]
PIPELINE_DIR holds controls.py and build_keys.py; the default is this file's folder. Give a folder that holds the
controls.py of the freeze before the amendment (eff3325) to see the checks fail there. Exit status 1 if one fails."""
import importlib.util
import os
import sys

d = os.path.abspath(sys.argv[1] if len(sys.argv) > 1 else os.path.dirname(__file__))
spec = importlib.util.spec_from_file_location("controls_under_test", os.path.join(d, "controls.py"))
c = importlib.util.module_from_spec(spec)
spec.loader.exec_module(c)


def page(title, abstract_block):
    return f"# {title}\n【作者】：某\n{abstract_block}【引证文献】：\n"


PAGES = {
    "empty_next_heading": page("新书介绍《某某研究》", "【摘要】：\n"),
    "empty_blank_line": page("新书介绍《某某研究》", "【摘要】：\n\n"),
    "normal": page("某某研究", "【摘要】：本文讨论易学。\n"),
    "zheng": page("新书出版", "【摘要】：<正>某某新书出版。\n"),
    "no_abstract_line": "# 编辑部消息\n【引证文献】：\n",
    "next_line_abstract": page("某某研究", "【摘要】：\n这是摘要正文。\n"),
    "foreword": page("序《墨经正读》", "【摘要】：为某书所作的序。\n"),
}


def cnki(text):
    c.fetch = lambda api, url, prefix, route, force=False: text
    return c.cnki_page(2010, 6, 1)


CASS_TEXT = "《周易研究》2010年第6期\n某某研究/甲//5\n序《墨经正读》/乙//12\n另一篇论文/丙//20\n"


def verdict(cnki_pages, cass_text=CASS_TEXT):
    entries = c.cass_issues(cass_text)[(2010, 6)]
    cn = [cnki(t)[1] for t in cnki_pages]
    return c.issue_verdict(2010, 6, {"deepseek": entries, "moonshot": entries}, cn, [], False, [], "ok")


def case_empty(key):
    kind, e = cnki(PAGES[key])
    return kind == "article" and e["abstract"] == "" and e["notice"] is True


def case_normal():
    kind, e = cnki(PAGES["normal"])
    return e["abstract"] == "本文讨论易学。" and e["notice"] is False


def case_next_line():
    kind, e = cnki(PAGES["next_line_abstract"])
    return e["abstract"] == "这是摘要正文。" and e["notice"] is False


def case_research_titles():
    return all(c.research({"forms": [t]}) for t in ["序卦传的哲学意义", "论卦序", "《周易集解》序", "序言", "时序与卦气"])


def case_cass_foreword():
    flags = [c.research(e) for e in c.cass_issues(CASS_TEXT)[(2010, 6)]]
    return flags == [True, False, True]


def case_complete():
    v = verdict([PAGES["normal"], page("另一篇论文", "【摘要】：二。\n"), PAGES["empty_next_heading"]])
    return (v["complete"] and v["counts"]["waived_unmatched"] == 2
            and sorted(v["waived_unmatched"]) == [["cass", "序《墨经正读》"], ["cnki", "新书介绍《某某研究》"]])


def case_matched_empty_not_listed():
    v = verdict([page("某某研究", "【摘要】：\n"), page("另一篇论文", "【摘要】：二。\n")])
    return v["complete"] and v["waived_unmatched"] == [["cass", "序《墨经正读》"]]


def case_still_bites_research_page():
    v = verdict([page("某某研究", "【摘要】：一。\n"), page("另一篇论文", "【摘要】：二。\n"),
                 page("另有一文", "【摘要】：三，有摘要。\n")])
    return not v["complete"] and "cnki_not_in_cass" in v["fails"]


def case_still_bites_xu_title():
    text = CASS_TEXT + "序卦传的哲学意义/丁//30\n"
    v = verdict([page("某某研究", "【摘要】：一。\n"), page("另一篇论文", "【摘要】：二。\n")], text)
    return not v["complete"] and "cass_not_in_cnki" in v["fails"]


WRAPPED_TEXT = "《周易研究》2010年第6期\n某某研究/甲//5\n显晦宁殊奥，卓识发覆艰\n序《墨经正读》/乙//12\n另一篇论文/丙//20\n"


def case_wrapped_listing():
    entry = [e for e in c.cass_issues(WRAPPED_TEXT)[(2010, 6)] if e["forms"][0].startswith("序")][0]
    v = verdict([PAGES["normal"], page("另一篇论文", "【摘要】：二。\n")], WRAPPED_TEXT)
    return (len(entry["forms"]) == 2 and v["complete"]
            and v["waived_unmatched"] == [["cass", "显晦宁殊奥，卓识发覆艰序《墨经正读》"]])


CASES = [
    ("empty abstract before the next heading is a notice", lambda: case_empty("empty_next_heading")),
    ("same with a blank line between", lambda: case_empty("empty_blank_line")),
    ("a normal abstract is kept and is not a notice", case_normal),
    ("a <正> abstract is a notice", lambda: cnki(PAGES["zheng"])[1]["notice"] is True),
    ("a page with no abstract line is a notice", lambda: cnki(PAGES["no_abstract_line"])[1]["notice"] is True),
    ("an abstract starting on the next line is still read", case_next_line),
    ("a CNKI foreword page is not research", lambda: not c.research(cnki(PAGES["foreword"])[1])),
    ("titles containing 序 stay research", case_research_titles),
    ("a CASS foreword entry is not research, the others are", case_cass_foreword),
    ("issue passes with a foreword and an empty-abstract page; both listed as waived", case_complete),
    ("an empty-abstract page that CASS also holds is not listed as waived", case_matched_empty_not_listed),
    ("a research page with an abstract missing from CASS still fails", case_still_bites_research_page),
    ("a CASS research title with 序 missing from CNKI still fails", case_still_bites_xu_title),
    ("a wrapped CASS foreword is listed as waived in its joined reading", case_wrapped_listing),
]

# The rule still rejects. Each case breaks one thing in an issue that passes, and the verdict must name it.
FRAME = "中国知网 页面不存在 " * 4        # CNKI's frame page for an id it does not hold: neither heading in it
T1, T2, T3 = "关于卦序的新探", "论象数与义理之关系", "汉代易学人物考"
CASS3 = f"《周易研究》2010年第6期\n{T1}/甲//5\n{T2}/乙//12\n{T3}/丙//20\n"
ART = {i: page(t, f"【摘要】：摘要{i}。\n") for i, t in enumerate((T1, T2, T3), 1)}


def judged(cass, cnki_by_id, nap=()):
    """Issue 2010/6 judged as main() does, with no network. cass: {copy: page text, or None for a copy that did not
    open}; cnki_by_id: CNKI page text by id (None: the fetch failed; an id that is absent is CNKI's frame page)."""
    c.fetch = lambda api, url, prefix, route, force=False: cnki_by_id.get(int(url[-7:-4]), FRAME)
    c.time.sleep = lambda s: None
    copies = {n: (None if t is None else c.cass_issues(t).get((2010, 6), [])) for n, t in cass.items()}
    cnki, gaps, capped = c.cnki_run(2010, 6, len(c.usable_copies(copies)[0]))
    return c.issue_verdict(2010, 6, copies, cnki, gaps, capped, list(nap), "ok")


def both(text):
    return {"deepseek": text, "moonshot": text}


def names(cass=None, cnki_by_id=ART, nap=()):
    return set(judged(cass or both(CASS3), cnki_by_id, nap)["fails"])


DECREASING = f"《周易研究》2010年第6期\n{T1}/甲//20\n{T2}/乙//12\n{T3}/丙//5\n"
REJECTS = [
    ("control: the unbroken issue is complete", lambda: judged(both(CASS3), ART)["complete"]),
    ("a CNKI page missing at the end of the run: cass_not_in_cnki", lambda: "cass_not_in_cnki" in names(cnki_by_id={1: ART[1], 2: ART[2]})),
    ("a CASS entry missing: cnki_not_in_cass", lambda: "cnki_not_in_cass" in names(both(f"《周易研究》2010年第6期\n{T1}/甲//5\n{T2}/乙//12\n"))),
    ("a CNKI id between two articles that is not one: cnki_gap", lambda: "cnki_gap" in names(cnki_by_id={1: ART[1], 3: ART[3]})),
    ("a CNKI id between two articles that does not open: cnki_gap_unopened", lambda: "cnki_gap_unopened" in names(cnki_by_id={1: ART[1], 2: None, 3: ART[3]})),
    ("no CASS copy carries the issue: cass_no_usable_copy", lambda: "cass_no_usable_copy" in names(both("无题\n"))),
    ("a CASS copy whose start pages decrease, the other unopened", lambda: {"cass_no_usable_copy", "cass_page_not_opened"} <= names({"deepseek": DECREASING, "moonshot": None})),
    ("a napstic title that is not in the listing: napstic_not_in_listing", lambda: "napstic_not_in_listing" in names(nap=("一篇不在目录里的文章",))),
    ("a different title in place of one is missing on both sides", lambda: {"cass_not_in_cnki", "cnki_not_in_cass"} <= names(cnki_by_id={**ART, 3: page("魏晋玄学新论", "【摘要】：三。\n")})),
]

bad = 0
for group, cases in (("the amendment", CASES), ("the rule still rejects", REJECTS)):
    group_bad = 0
    for name, fn in cases:
        try:
            ok = bool(fn())
        except Exception as exc:  # a missing function or key in the frozen code counts as a failed case
            ok = False
            name += f"  [{type(exc).__name__}: {exc}]"
        group_bad += not ok
        print("PASS" if ok else "FAIL", "-", name)
    print(f"{len(cases) - group_bad} of {len(cases)} pass: {group}")
    bad += group_bad
sys.exit(1 if bad else 0)
