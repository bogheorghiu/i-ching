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

bad = 0
for name, fn in CASES:
    try:
        ok = bool(fn())
    except Exception as exc:  # a missing function or key in the frozen code counts as a failed case
        ok = False
        name += f"  [{type(exc).__name__}: {exc}]"
    bad += not ok
    print("PASS" if ok else "FAIL", "-", name)
print(f"{len(CASES) - bad} of {len(CASES)} pass")
sys.exit(1 if bad else 0)
