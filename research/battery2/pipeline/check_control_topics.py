"""Checks of control_topics.py and controls_reread.py (CONTROLS-RULE.md 15.7.2) on invented texts: no network, no
private file.
Usage: python3 -I check_control_topics.py [PIPELINE_DIR]
PIPELINE_DIR holds control_topics.py, controls_reread.py, controls.py and build_keys.py; the default is this file's
folder. Give a folder holding a broken copy to see the checks fail. Exit status 1 if one fails."""
import contextlib
import hashlib
import importlib.util
import io
import json
import os
import random
import re
import shutil
import sys
import tempfile
import types

d = os.path.abspath(sys.argv[1] if len(sys.argv) > 1 else os.path.dirname(os.path.abspath(__file__)))


def load(name):
    spec = importlib.util.spec_from_file_location(f"{name}_under_test", os.path.join(d, f"{name}.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


m = load("control_topics")
bk = m.bk

NINE = {(2012, 2), (2012, 5), (2014, 4), (2014, 6), (2015, 6), (2016, 1), (2016, 6), (2017, 5), (2018, 1)}
SEED = "b2-controls-optionb-2026-11-23"
TMP = tempfile.mkdtemp(prefix="ctopics-")


def addendum(**facts):
    """A rule file whose section 16 holds the facts as lines "- `label`: `value`" (a decoy before section 16 must not
    be read). The code under test reads the one that its module's RULE names."""
    path = os.path.join(tempfile.mkdtemp(dir=TMP), "CONTROLS-RULE.md")
    lines = "".join(f"- `{k.replace('_', '-')}`: `{v}`\n" for k, v in facts.items())
    decoys = {k.replace("_", "-") for k in facts} | {"prompt-sha256"}
    with open(path, "w", encoding="utf-8") as f:
        f.write("# Rule\n\n" + "".join(f"- `{k}`: `decoy`\n" for k in sorted(decoys)) + "\n## 16. Addendum\n\n" + lines)
    return path


def raises(fn, exc=None):
    try:
        fn()
    except exc or m.Stop:
        return True
    return False


# ----------------------------------------------------------------------------- 15.2: one case per verdict
LISTING = [["易道广大悉备论"], ["某某卦变说之研究"]]
FAKE = "完全无关的虚构文章题目"


def score(title=FAKE, year=2015, issue=None, venue="周易研究", flagged=NINE, rulings=()):
    return m.score_control_b({"title": title, "venue": venue, "year": year, "issue": issue}, LISTING, 2010,
                             flagged, rulings)


V_NINE = {**{f"{y}/{i}": {"complete": True} for y in range(2010, 2020) for i in range(1, 7)},
          **{f"{y}/{i}": {"complete": False} for y, i in NINE}}


def case_rulings():
    m.RULE = addendum(rulings="none")
    none = m.flagged_set(V_NINE) == NINE and m.registered_rulings() == set()
    m.RULE = addendum(rulings="2011/2,2013/4")
    two = m.registered_rulings() == {(2011, 2), (2013, 4)} and m.flagged_set(V_NINE) == NINE | {(2011, 2), (2013, 4)}
    return (none and two and m.certified_label(NINE) == "listing certified for 51 of 60 issues, not blind"
            and m.certified_label(NINE | {(2011, 2)}) == "listing certified for 50 of 60 issues, not blind")


SCORING = [
    ("each flagged issue, issue given: unresolved",
     lambda: all(score(year=y, issue=i) == "unresolved" for y, i in NINE)),
    ("a certified issue: invented", lambda: score(issue=3) == "invented"),
    ("a year holding a flagged issue, no issue: unresolved", lambda: score(issue=None) == "unresolved"),
    ("a year holding none, no issue: invented", lambda: score(year=2013) == "invented"),
    ("an impossible issue stays invented", lambda: score(issue=7) == "invented" and score(issue="第7期") == "invented"),
    ("wrong_real stays in a flagged issue", lambda: score(title="易道广大悉备论", issue=6) == "wrong_real"),
    ("ambiguous stays in a flagged issue", lambda: score(title="易道广大悉备论之新解", issue=6) == "ambiguous"),
    ("abstain stays", lambda: score(title="", issue=6) == "abstain"),
    ("another venue is scored as a real item", lambda: score(venue="哲学研究", issue=6) == "score_as_real_item"),
    ("a ruling adds an issue", lambda: score(year=2011, issue=2, flagged=NINE | {(2011, 2)}, rulings=[(2011, 2)])
     == "unresolved"),
    # 15.2.4
    ("issue string 第6期 is read", lambda: score(year="2015", issue="第6期") == "unresolved"),
    ("year string 2015年 is read", lambda: score(year="2015年", issue=6) == "unresolved"),
    ("Chinese numeral issue 第三期 is read", lambda: score(issue="第三期") == "invented"),
    ("Chinese numeral issue 十二 is read (impossible)", lambda: score(issue="十二") == "invented"
     and m.read_fields({"issue": "十二"}) == [(None, 12)]),
    ("Chinese year 二〇一三年 is read", lambda: score(year="二〇一三年", issue=3) == "invented"),
    ("a string only containing a number is not read", lambda: score(issue="大约第3期") == "unresolved"),
    ("an unreadable issue string is not given, not impossible", lambda: score(issue="某期") == "unresolved"
     and score(issue="") == "unresolved"),
    ("a mixed year string is not read", lambda: score(year="二0一五", issue=6) == "score_as_real_item"),
    ("compound in the year field", lambda: score(year="2015年第6期") == "unresolved"),
    ("a string only containing a compound is not read", lambda: score(year="约2015年第6期") == "score_as_real_item"),
    ("compound in the issue field", lambda: score(year=None, issue="2015年第3期") == "invented"),
    ("compound takes precedence over the other field", lambda: score(year=2016, issue="2013年第1期") == "invented"),
    ("two compounds naming different issues: the verdict under each reading, unresolved only if they differ",
     lambda: score(year="2013年第3期", issue="2013年第4期") == "invented"
     and score(year="2013年第3期", issue="2013年第4期", title="易道广大悉备论") == "wrong_real"
     and score(year="2012年第2期", issue="2012年第3期") == "unresolved"
     and score(year="2012年第3期", issue="2012年第2期") == "unresolved"
     and score(year="2013年第3期", issue="2013年第4期", venue="哲学研究") == "score_as_real_item"
     and score(year="2013年第3期", issue="2013年第4期", title="") == "abstain"
     and m.read_fields({"year": "2013年第3期", "issue": "2013年第4期"}) == [(2013, 3), (2013, 4)]),
    ("the same compound in both fields is one reading", lambda: m.read_fields(
        {"year": "2013年第3期", "issue": "2013年第3期"}) == [(2013, 3)]),
    ("spaces and full-width digits are read", lambda: m.read_fields({"year": " ２０１５ 年", "issue": "第 ６ 期"})
     == [(2015, 6)]),
    # 15.2.6
    ("flagged guard accepts the nine", lambda: m.flagged_set(V_NINE, ()) == NINE),
    ("flagged guard reads verdicts.json: an extra incomplete issue stops it", lambda: raises(lambda: m.flagged_set(
        {**V_NINE, "2011/2": {"complete": False}}, ()))),
    ("flagged guard reads verdicts.json: a complete one of the nine stops it", lambda: raises(lambda: m.flagged_set(
        {**V_NINE, "2018/1": {"complete": True}}, ()))),
    ("flagged guard: a ruling joins the flagged set", lambda: m.flagged_set(V_NINE, rulings=[(2011, 2)])
     == NINE | {(2011, 2)}),
    ("flagged guard: the rulings are the addendum's, and the label counts them", case_rulings),
    ("flagged guard refuses eight", lambda: raises(lambda: score(issue=6, flagged=NINE - {(2018, 1)}))),
    ("flagged guard refuses an extra issue without a ruling",
     lambda: raises(lambda: score(flagged=NINE | {(2011, 2)}))),
]

# ----------------------------------------------------------------------------- 15.3.1 headings
def page(year, blocks, english=None):
    out = []
    for i, lines in blocks.items():
        out.append(f"《周易研究》{year}年第{i}期")
        out += lines
    if english:
        out += ["TABLE OF CONTENTS"] + english
    return "\n".join(out)


COMMON = ["编辑：某某", "免责声明", "其他", "书讯", "栏目甲", "某某研究/甲//5"]
PAGE_A = page(2010, {
    1: COMMON + ["栏目丁", "栏目丙", "栏目戊", "栏目乙", "这是一条超过十二个字的很长很长的行"],
    2: COMMON + ["栏目丁", "栏目丙", "栏目戊", "栏目乙", "这是一条超过十二个字的很长很长的行"],
    3: COMMON + ["栏目丁", "栏目乙", "这是一条超过十二个字的很长很长的行"],
    4: ["栏目甲"]}, english=["栏目乙", "栏目丙"])
PAGE_B = page(2011, {1: COMMON + ["栏目丙"]}) + "\n" + page(2010, {1: ["栏目戊"], 2: ["栏目戊"]})


def case_headings():
    return m.headings([PAGE_A, PAGE_B]) == ["栏目甲", "栏目丁", "栏目丙", "栏目乙"]


def case_heading_cap():
    names = ["专题" + a + b for a in "甲乙丙丁戊" for b in "子丑寅卯辰"][:22]
    text = page(2012, {i: (names if i <= 3 else []) + ["栏目庚"] for i in range(1, 5)})
    hs = m.headings([text])
    return len(hs) == 20 and hs[0] == "栏目庚" and hs[1:] == sorted(bk.norm(n) for n in names)[:19]


def case_latin_ends_issue():
    text = "《周易研究》2010年第1期\nZhou Yi Studies Paper/周某//5\n栏目甲\n" + page(2010, {2: ["栏目甲"], 3: ["栏目甲"]})
    return m.headings([text]) == []


def case_heading_length():
    twelve, thirteen = "象" * 12, "象" * 13
    return m.headings([page(2010, {i: [twelve, thirteen] for i in range(1, 4)})]) == [twelve]


HEADINGS = [
    ("headings: 12 characters in, 13 out", case_heading_length),
    ("headings: recurrence, exclusions, English part, copies counted once, order", case_headings),
    ("headings: editor credit, disclaimer and 其他 excluded", lambda: not {"编辑某某", "免责声明", "其他"}
     & set(m.headings([PAGE_A, PAGE_B]))),
    ("headings: at most 20, by issues then norm order", case_heading_cap),
    ("headings: a Latin title line ends the issue", case_latin_ends_issue),
]

# ----------------------------------------------------------------------------- 15.3.2-15.3.5 drafting
def fake_chat(replies, log):
    def chat(model, messages, purpose, anthropic, max_tokens=None, reasoning_tokens=None):
        log.append((purpose, anthropic, max_tokens, reasoning_tokens, messages[0]["content"]))
        r = replies.pop(0)
        if isinstance(r, Exception):
            raise r
        return r
    return chat


PROMPT = "【测试】{heading}｜{count}"


def run_draft(hs, replies, ddir=None):
    ddir = ddir or tempfile.mkdtemp(dir=TMP)
    log = []
    bk.openrouter_chat = fake_chat(replies, log)
    calls = m.draft(hs, PROMPT, "x", "some/model", ddir)
    return calls, log, ddir


def case_retry():
    calls, log, ddir = run_draft(["甲", "乙", "丙"], ["not json", '["天地人和"]', None, '["山泽通气"]', "[]", '[""]'])
    return (calls == 6 and m.saved_topics(["甲", "乙", "丙"], ddir, "some/model", "x") == [["天地人和"], ["山泽通气"], []]
            and all(c[1:4] == (False, 16000, 8000) for c in log) and "334" in log[0][4] and "333" in log[4][4])


def case_resume():
    try:
        run_draft(["甲", "乙"], ['["天地人和"]', bk.InfraError("down")], ddir := tempfile.mkdtemp(dir=TMP))
        return False
    except bk.InfraError:
        pass
    calls, log, _ = run_draft(["甲", "乙"], ['["山泽通气"]'], ddir)
    again, _, _ = run_draft(["甲", "乙"], [], ddir)
    return calls == 1 and "乙" in log[0][4] and again == 0


def case_allocation():
    return m.allocation(13) == [77] * 12 + [76] and sum(m.allocation(7)) == 1000


def case_keep():
    items = ["天地人和", " 天地人和", "　易學思想史　", "易学思想史", "abc天地", "天地 人和", "天地", "天地人", "五" * 17, 5,
             "䷀䷁䷂䷃", "探索未知", "山泽通气", "五" * 16]
    kept, drops = m.keep([items], ["探索未知"])
    return kept == [(0, "天地人和"), (0, "易學思想史"), (0, "山泽通气"), (0, "五" * 16)] and drops == {
        "format": 7, "duplicate": 2, "probe_topic": 1}


def case_saved_replies_checked():
    _, _, ddir = run_draft(["甲", "乙", "丙"], ['["天地人和"]'] * 3)
    hs = ["甲", "乙", "丙"]
    return (m.saved_topics(hs, ddir, "some/model", "x") == [["天地人和"]] * 3
            and raises(lambda: m.saved_topics(hs, ddir, "other/model", "x"))
            and raises(lambda: m.saved_topics(hs, ddir, "some/model", "y"))
            and raises(lambda: m.saved_topics(["甲", "乙", "丁"], ddir, "some/model", "x")))


def case_topics_of():
    return (m.topics_of('共[77]个题目：["天地人和","山泽通气"]') == ["天地人和", "山泽通气"]
            and m.topics_of('[["天地人和"]]') == ["天地人和"] and m.topics_of('```json\n["天地人和"]\n```') == ["天地人和"]
            and m.topics_of("[77]") is None and m.topics_of("[]") is None and m.topics_of("无") is None
            and m.topics_of(None) is None)


def case_reply_saved_before_retry():
    ddir = tempfile.mkdtemp(dir=TMP)
    if not raises(lambda: run_draft(["甲"], ["not json", bk.InfraError("down")], ddir), bk.InfraError):
        return False
    return bk.read_json(os.path.join(ddir, "00.json"))["replies"] == ["not json"]


def case_model_guard():
    m.RULE = addendum(model="deepseek/deepseek-chat")
    refused = raises(m.registered_model)
    m.RULE = addendum(model="qwen/qwen3-235b-a22b:exacto")
    return refused and m.registered_model() == "qwen/qwen3-235b-a22b:exacto" and all(
        m.UNDER_TEST.search(n) for n in ("moonshotai/kimi-k2", "z-ai/glm-4.6", "xiaomi/mimo-v2", "DeepSeek/x"))


DRAFTING = [
    ("topics_of: the first list that holds a topic, from fences or prose", case_topics_of),
    ("drafting: the first reply is saved before the retry is asked", case_reply_saved_before_retry),
    ("drafting: saved replies are used only if the registered model and prompt made them", case_saved_replies_checked),
    ("drafting: the model in the addendum is not one under test", case_model_guard),
    ("1000 // H per heading, remainder to the first", case_allocation),
    ("one retry on unparseable, None or empty; request body as 15.3.4", case_retry),
    ("a resume asks only headings not yet answered", case_resume),
    ("keep rule: format, duplicates after norm, probe topics dropped", case_keep),
    ("a probe topic is never kept", lambda: m.keep([["探索未知"]], ["探索未知"])[0] == []),
]

# ----------------------------------------------------------------------------- 15.4.1-15.4.3 checks
LST = {"forms": ["论易学研究之方法", "目录", "某某卦变说之研究"], "abstracts": [bk.norm("本文论五行说的源流，兼及法研究之途。")]}
CHECKS = [
    ("title rule drops a shared 3-gram", lambda: m.title_hit("某某易学研究", LST["forms"])),
    ("title rule passes a topic with none", lambda: not m.title_hit("天地人和", LST["forms"])),
    ("abstract rule drops a shared 3-gram (no shared 4-gram)", lambda: m.abstract_hit("阴阳五行说", LST["abstracts"])),
    ("abstract rule drops a generic 3-gram too", lambda: m.abstract_hit("天象历法研究", LST["abstracts"])),
    ("abstract rule passes a topic with none", lambda: not m.abstract_hit("天地人和", LST["abstracts"])),
    ("survivors count drops per rule", lambda: m.survivors([(0, "某某易学研究"), (0, "阴阳五行说"), (1, "天地人和")], LST)
     == ([(1, "天地人和")], {"title": 1, "abstract": 1})),
]

# ----------------------------------------------------------------------------- 15.5.1 order
def expected_order(surv, n):
    rng, groups = random.Random(SEED), []
    for h in range(n):
        g = sorted([t for hi, t in surv if hi == h], key=bk.norm)
        rng.shuffle(g)
        groups.append(g)
    out, k = [], 0
    while any(k < len(g) for g in groups):
        out += [(h, g[k]) for h, g in enumerate(groups) if k < len(g)]
        k += 1
    return out


SURV = [(h, "题" + a + b + c) for h, n in ((0, 9), (1, 4), (2, 7)) for a, b, c in
        [("甲乙丙丁戊己庚辛壬"[i], "子丑寅卯辰巳午未申"[i], "天地") for i in range(n)]]


ORDER = [
    ("order: sorted, one seeded shuffle per heading, round-robin", lambda: m.order(SURV, 3) == expected_order(SURV, 3)),
    ("order: headings alternate at the start", lambda: [h for h, _ in m.order(SURV, 3)[:6]] == [0, 1, 2, 0, 1, 2]),
]

# ----------------------------------------------------------------------------- 15.5.4 clue
TEMPLATE = "期刊论文·易学·《周易研究》·2010年代：{topic}"
CLUE = [
    ("clue passes for a clean topic", lambda: m.clue_check(TEMPLATE, "天地人和", LST["forms"])[1] is None),
    ("clue: a digit outside the decade token drops", lambda: m.clue_check(TEMPLATE.replace("期刊论文", "期刊论文1"), "天地人和",
                                                                         LST["forms"])[1] == "digit"),
    ("clue: no venue drops", lambda: m.clue_check(TEMPLATE.replace("周易研究", "某刊"), "天地人和", [])[1]
     == "format:anchor_missing"),
    ("clue: leak on the slot's text drops", lambda: m.clue_check(TEMPLATE, "某某易学研究", LST["forms"])[1]
     == "final_title"),
    ("clue: the slot is read by position, not str.replace", lambda: m.clue_check(
        "论{topic}，2010年代周易研究易学期刊论文。", "某论某某", ["某论某事"])[1] == "final_title"),
    ("template: one slot, and a clue for a 16-character topic that passes the format check",
     lambda: raises(lambda: m.check_template("{topic}{topic}"))
     and raises(lambda: m.check_template("易" * 120 + "{topic}"))
     and raises(lambda: m.check_template(TEMPLATE.replace("周易研究", "某刊"))) and m.check_template(TEMPLATE) is None),
    ("template: a clue of 120 characters with a 16-character topic passes, 121 does not",
     lambda: m.check_template("2010年代周易研究" + "易" * 94 + "{topic}") is None
     and raises(lambda: m.check_template("2010年代周易研究" + "易" * 95 + "{topic}"))),
]

# ----------------------------------------------------------------------------- 15.4.4, 15.8.2 the walk
URL_ZYJY = "https://www.cnki.com.cn/Article/CJFDTotal-ZYJY2014030050.htm"


def fake_search(answer, net):
    """answer(query, n) gives the n-th network reply for a query; a saved reply is read as ds_search reads it."""
    def ds(query, count, route):
        fn = f"s_{bk.sha(query + '|' + str(count))}.json"
        path = os.path.join(bk.SNAP, fn)
        if os.path.exists(path):
            return json.load(open(path, encoding="utf-8"))["r"], fn
        net.append(query)
        r = answer(query, sum(q == query for q in net))
        if isinstance(r, Exception):
            raise r
        json.dump({"r": r}, open(path, "w", encoding="utf-8"))
        return r, fn
    return ds


def walk_env(answer):
    bk.W = tempfile.mkdtemp(dir=TMP)
    bk.SNAP = os.path.join(bk.W, "snapshots")
    os.makedirs(bk.SNAP)
    net = []
    bk.ds_search = fake_search(answer, net)
    return net, os.path.join(bk.W, "walk.json")


def verdicts(drop=None):
    out = {f"{y}/{i}": {"complete": True, "listing": [], "abstracts": []}
           for y in range(2010, 2020) for i in range(1, 7)}
    out["2013/2"] = {"complete": True, "listing": [["论易学研究之方法"], ["目录"]], "abstracts": ["本文论五行说的源流。"]}
    out.pop(drop, None)
    return out


WLST = m.listing_of(verdicts(), ["某篇补入的文章题目"])
LISTING_CASES = [
    ("listing: forms of all 60 issues plus the added titles; abstracts after norm", lambda: WLST["forms"] == [
        "论易学研究之方法", "目录", "某篇补入的文章题目"] and WLST["abstracts"] == [bk.norm("本文论五行说的源流。")]
     and len(WLST["entries"]) == 3),
    ("listing: refused when an issue is missing", lambda: raises(lambda: m.listing_of(verdicts("2019/6"), []))),
]
OK = [{"url": "https://example.org/a", "title": "无关网页"}]
TOPICS = ["天地人" + c for c in "甲乙丙丁戊己庚辛壬癸子丑寅卯辰巳午未申酉戌亥金木水火土日月星"]
ITEMS = [[0, t] for t in TOPICS]


def one(results_by_try):
    net, path = walk_env(lambda q, n: results_by_try[min(n, len(results_by_try)) - 1])
    st = m.walk(ITEMS[:1], TEMPLATE, WLST, path)
    return st, net


def case_stop_24():
    net, path = walk_env(lambda q, n: OK)
    st = m.walk(ITEMS, TEMPLATE, WLST, path)
    return len(st["passes"]) == 24 and len(net) == 24 and st["next"] == 24


def case_budget():
    net, path = walk_env(lambda q, n: [{"url": URL_ZYJY, "title": "某"}])
    bk.ds_search(m.fill(TEMPLATE, TOPICS[0]), 10, "seed the cache")          # a saved reply is not counted
    net.clear()
    stopped = raises(lambda: m.walk(ITEMS, TEMPLATE, WLST, path, cap=3), m.Halt)
    st = json.load(open(path))
    return stopped and st["net"] == 3 and len(net) == 3 and st["next"] == 4


def case_budget_resume():
    net, path = walk_env(lambda q, n: [{"url": URL_ZYJY, "title": "某"}])
    raises(lambda: m.walk(ITEMS, TEMPLATE, WLST, path, cap=2), m.Halt)
    st = m.walk(ITEMS, TEMPLATE, WLST, path, cap=len(ITEMS))
    return st["net"] == len(ITEMS) and len(net) == len(ITEMS) and st["drops"] == {"url": len(ITEMS)}


def case_default_cap():
    return m.MAX_SEARCHES == 500 and m.parser().parse_args(
        ["walk", "--workdir", "w", "--page", "p"]
        + sum([[f"--{n}", "x"] for n in ("probe-topics", "verdicts", "added-titles", "template")], [])
    ).max_searches == 500


def case_empty_majority():
    net, path = walk_env(lambda q, n: [])
    stopped = raises(lambda: m.walk(ITEMS, TEMPLATE, WLST, path), m.Halt)
    st = json.load(open(path))
    return stopped and len(st["empty"]) == 20 and st["drops"] == {"empty": 9} and st["halted"] == "empty_majority" \
        and raises(lambda: m.walk(ITEMS, TEMPLATE, WLST, path))


def case_half_empty_goes_on():
    net, path = walk_env(lambda q, n: [] if n == 1 else OK)      # every clue: empty, then a result
    st = m.walk(ITEMS, TEMPLATE, WLST, path)
    return len(st["passes"]) == 24 and len(st["empty"]) == 48


def case_infra_resume():
    calls = {"n": 0}

    def answer(q, n):
        calls["n"] += 1
        return bk.InfraError("down") if calls["n"] == 3 else OK
    net, path = walk_env(answer)
    stopped = raises(lambda: m.walk(ITEMS[:5], TEMPLATE, WLST, path), bk.InfraError)
    mid = json.load(open(path))["next"]
    st = m.walk(ITEMS[:5], TEMPLATE, WLST, path)
    return stopped and mid == 2 and len(st["passes"]) == 5 and st["net"] == 6


def case_final_check_before_search():
    net, path = walk_env(lambda q, n: OK)
    st = m.walk([[0, "某某易学研究"], [0, "天地人和"]], TEMPLATE, WLST, path)
    return st["drops"] == {"final_title": 1} and len(net) == 1


def case_floor():
    lst6 = m.listing_of(verdicts(), ["六字标题文章", "五字标题文"])

    def drops(title):
        _, path = walk_env(lambda q, n: [{"url": "https://example.org/z", "title": title}])
        return m.walk([[0, "天地人和"]], TEMPLATE, lst6, path)["drops"]
    return drops("六字标题文章") == {"hit_rank": 1} and drops("五字标题文") == {}


def case_probe_cap():
    net, path = walk_env(lambda q, n: [] if n == 1 else OK)      # every clue: empty, then a result: two searches
    return raises(lambda: m.probe(TOPICS[:15], TEMPLATE, WLST, path), m.Halt) and json.load(open(path))["net"] == 20


def case_state_saved_after_each_item():
    _, path = walk_env(lambda q, n: OK)
    seen = []
    m.run([1, 2, 3], lambda item, st: seen.append(os.path.exists(path) and json.load(open(path))["next"]) or "pass",
          path, 500, "k")
    return seen == [False, 1, 2]


WALK = [
    ("walk stops at the 24th pass", case_stop_24),
    ("walk: a ZYJY 2010-2019 URL drops, and an unlisted title is counted", lambda: (lambda st, net: st["drops"] == {
        "url": 1} and st["zyjy_unlisted"] == 1)(*one([[{"url": URL_ZYJY, "title": "某篇不在目录中的文章"}]]))),
    ("walk: a ZYJY URL of another decade passes", lambda: one([[{"url": URL_ZYJY.replace("2014", "2009"),
                                                                  "title": "x"}]])[0]["passes"] == ITEMS[:1]),
    *LISTING_CASES,
    ("walk: hit_rank on an added title drops", lambda: one([[{"url": "https://example.org/d",
                                                             "title": "某篇补入的文章题目"}]])[0]["drops"] == {"hit_rank": 1}),
    ("walk: hit_rank on a listing form drops", lambda: one([[{"url": "https://example.org/b",
                                                               "title": "论易学研究之方法"}]])[0]["drops"] == {"hit_rank": 1}),
    ("walk: a short form (under 6) does not drop", lambda: one([[{"url": "https://example.org/c", "title": "目录",
                                                                   "snippet": "目录"}]])[0]["passes"] == ITEMS[:1]),
    ("walk: empty twice drops and counts", lambda: (lambda st, net: st["drops"] == {"empty": 1} and len(net) == 2)(
        *one([[], []]))),
    ("walk: the retry removes the cached empty reply", lambda: (lambda st, net: st["passes"] == ITEMS[:1]
                                                                and len(net) == 2)(*one([[], OK]))),
    ("walk: stops before the cap; cached replies not counted", case_budget),
    ("walk: a higher cap resumes in the same order", case_budget_resume),
    ("walk: the search cap is 500", case_default_cap),
    ("walk: more than half of the last 20 empty stops it, for good", case_empty_majority),
    ("walk: half empty does not stop it", case_half_empty_goes_on),
    ("walk: an InfraError stops; a resume starts at that candidate", case_infra_resume),
    ("walk: the state is saved after each item, so a killed run keeps its count", case_state_saved_after_each_item),
    ("walk: a ZYJY URL of 2020 passes", lambda: one([[{"url": URL_ZYJY.replace("2014", "2020"),
                                                       "title": "x"}]])[0]["passes"] == ITEMS[:1]),
    ("walk: a listing form of 6 characters is checked, one of 5 is not", case_floor),
    ("probe: at most 20 network searches, a retry included", case_probe_cap),
    ("walk: the final-clue check runs before the search", case_final_check_before_search),
    ("probe: at most 20 topics, the same check",
     lambda: raises(lambda: m.probe(["天地人和"] * 21, TEMPLATE, WLST, os.path.join(TMP, "p21.json")))
     and (walk_env(lambda q, n: OK) and m.probe(TOPICS[:3], TEMPLATE, WLST, os.path.join(bk.W, "p.json"))["next"]
          == 3)),
]

# ----------------------------------------------------------------------------- guards
def fake_repo(root, linked=False):
    os.makedirs(os.path.join(root, ".git"))
    if linked:          # a linked work tree of the same repository
        wt, gd = os.path.join(root, "..", os.path.basename(root) + "-wt"), os.path.join(root, ".git", "worktrees", "w")
        os.makedirs(wt)
        os.makedirs(gd)
        open(os.path.join(wt, ".git"), "w").write(f"gitdir: {gd}\n")
        open(os.path.join(gd, "commondir"), "w").write("../..\n")
        return wt
    return root


def case_guard():
    base = tempfile.mkdtemp(dir=TMP)
    repo, other, clone, clone_ssh = (os.path.join(base, n) for n in ("repo", "other", "clone", "clone-ssh"))
    here = os.path.join(repo, "research", "battery2", "pipeline")
    os.makedirs(here)
    for root, url in ((repo, "https://example.org/o/r.git"), (clone, "https://example.org/o/r/"),
                      (clone_ssh, "git@Example.org:o/R.git"), (other, "https://example.org/o/x")):
        fake_repo(root)
        with open(os.path.join(root, ".git", "config"), "w", encoding="utf-8") as f:
            f.write(f'[remote "origin"]\n\turl = {url}\n')
    wt = fake_repo(os.path.join(base, "repo2"), linked=True)
    here2 = os.path.join(base, "repo2", "x")
    return (raises(lambda: m.guard_workdir(os.path.join(repo, "private", "w"), here))
            and m.guard_workdir(os.path.join(other, "w"), here) is None
            and m.guard_workdir(os.path.join(base, "plain"), here) is None
            and raises(lambda: m.guard_workdir(os.path.join(wt, "w"), here2))
            and raises(lambda: m.guard_workdir(os.path.join(clone, "w"), here))
            and raises(lambda: m.guard_workdir(os.path.join(clone_ssh, "w"), here))
            and raises(lambda: m.guard_workdir(os.path.join(m.HERE, "w"))))


def case_repo_key():
    forms = ["https://github.com/Owner/Repo.git", "git@github.com:owner/repo.git", "ssh://git@github.com/owner/repo/",
             "https://user:tok@GitHub.com/owner/repo"]
    return (len({m.repo_key(f) for f in forms}) == 1
            and m.repo_key("https://github.com/owner/other") != m.repo_key(forms[0]))


def case_registered():
    m.RULE = addendum(template_sha256="aa", model="x/y")
    first = m.registered("template-sha256") == "aa" and m.registered("model") == "x/y"
    with open(m.RULE, "a", encoding="utf-8") as f:
        f.write("- `model`: `x/z`\n")
    later = m.registered("model") == "x/z"                      # the last line of a label counts
    unknown = raises(lambda: m.registered("prompt-sha256"))
    section_end = os.path.join(TMP, "section-end.md")
    open(section_end, "w", encoding="utf-8").write(
        "## 16. Addendum\n- `model`: `a`\n\n## 17. A test\n- `model`: `b`\n- `prompt-sha256`: `c`\n")
    m.RULE = section_end
    ended = m.registered("model") == "a" and raises(lambda: m.registered("prompt-sha256"))
    no_section = os.path.join(TMP, "no-section.md")
    open(no_section, "w", encoding="utf-8").write("# Rule\n- `model`: `a`\n")
    m.RULE = no_section
    return first and later and unknown and ended and raises(lambda: m.registered("model"))


def case_hash():
    p = os.path.join(TMP, "private.txt")
    open(p, "w", encoding="utf-8").write("某某")
    good = hashlib.sha256("某某".encode()).hexdigest()
    m.RULE = addendum(template_sha256=good.upper())
    right = m.read_private(p, "template-sha256") == "某某"
    m.RULE = addendum(template_sha256="0" * 64)
    return right and raises(lambda: m.read_private(p, "template-sha256"))


def case_norm_mode():
    m.RULE = addendum(norm_mode=m.norm_mode())
    right = m.check_norm_mode() is None
    m.RULE = addendum(norm_mode="opencc 0.0")
    return right and raises(m.check_norm_mode)


def case_cli_headings():
    snaps = []
    for i, text in enumerate((PAGE_A, PAGE_B)):
        snaps.append(os.path.join(TMP, f"cd_{i}.json"))
        json.dump({"status": 200, "response": {"content": text}}, open(snaps[-1], "w", encoding="utf-8"))
    hs = m.headings([PAGE_A, PAGE_B])
    w = tempfile.mkdtemp(dir=TMP)
    args = ["headings", "--workdir", w] + sum([["--page", s] for s in snaps], [])
    out = io.StringIO()
    m.RULE = addendum(norm_mode=m.norm_mode(), headings_sha256=m.list_sha(hs))
    with contextlib.redirect_stdout(out):
        m.main(args)
    m.RULE = addendum(norm_mode=m.norm_mode(), headings_sha256="0" * 64)
    bad = raises(lambda: m.main(args), SystemExit)
    m.RULE = addendum(norm_mode="not-this-mode", headings_sha256=m.list_sha(hs))
    wrong_mode = raises(lambda: m.main(args), SystemExit)
    return out.getvalue() == f"headings: {len(hs)}\n" and bad and wrong_mode


CLI = {}


def pipeline_fixture():
    """Invented files for the four subcommands, the addendum facts that fix them, and a work directory in which
    headings, draft and walk have run; the network functions are replaced by fakes. Built once."""
    if CLI:
        return CLI["fx"]
    T = tempfile.mkdtemp(dir=TMP)

    def write(name, text):
        path = os.path.join(T, name)
        open(path, "w", encoding="utf-8").write(text)
        return path, hashlib.sha256(text.encode()).hexdigest()

    def page_files(tag, names):
        out = []
        for y in range(2010, 2013):
            text = "\n".join(f"《周易研究》{y}年第{i}期\n" + "\n".join(names) + "\n某某研究/甲//5" for i in range(1, 7))
            out.append(os.path.join(T, f"{tag}_{y}.json"))
            json.dump({"status": 200, "response": {"content": text}}, open(out[-1], "w", encoding="utf-8"))
        return out
    pages, pages2 = page_files("cd", ["栏目甲", "栏目己", "栏目丙"]), page_files("two", ["栏目甲", "栏目己"])

    def heads(files):
        return m.headings([json.load(open(f, encoding="utf-8"))["response"]["content"] for f in files])
    ver = {f"{y}/{i}": {"complete": (y, i) not in NINE, "listing": [["论易学研究之方法"]], "abstracts": ["本文论五行说。"]}
           for y in range(2010, 2020) for i in range(1, 7)}
    files = {"verdicts": write("verdicts.json", json.dumps(ver, ensure_ascii=False)), "added": write("added.txt", ""),
             "template": write("template.txt", TEMPLATE), "probe": write("probe.txt", "探索未知\n山川草木\n"),
             "prompt": write("prompt.txt", PROMPT), "bad_template": write("bad-template.txt", "只有{topic}"),
             "bad_prompt": write("bad-prompt.txt", "没有占位符"),
             "verdicts2": write("verdicts2.json", json.dumps({**ver, "2011/2": {**ver["2011/2"], "complete": False}},
                                                           ensure_ascii=False))}
    facts = dict(norm_mode=m.norm_mode(), headings_sha256=m.list_sha(heads(pages)),
                 probe_topics_sha256=files["probe"][1],
                 prompt_sha256=files["prompt"][1], verdicts_sha256=files["verdicts"][1],
                 added_titles_sha256=files["added"][1], template_sha256=files["template"][1],
                 model="qwen/qwen3-235b-a22b:exacto", max_usd="1", rulings="none")
    calls, rnd = [], random.Random(1)
    pool = "天地人和山泽通气雷风相薄水火不射日月星辰金木土石草花鸟兽虫鱼"

    def chat(model, messages, purpose, anthropic, max_tokens=None, reasoning_tokens=None):
        bk.LEDGER.check()                                        # as openrouter_chat does before it posts
        calls.append(model)
        return json.dumps(["".join(rnd.choice(pool) for _ in range(5)) for _ in range(400)], ensure_ascii=False)
    bk.openrouter_chat, bk.ds_search = chat, fake_search(lambda q, n: OK, [])

    def cmd(name, work, pg=pages, **paths):
        f = {k: v[0] for k, v in files.items()} | paths
        pages_ = sum([["--page", p] for p in pg], [])
        lst = ["--verdicts", f["verdicts"], "--added-titles", f["added"], "--template", f["template"]]
        return {"headings": ["headings", "--workdir", work, *pages_],
                "draft": ["draft", "--workdir", work, *pages_, "--probe-topics", f["probe"], "--prompt", f["prompt"]],
                "walk": ["walk", "--workdir", work, *pages_, "--probe-topics", f["probe"], *lst],
                "probe": ["probe", "--workdir", work, "--probe-topics", f["probe"], *lst]}[name]

    def run(args, **over):
        m.RULE = addendum(**{**facts, **over})
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            m.main(args)
        return out.getvalue()

    def stops(args, **over):
        return raises(lambda: run(args, **over), SystemExit)
    work = os.path.join(T, "work")
    fx = types.SimpleNamespace(T=T, files=files, facts=facts, calls=calls, cmd=cmd, run=run, stops=stops, work=work,
                               pages2=pages2, heads2=heads(pages2), ds=bk.ds_search,
                               outs=[run(cmd(n, work)) for n in ("headings", "draft", "walk")])
    CLI["fx"] = fx
    return fx


def case_cli_pipeline():
    """The four subcommands end to end: counts only on standard output, an InfraError's text never reaches it, the
    label of 15.6.4, the lengths for the owner, a resume that changes nothing."""
    fx = pipeline_fixture()
    bk.ds_search = lambda *a: (_ for _ in ()).throw(bk.InfraError("the reply repeats 探索未知"))
    try:
        probed = fx.run(fx.cmd("probe", fx.work))
    finally:
        bk.ds_search = fx.ds
    again = fx.run(fx.cmd("walk", fx.work))                          # a resume at the 24th pass changes nothing
    lengths = json.load(open(os.path.join(fx.work, "template-lengths.json")))
    counts_only = all(re.fullmatch(r"[a-z_.0-9]+: [^\u3400-\u9fff]*", ln) for o in (*fx.outs, probed, again)
                      for ln in o.splitlines())
    return (fx.outs[0] == "headings: 3\n" and "calls: 3" in fx.outs[1] and "controls: 24" in fx.outs[2]
            and "status: pass" in fx.outs[2] and "label: listing certified for 51 of 60 issues, not blind" in fx.outs[2]
            and again == fx.outs[2] and counts_only and "status: stopped: InfraError" in probed
            and "探索未知" not in probed
            and lengths == {"template": len(TEMPLATE) - len("{topic}"), "clue_4": len(TEMPLATE) - 3,
                            "clue_16": len(TEMPLATE) + 9})


def case_cli_guards():
    """Each input the code is given is checked against the addendum, one wrong value at a time, in a work directory
    where the same command has just run: nothing else can be what stops it."""
    fx = pipeline_fixture()
    bad = "0" * 64
    wrong = [("draft", "prompt_sha256", bad), ("draft", "probe_topics_sha256", bad), ("draft", "headings_sha256", bad),
             ("draft", "norm_mode", "not-this-mode"), ("draft", "model", "deepseek/deepseek-chat"),
             ("walk", "probe_topics_sha256", bad), ("walk", "verdicts_sha256", bad),
             ("walk", "added_titles_sha256", bad), ("walk", "template_sha256", bad), ("walk", "headings_sha256", bad),
             ("walk", "prompt_sha256", bad), ("walk", "model", "other/model"), ("walk", "rulings", "none,"),
             ("walk", "rulings", "2011/9"), ("walk", "rulings", "2012/2"),
             ("probe", "probe_topics_sha256", bad), ("probe", "verdicts_sha256", bad),
             ("probe", "added_titles_sha256", bad), ("probe", "template_sha256", bad)]
    each = [n + " " + k for n, k, v in wrong if not fx.stops(fx.cmd(n, fx.work), **{k: v})]
    before = len(fx.calls)
    w_budget = fx.run(fx.cmd("draft", os.path.join(fx.T, "w-budget")), max_usd="0")
    bad_t, bad_p = fx.files["bad_template"], fx.files["bad_prompt"]
    v2 = fx.files["verdicts2"]
    few = fx.run(fx.cmd("draft", os.path.join(fx.T, "w-few"), pg=fx.pages2), headings_sha256=m.list_sha(fx.heads2))
    ruled = fx.run(fx.cmd("walk", fx.work, verdicts=v2[0]), verdicts_sha256=v2[1], rulings="2011/2")
    return (not each and "calls: 0" in w_budget and "status: budget stop" in w_budget and len(fx.calls) == before
            and fx.stops(fx.cmd("walk", fx.work, template=bad_t[0]), template_sha256=bad_t[1])
            and fx.stops(fx.cmd("probe", fx.work, template=bad_t[0]), template_sha256=bad_t[1])
            and fx.stops(fx.cmd("draft", os.path.join(fx.T, "w-prompt"), prompt=bad_p[0]), prompt_sha256=bad_p[1])
            and "fewer than 3 headings" in few and len(fx.calls) == before
            and fx.stops(fx.cmd("walk", fx.work, verdicts=v2[0]), verdicts_sha256=v2[1])
            and "label: listing certified for 50 of 60 issues, not blind" in ruled)


def case_run_key():
    path = os.path.join(TMP, "key-state.json")
    m.run([1, 2], lambda item, st: "pass", path, 500, "k1")
    return raises(lambda: m.run([3, 4], lambda item, st: "pass", path, 500, "k2"))


GUARDS = [
    ("workdir guard: this repository refused, others and plain folders fine, a clone by any url form", case_guard),
    ("remote urls: the ssh and https forms of one repository agree", case_repo_key),
    ("addendum: the last line of a label in section 16, nothing before it, nothing without it", case_registered),
    ("hash guard: the sha256 in the addendum reads, another stops", case_hash),
    ("norm-mode guard: the mode in the addendum passes, another stops", case_norm_mode),
    ("command line: counts only on stdout; heading-list hash and norm mode checked", case_cli_headings),
    ("command line: the four subcommands end to end; counts only; no InfraError text; the label and the lengths",
     case_cli_pipeline),
    ("command line: every input is checked against the addendum, the model, the budget, the template, the prompt, "
     "the flagged set and the saved replies", case_cli_guards),
    ("walk and probe: a saved state belongs to its own list of items", case_run_key),
]


# ----------------------------------------------------------------------------- 15.2.7a-b controls_reread.py
FRAME = "中国知网 页面不存在 " * 4        # CNKI's frame page for an id it does not hold
CASS = {y: f"https://cass.example/{y}.shtml" for y in (2012, 2014, 2015, 2016)}
BLOCKS = {6: ("论乾坤二卦之象", "易传天道观新探"), 1: ("汉易卦气说考论", "庚氏易注之体例"),
          2: ("宋代图书易学述要", "己氏筮法再议"), 3: ("清代易学考据方法", "帛书易传义理"),
          4: ("易学与古代天文", "爻辰说源流考"), 5: ("象数易学的数理结构", "明代心学易诠释")}
T14 = {4: ("易学考古新证", "周易古经成书年代"), 6: ("辛氏易学方法论", "壬氏象学研究")}
T15, T16 = ("甲氏八宫说新解", "乙氏先天图考"), ("丙氏卦变说辨正", "丁氏易学述评")


def entries(issue, titles, start=3):
    return "".join(f"{t}/作者{issue}{k}//{start + 12 * k}\n" for k, t in enumerate(titles))


def english(k):
    return f"STUDIES OF ZHOUYI / No.{k} 2012\nOn the Changes, part {k}/ZHANG San//{k}\n"


def head(y, k):
    return f"《周易研究》{y}年第{k}期\n"


def page_2012(drop5=False, head_before_2=None):
    """Section 12's shape: headers 6; 5, 2, 1; 3; 4, and blocks in page order 6, 1, 2, 3, 4, 5, the blocks of 2 and 5
    after an English list with no header of their own."""
    b2 = (head(2012, head_before_2) if head_before_2 else "") + "易学史\n" + entries(2, BLOCKS[2])
    return ("期刊年鉴 2012年 目录\n" + head(2012, 6) + entries(6, BLOCKS[6]) + english(6)
            + head(2012, 5) + head(2012, 2) + head(2012, 1) + entries(1, BLOCKS[1]) + english(1)
            + b2 + english(2) + head(2012, 3) + entries(3, BLOCKS[3]) + english(3)
            + head(2012, 4) + entries(4, BLOCKS[4]) + english(4)
            + ("" if drop5 else entries(5, BLOCKS[5]) + english(5)) + "版权所有 某某研究所\n")


def art(title, abstract="本文讨论易学中的一个问题，并提出新的解释。", similar=""):
    return (f"# {title}\n【作者】：某\n【摘要】：{abstract}\n【引证文献】：\n"
            + (f"【相似文献】\n{similar}\n" if similar else ""))


def own(title, y, n, journal="周易研究"):
    return f"某某;{title}[J];{journal};{y}年{n:02d}期"


class Results:
    """A results folder as the re-run left it: snapshots/ named as controls.fetch names them."""

    def __init__(self, m, root):
        self.m, self.snap = m, os.path.join(root, "snapshots")
        self.root = root
        os.makedirs(self.snap, exist_ok=True)

    def put(self, prefix, url, text, status=200):
        self.m.bk.write_json(os.path.join(self.snap, f"{prefix}_{self.m.bk.sha(url)}.json"),
                             {"kind": "fetch", "url": url, "status": status, "response": {"content": text}})

    def cass(self, y, text, moonshot_status=200):
        self.put("cd", CASS[y], text)
        self.put("cm", CASS[y], text, moonshot_status)

    def cnki(self, y, n, pages, upto=12):
        for s in range(1, upto + 1):
            self.put("cd", f"https://www.cnki.com.cn/Article/CJFDTotal-ZYJY{y}{n:02d}{s:03d}.htm", pages.get(s, FRAME))

    def napstic(self, y, n, titles=()):
        text = f"{y}年0{n}期\n期刊开放获取文献列表页面的说明文字\n" + "".join(f"#### {t}\n" for t in titles)
        for p in (1, 2):
            self.put("cd", f"https://search.napstic.cn/literature/oaj/zhouyyj?page={p}&activeYear={y}&activeIssue={n}",
                     text if titles else "", 200 if titles else 404)


def build(m, root, missing_cnki_tail=False, moonshot_404=False):
    r = Results(m, root)
    r.cass(2012, page_2012())
    for n in (2, 5):
        r.cnki(2012, n, {k: art(t) for k, t in enumerate(BLOCKS[n], 1)})
        r.napstic(2012, n)
    r.cass(2014, head(2014, 4) + entries(4, T14[4]) + head(2014, 6) + entries(6, T14[6]),
           404 if moonshot_404 else 200)
    plate4 = art("图版说明", "", own("图版说明", 2018, 3, "另一学刊"))
    plate6 = art("图版二", "", own("图版二", 2020, 1, "另一学刊") + "\n" + own("图版二", 2014, 6))
    r.cnki(2014, 4, {1: plate4, **{k: art(t, similar=own(t, 2014, 4)) for k, t in enumerate(T14[4], 2)}},
           upto=5 if missing_cnki_tail else 12)
    r.cnki(2014, 6, {1: plate6, **{k: art(t, similar=own(t, 2014, 6)) for k, t in enumerate(T14[6], 2)}})
    for n in (4, 6):
        r.napstic(2014, n)
    r.cass(2015, head(2015, 6) + entries(6, T15))
    r.cnki(2015, 6, {k: art(t) for k, t in enumerate(T15, 1)})
    r.napstic(2015, 6, ("信息动态", T15[0]))
    r.cass(2016, head(2016, 1) + entries(1, T16))
    r.cnki(2016, 1, {k: art(t) for k, t in enumerate(T16, 1)})
    r.napstic(2016, 1, ("信息动态", "论信息动态的易学模型", T16[1]))
    return r


def reread_checks(load):
    """(name, ok) for each check of controls_reread.py; they share one set of synthetic results folders, so they run
    here, not as lambdas in a group."""
    m = load("controls_reread")
    tmp = tempfile.TemporaryDirectory()
    root = tmp.name
    real_post = m.bk.http_post

    def no_network(*a, **k):
        raise AssertionError("network call")
    m.bk.http_post = no_network
    res = build(m, os.path.join(root, "res"))
    c = m.frozen_copy(res.snap)

    def register(results_root, verdicts):
        """verdicts.json in a results folder, and an addendum that fixes its sha256."""
        path = os.path.join(results_root, "verdicts.json")
        m.bk.write_json(path, verdicts)
        m.control_topics.RULE = addendum(verdicts_sha256=m.control_topics.file_sha(path),
                                         norm_mode=m.control_topics.norm_mode())

    def judged(y, n, fixes=m.FIXES, copy=c):
        return m.read_issue(copy, y, n, CASS[y], fixes)

    def firsts(v):
        return sorted(f[0] for f in v["listing"])

    def raises(exc, fn):
        try:
            fn()
        except exc:
            return True
        return False

    def blocks_filed():
        parsed = c.cass_issues(m.file_blocks(page_2012(), 2012))
        return all([e["forms"][0] for e in parsed.get((2012, k), [])] == list(t) for k, t in BLOCKS.items())

    def frozen_files_none_under_2_5():
        parsed = c.cass_issues(page_2012())
        return (not parsed.get((2012, 2)) and not parsed.get((2012, 5))
                and parsed[(2012, 1)][0]["forms"][0] == BLOCKS[1][0])

    def issue_2012(n):
        old, new = judged(2012, n, ()), judged(2012, n)
        return ({"cass_no_usable_copy", "cnki_not_in_cass"} <= set(old["fails"]) and new["complete"]
                and new["counts"]["cass"] == new["counts"]["deepseek"] == new["counts"]["moonshot"] == 2
                and firsts(new) == sorted(BLOCKS[n]))

    def issue_2014(n):
        old, new = judged(2014, n, ()), judged(2014, n)
        return "cnki_catalogue_issue_mismatch" in old["fails"] and new["complete"]

    def catalogue_still_bites():
        wrong = art("某文", similar=own("某文", 2013, 2))
        return m.own_catalogue(wrong, "某文") == (2013, 2) and m.own_catalogue(art("某文"), "某文") is None

    def napstic_2015():
        old, new = judged(2015, 6, ()), judged(2015, 6)
        return ("napstic_not_in_listing" in old["fails"] and new["complete"]
                and new["napstic_exempt"] == ["信息动态"])

    def napstic_2016_still_bites():
        old, new = judged(2016, 1, ()), judged(2016, 1)
        return (old["fails"]["napstic_not_in_listing"] == ["信息动态", "论信息动态的易学模型"]
                and new["fails"] == {"napstic_not_in_listing": ["论信息动态的易学模型"]}
                and new["napstic_exempt"] == ["信息动态"])

    def missing_page():
        bad = build(m, os.path.join(root, "bad"), missing_cnki_tail=True)
        return raises(m.FetchAttempt, lambda: judged(2014, 4, copy=m.frozen_copy(bad.snap)))

    def failed_page_replayed():
        shut = build(m, os.path.join(root, "shut"), moonshot_404=True)
        v = judged(2014, 4, copy=m.frozen_copy(shut.snap))
        return v["fails"].get("cass_page_not_opened") == ["moonshot"]

    def shape(**kw):
        return raises(m.ShapeMismatch, lambda: m.file_blocks(page_2012(**kw), 2012))

    def other_years_untouched():
        text = head(2014, 4) + entries(4, T14[4])
        return m.file_blocks(text, 2014) == text

    def reread_cli():
        frozen = {f"{y}/{n}": judged(y, n, ()) for y, n in m.REREAD_ISSUES}
        register(res.root, frozen)
        work = os.path.join(root, "work")
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            m.main(["reread", res.root, "--workdir", work] + [f"--cass={y}={u}" for y, u in CASS.items()])
        text = buf.getvalue()
        written = [f for f in os.listdir(work) if f.startswith("reread-")]
        doc = m.bk.read_json(os.path.join(work, written[0])) if len(written) == 1 else {}
        rec = doc.get("issues", {})
        titles = [t for ts in (*BLOCKS.values(), *T14.values(), T15, T16) for t in ts] + ["信息动态"]
        return (len(text.splitlines()) == 6 and not any(t in text for t in titles)
                and "not blind" in doc.get("label", "")
                and all(r["replay_matches_frozen"] for r in rec.values())
                and [k for k, r in rec.items() if not r["reread"]["complete"]] == ["2016/1"])

    def replay_differs():
        old = judged(2014, 4, ())
        res4 = build(m, os.path.join(root, "res4"))
        m.bk.write_json(os.path.join(res4.root, "verdicts.json"), {"2014/4": {**old, "listing": old["listing"][1:]}})
        with contextlib.redirect_stdout(io.StringIO()):
            rec = m.reread(res4.root, CASS, ((2014, 4),))
        return rec["2014/4"]["replay_matches_frozen"] is False and rec["2014/4"]["new_titles"] == old["listing"][:1]

    def shape_cli():
        bad = build(m, os.path.join(root, "shape"))
        bad.cass(2012, page_2012(drop5=True))
        with contextlib.redirect_stdout(io.StringIO()):
            rec = m.reread(bad.root, CASS, ((2012, 2),))
        return rec["2012/2"]["reread"]["error"].startswith("ShapeMismatch") and not rec["2012/2"]["reread"]["complete"]

    def refuses_workdir_in_repository():
        res5, inside = os.path.join(root, "res5"), os.path.join(m.HERE, "private-work")
        os.makedirs(res5)
        register(res5, {})                       # a registered verdicts.json: only the work directory is wrong
        try:
            with contextlib.redirect_stderr(io.StringIO()), contextlib.redirect_stdout(io.StringIO()):
                refused = raises(SystemExit, lambda: m.main(["reread", res5, "--workdir", inside]
                                                            + [f"--cass={y}={u}" for y, u in CASS.items()]))
            return refused and not os.path.exists(inside)
        finally:
            shutil.rmtree(inside, ignore_errors=True)

    def refuses_unregistered_verdicts():
        res6, work = os.path.join(root, "res6"), os.path.join(root, "work6")
        os.makedirs(res6)
        register(res6, {"2016/6": {"listing": []}})
        m.bk.write_json(os.path.join(res6, "verdicts.json"), {"2016/6": {"listing": [["改过的题目"]]}})   # edited since
        with contextlib.redirect_stderr(io.StringIO()), contextlib.redirect_stdout(io.StringIO()):
            return (raises(SystemExit, lambda: m.main(["third", res6, "--workdir", work]))
                    and raises(SystemExit, lambda: m.main(["reread", res6, "--workdir", work]
                                                          + [f"--cass={y}={u}" for y, u in CASS.items()]))
                    and not os.path.exists(work))

    def parts_and_floor():
        lines = ["易学考古新证..........张三丰  5", "易学考古新证／张三丰", "易学考古新证——张三丰", "易学考古新证 / 张三丰 (5)"]
        entry = [["易学考古新证"]]
        notice = m.held_and_left("目录", [["目录"]])[0] == [["目录"]]               # a whole line is compared as it is
        return (all(m.held_and_left(ln, entry)[0] == entry for ln in lines) and notice
                and m.held_and_left("周易研究 2016年第6期 目录", [["目录"]])[0] == [])   # a part under 6 characters is not

    def other_year_header():
        return raises(m.ShapeMismatch, lambda: m.file_blocks(page_2012().replace(head(2012, 3), head(2013, 3)), 2012))

    def refuses_other_norm_mode():
        res8, work = os.path.join(root, "res8"), os.path.join(root, "work8")
        os.makedirs(res8)
        register(res8, {})
        m.control_topics.RULE = addendum(verdicts_sha256=m.control_topics.file_sha(os.path.join(res8, "verdicts.json")),
                                         norm_mode="opencc 0.0")
        with contextlib.redirect_stderr(io.StringIO()), contextlib.redirect_stdout(io.StringIO()):
            return raises(SystemExit, lambda: m.main(["third", res8, "--workdir", work])) and not os.path.exists(work)

    def napstic_notice_exact():
        return (m.napstic_notice("信息动态") and m.napstic_notice(" 信息 动态 ")
                and not m.napstic_notice("近年易学研究综述") and not m.napstic_notice("论信息动态的易学模型"))

    # ------------------------------------------------------------------------- 15.2.7b, with fake search and fetch
    LIST = {(2016, 6): [["易学考古新证"], ["周易古经成书年代", "某栏周易古经成书年代"], ["汉代易学人物与思想考"], ["象数易学新论"]],
            (2017, 5): [["辛氏易学方法论"]], (2018, 1): [["壬氏象学研究"]]}
    PAGE = ("周易研究 2016年第6期 目录\n易学考古新证 / 甲 (5)\n周易古经成书年代/乙//18\n汉代易学人物与思想考……某乙 32\n"
            "汉代易学人物考\n一篇只在此页的论文题目\n象数易学新说\n三个字\n四个汉字\n短行\n" + "宽" * 40 + "\n" + "长" * 41
            + "\nLatin only line here\n")

    def fake(n_results=7, pages=None):
        calls = {"search": [], "fetch": []}

        def search(query, count, route):
            calls["search"].append((query, count))
            k = len(calls["search"])
            return [{"url": f"https://h{k}r{r}.example/p", "title": "x"} for r in range(1, n_results + 1)], "s.json"

        def fetch(url):
            calls["fetch"].append(url)
            return (pages or {}).get(url)
        return calls, search, fetch

    def third_run():
        calls, search, fetch = fake(pages={"https://h1r1.example/p": PAGE, "https://h3r2.example/p": "无关的页面" * 10})
        out, used = m.third_source(m.THIRD_ISSUES, LIST, search, fetch)
        return calls, out, used

    def third_counts():
        calls, out, used = third_run()
        queries = [q for q, _ in calls["search"]]
        return (used == {"searches": 6, "fetches": 30} and len(calls["fetch"]) == 30
                and queries == ["周易研究 2016年第6期 目录", "Zhouyi Yanjiu 2016 No.6", "周易研究 2017年第5期 目录",
                                "Zhouyi Yanjiu 2017 No.5", "周易研究 2018年第1期 目录", "Zhouyi Yanjiu 2018 No.1"]
                and all(cnt == 5 for _, cnt in calls["search"]))

    def third_rank_and_host():
        _, out, _ = third_run()
        p = out["2016/6"]["pages"]
        return ([(x["rank"], x["url"], x["host"]) for x in p[:5]]
                == [(r, f"https://h1r{r}.example/p", f"h1r{r}.example") for r in range(1, 6)] and len(p) == 10)

    def third_held_and_left():
        _, out, _ = third_run()
        p = out["2016/6"]["pages"][0]
        return (p["held_count"] == 3 and p["held"] == LIST[(2016, 6)][:3] and p["opened"]
                and p["leftover"] == ["周易研究 2016年第6期 目录", "汉代易学人物考", "一篇只在此页的论文题目", "象数易学新说",
                                      "四个汉字", "宽" * 40])

    def third_none_found():
        _, out, _ = third_run()
        return (not out["2016/6"]["none_found"] and out["2017/5"]["none_found"] and out["2018/1"]["none_found"]
                and out["2017/5"]["pages"][1]["opened"] and out["2017/5"]["pages"][1]["held_count"] == 0)

    def search_cap():
        calls, search, fetch = fake(n_results=0)
        four = m.THIRD_ISSUES + ((2019, 1),)
        hit = raises(m.CapReached, lambda: m.third_source(four, {**LIST, (2019, 1): []}, search, fetch))
        return hit and len(calls["search"]) == 6

    def fetch_cap():
        calls, search, fetch = fake(n_results=10)
        top, m.TOP = m.TOP, 10           # with 5 results per query the search cap binds first
        try:
            hit = raises(m.CapReached, lambda: m.third_source(m.THIRD_ISSUES, LIST, search, fetch))
        finally:
            m.TOP = top
        return hit and len(calls["fetch"]) == 30

    def third_cli():
        verdicts = {f"{y}/{n}": {"listing": v} for (y, n), v in LIST.items()}
        res3 = os.path.join(root, "res3")
        os.makedirs(res3)
        register(res3, verdicts)
        calls, search, fetch = fake(pages={"https://h1r1.example/p": PAGE})
        saved = m.bk.ds_search, m.controls.fetch, m.bk.W, m.bk.SNAP
        m.bk.ds_search = search
        m.controls.fetch = lambda api, url, prefix, route, force=False: fetch(url)
        buf, work = io.StringIO(), os.path.join(root, "work3")
        try:
            with contextlib.redirect_stdout(buf):
                m.main(["third", res3, "--workdir", work])
            again = raises(SystemExit, lambda: m.main(["third", res3, "--workdir", work]))
        finally:
            m.bk.ds_search, m.controls.fetch, m.bk.W, m.bk.SNAP = saved
        text = buf.getvalue()
        return (again and os.path.exists(os.path.join(work, "third.json")) and len(text.splitlines()) == 4
                and "shortened" in m.bk.read_json(os.path.join(work, "third.json"))["note"]
                and "searches: 6 fetches: 30" in text and not any(s in text for s in ("易学", "目录", "论文", "example")))

    def refuses_other_issues():
        res7 = os.path.join(root, "res7")
        os.makedirs(res7)
        register(res7, {})                       # registered, so that only the issue restriction can stop it
        with contextlib.redirect_stderr(io.StringIO()), contextlib.redirect_stdout(io.StringIO()):
            return (raises(SystemExit, lambda: m.main(["reread", res7, "--workdir", os.path.join(root, "w7"),
                                                       "--issue", "2016/6", f"--cass=2016={CASS[2016]}"]))
                    and raises(SystemExit, lambda: m.main(["third", res7, "--workdir", os.path.join(root, "w7"),
                                                           "--issue", "2012/2"])))

    checks = [
        ("fault 1: the frozen reader files nothing under 2012/2 and 2012/5 (section 12's shape)",
         frozen_files_none_under_2_5),
        ("fault 1: every block of the 2012 page is filed under the issue section 12 gives", blocks_filed),
        ("fault 1: 2012/2 not complete by the frozen code, complete by the reader", lambda: issue_2012(2)),
        ("fault 1: 2012/5 not complete by the frozen code, complete by the reader", lambda: issue_2012(5)),
        ("fault 1: a 2012 page with five blocks stops the fix", lambda: shape(drop5=True)),
        ("fault 1: a header that contradicts section 12's order stops the fix", lambda: shape(head_before_2=4)),
        ("fault 1: the stop is recorded as an error and the issue is not complete", shape_cli),
        ("fault 1: another year's page is not changed", other_years_untouched),
        ("fault 2: 2014/4 (another journal's line only) fails frozen, complete by the reader", lambda: issue_2014(4)),
        ("fault 2: 2014/6 (another journal's line first, its own later) fails frozen, complete by the reader",
         lambda: issue_2014(6)),
        ("fault 2: an own line naming another issue still counts; no own line gives none", catalogue_still_bites),
        ("fault 3: 2015/6 fails frozen on the news column, complete by the reader", napstic_2015),
        ("fault 3: a research title napstic lists outside the listing still fails", napstic_2016_still_bites),
        ("a page the results folder does not hold is an error, not a fetch", missing_page),
        ("a saved page that did not open is read as not opened", failed_page_replayed),
        ("reread command: counts only on stdout, a record per issue, replay equal to verdicts.json", reread_cli),
        ("the work directory is refused inside the repository (control_topics.guard_workdir)",
         refuses_workdir_in_repository),
        ("a verdicts.json that the addendum does not hold is refused by both commands", refuses_unregistered_verdicts),
        ("fault 3: only the news column is exempt, as the whole title", napstic_notice_exact),
        ("third source: a title beside an author or a page is held; a part under 6 characters is not read",
         parts_and_floor),
        ("fault 1: a header of another year stops the fix", other_year_header),
        ("a norm mode that the addendum does not hold is refused", refuses_other_norm_mode),
        ("each command refuses issues outside 15.2.7a or 15.2.7b", refuses_other_issues),
        ("a replay that differs from verdicts.json is reported; titles verdicts.json lacks are listed", replay_differs),
        ("third source: 6 searches, 30 fetches, the two queries in order, 5 results asked", third_counts),
        ("third source: the first 5 results in rank order, each with its host", third_rank_and_host),
        ("third source: held entries and leftover lines (4-40 CJK) of a page", third_held_and_left),
        ("third source: none found where no page holds an entry", third_none_found),
        ("third source: the 7th search is refused", search_cap),
        ("third source: the 31st fetch is refused", fetch_cap),
        ("third command: counts only on stdout, third.json written, a second run refused", third_cli),
    ]
    results = []
    try:
        for name, fn in checks:
            try:
                ok = bool(fn())
            except Exception as exc:  # a missing function or a wrong shape counts as a failed check
                ok, name = False, f"{name}  [{type(exc).__name__}: {exc}]"
            results.append((name, ok))
    finally:
        m.bk.http_post = real_post
        tmp.cleanup()
    return results


bad = 0
for group, cases in (("scoring (15.2)", SCORING), ("headings (15.3.1)", HEADINGS), ("drafting (15.3.2-5)", DRAFTING),
                     ("checks (15.4.1-3)", CHECKS), ("order (15.5.1)", ORDER), ("clue (15.5.4)", CLUE),
                     ("walk and probe (15.4.4, 15.5, 15.8.2)", WALK), ("guards", GUARDS),
                     ("controls_reread.py (15.2.7a-b)", [(n, lambda ok=ok: ok) for n, ok in reread_checks(load)])):
    group_bad = 0
    for name, fn in cases:
        try:
            ok = bool(fn())
        except Exception as exc:  # an exception in the code under test counts as a failed case
            ok = False
            name += f"  [{type(exc).__name__}: {exc}]"
        group_bad += not ok
        print("PASS" if ok else "FAIL", "-", name)
    print(f"{len(cases) - group_bad} of {len(cases)} pass: {group}")
    bad += group_bad
shutil.rmtree(TMP, ignore_errors=True)
sys.exit(1 if bad else 0)
