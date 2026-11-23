"""Battery 2 negative controls, option b (CONTROLS-RULE.md section 15): the headings, the drafting of candidate topics,
their checks, the walk to 24 clues and the template probe; and score_control_b, the wrapper of score_control (15.2).

Usage: python3 -I control_topics.py SUBCOMMAND --workdir DIR ...   (SUBCOMMAND -h for its arguments)
  headings  derive the heading list from saved CASS pages and check its sha256
  draft     one call per heading; saved replies are reused on a resume
  walk      checks 15.4.1-15.4.4 and 15.5.4 in the order of 15.5.1, to the 24th pass
  probe     the template probe of 15.5.5
Every file it writes goes to DIR; standard output holds counts only.

What it needs to know in advance (the sha256 of each private file and of the heading list, the norm mode, the model
and the budget) it reads from the addendum, section 16 of CONTROLS-RULE.md, as lines "- `label`: `value`" (the last
line of a label counts), and it stops unless what it is given is what the addendum holds (15.7.1, 15.7.5). Labels:
template-sha256, prompt-sha256, probe-topics-sha256, verdicts-sha256, added-titles-sha256, headings-sha256,
norm-mode, model, max-usd, rulings ("none", or issues as "2011/2,2013/4"), and max-searches for a walk cap above 500.
"""
import argparse
import hashlib
import json
import os
import random
import re
import subprocess
import sys
import unicodedata

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import build_keys as bk  # noqa: E402
import controls  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
RULE = os.path.join(HERE, "CONTROLS-RULE.md")
NINE = {(2012, 2), (2012, 5), (2014, 4), (2014, 6), (2015, 6), (2016, 1), (2016, 6), (2017, 5), (2018, 1)}
DECADE = 2010
TOKEN = f"{DECADE}年代"
SEED = "b2-controls-optionb-2026-11-23"
N_CANDIDATES, N_CONTROLS, MAX_HEADINGS, MIN_HEADINGS, MIN_ISSUES, MAX_HEADING_LEN = 1000, 24, 20, 3, 3, 12
MAX_SEARCHES, PROBE_MAX, EMPTY_WINDOW, FLOOR = 500, 20, 20, 6
SLOT = "{topic}"
TOPIC = re.compile("[\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff]{4,16}")    # not the hexagram symbols (4DC0-4DFF)
ZYJY_URL = re.compile(r"(?i)CJFDTotal-ZYJY(20\d\d)")
# 15.5.4: a control has no record, so clue_format_check gets a synthetic one (venue branch).
SYNTH_ST = {"key": {"venue": controls.JOURNAL, "year": DECADE, "author": ""}, "stratum": {"language": "zh"}}
SYNTH_PAYLOAD = {"anchor": {"type": "venue"}}
UNDER_TEST = re.compile(r"deepseek|kimi|moonshot|glm|zhipu|z-ai|mimo|xiaomi", re.I)    # PREREG decision 2, 15.3.4


class Stop(Exception):
    """The code refuses to go on: a hash, a mode, a path or an input is not what the rule requires."""


class Halt(Exception):
    """The walk or the probe stops: "budget" (15.8.2) or "empty_majority" (15.4.4)."""


def need(cond, msg):
    if not cond:
        raise Stop(msg)


# ----------------------------------------------------------------------------- guards (15.1.4, 15.7.1, 15.7.5)
def git_common(path):
    """The common git directory of the work tree that holds path, or None."""
    p = os.path.realpath(path)
    while True:
        g = os.path.join(p, ".git")
        if os.path.isdir(g):
            return os.path.realpath(g)
        if os.path.isfile(g):
            with open(g, encoding="utf-8") as f:
                line = f.read().strip()
            gd = os.path.realpath(os.path.join(p, line.partition("gitdir:")[2].strip()))
            cd = os.path.join(gd, "commondir")
            if os.path.isfile(cd):
                with open(cd, encoding="utf-8") as f:
                    return os.path.realpath(os.path.join(gd, f.read().strip()))
            return gd
        if os.path.dirname(p) == p:
            return None
        p = os.path.dirname(p)


def repo_key(url):
    """A remote url without scheme, user, case and trailing .git: the ssh and https forms of one repository agree."""
    u = re.sub(r"^[a-z][a-z0-9+.-]*://", "", url.strip().lower())
    u = re.sub(r"^[^/@]*@", "", u)
    return u.replace(":", "/", 1).rstrip("/").removesuffix(".git").rstrip("/")


def remote_urls(common):
    """The urls in a git directory's config as repo_key reads them: another clone of this repository has the same."""
    try:
        with open(os.path.join(common, "config"), encoding="utf-8") as f:
            return {repo_key(u) for u in re.findall(r"^\s*url\s*=\s*(\S+)", f.read(), re.M)}
    except OSError:
        return set()


def history(common):
    """The commits of every ref in a git directory. A clone whose remote is written another way (a local path, a
    proxy url) is still this repository, and so is a public copy of it: each shares commits with this history."""
    r = subprocess.run(["git", "--git-dir", common, "rev-list", "--all"], capture_output=True, text=True)
    need(r.returncode == 0, "the history of a git work tree could not be read, so --workdir cannot be checked")
    return set(r.stdout.split())


def guard_workdir(workdir, here=HERE):
    mine, w = git_common(here), os.path.realpath(workdir)
    if mine is not None:
        theirs = git_common(w)
        need(theirs != mine and not (theirs and remote_urls(theirs) & remote_urls(mine)),
             "--workdir lies inside a work tree of this repository")
        need(not (theirs and history(theirs) & history(mine)),
             "--workdir lies inside a work tree that shares commits with this repository")
    else:   # an export without .git: the repository root is three levels up (research/battery2/pipeline)
        root = os.path.realpath(os.path.join(here, "..", "..", ".."))
        need(os.path.commonpath([root, w]) != root, "--workdir lies inside this repository's folder")


def file_sha(path):
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def registered(label):
    """15.7.1, 15.7.5: what the addendum (section 16 of the rule file) fixes for label."""
    with open(RULE, encoding="utf-8") as f:
        text = f.read()
    head = re.search(r"^## 16\.", text, re.M)
    need(head, "the rule file has no section 16, the addendum")
    after = re.search(r"^## ", text[head.end():], re.M)       # section 16 ends at the next section
    section = text[head.start():head.end() + after.start()] if after else text[head.start():]
    values = re.findall(rf"^- `{re.escape(label)}`: `([^`\n]+)`[ \t]*$", section, re.M)
    need(values, f"the addendum fixes no {label}")
    return values[-1]


def registered_model():
    """15.3.4: the model the addendum names; a model under test is refused."""
    model = registered("model")
    need(not UNDER_TEST.search(model), "the model in the addendum is one under test (15.3.4)")
    return model


def check_private(path, label):
    need(file_sha(path) == registered(label).lower(),
         f"sha256 of {os.path.basename(path)} is not the one in the addendum")


def read_private(path, label):
    check_private(path, label)
    with open(path, encoding="utf-8") as f:
        return f.read()


def lines_of(text):
    return [ln.strip() for ln in text.splitlines() if ln.strip()]


def list_sha(items):
    return hashlib.sha256("\n".join(items).encode("utf-8")).hexdigest()


def norm_mode():
    if bk._OCC is None:
        return "table"
    from importlib import metadata
    for name in ("opencc", "opencc-python-reimplemented"):
        try:
            return f"opencc {metadata.version(name)}"
        except metadata.PackageNotFoundError:
            pass
    return "opencc unknown"


def check_norm_mode():
    need(norm_mode() == registered("norm-mode"), f"norm mode here is {norm_mode()!r}, not the one in the addendum")


# ----------------------------------------------------------------------------- scoring (15.2)
CN_ISSUE = {"一": 1, "二": 2, "三": 3, "四": 4, "五": 5, "六": 6, "七": 7, "八": 8, "九": 9, "十": 10, "十一": 11,
            "十二": 12}
CN_DIGIT = dict(zip("〇零一二三四五六七八九", "00123456789"))
_X = "([0-9]+|十[一二]?|[一二三四五六七八九])"
_Y = "([0-9]{4}|[〇零一二三四五六七八九]{4})"
ISSUE_FORM, YEAR_FORM, BOTH_FORM = re.compile(f"第?{_X}期?"), re.compile(f"{_Y}年?"), re.compile(f"{_Y}年第?{_X}期")


def _issue(x):
    return int(x) if x.isascii() else CN_ISSUE[x]


def _year(y):
    return int("".join(CN_DIGIT.get(ch, ch) for ch in y))


def read_fields(answer):
    """15.2.4: the readings of the answer's year and issue, each string read as a number, or None when it has no form
    15.2.4 names. Normally one (year, issue); two when the fields hold compound strings that name different issues
    (the text says a compound takes precedence over the other field, which cannot hold for two), the year field's
    first."""
    out, both = {}, []
    for k, form, conv in (("year", YEAR_FORM, _year), ("issue", ISSUE_FORM, _issue)):
        v = answer.get(k)
        if not isinstance(v, str):
            out[k] = v
            continue
        s = re.sub(r"\s+", "", unicodedata.normalize("NFKC", v))
        m = BOTH_FORM.fullmatch(s)
        if m:
            reading = (_year(m.group(1)), _issue(m.group(2)))
            both += [reading] * (reading not in both)
            out[k] = None
            continue
        m = form.fullmatch(s)
        out[k] = conv(m.group(1)) if m else None
    return both or [(out["year"], out["issue"])]


def registered_rulings():
    """15.2.6: the issues the owner ruled not complete under 15.1.5, as the addendum names them."""
    value = registered("rulings").strip().lower()
    if value == "none":
        return set()
    need(re.fullmatch(r"\d{4}/\d(,\d{4}/\d)*", value),
         "the addendum's rulings are not 'none' or issues like 2011/2,2013/4")
    ruled = {tuple(map(int, x.split("/"))) for x in value.split(",")}
    need(all(DECADE <= y < DECADE + 10 and i in controls.ISSUES for y, i in ruled) and not ruled & NINE,
         "a ruling is not an issue of the decade that is outside the nine")
    return ruled


def flagged_set(verdicts, rulings=None):
    """15.2.6: the issues verdicts.json holds as not complete, plus the rulings (the addendum's, if not given); the
    code stops unless that is the nine plus the rulings."""
    rulings = registered_rulings() if rulings is None else set(rulings)
    got = {tuple(map(int, k.split("/"))) for k, v in verdicts.items() if not v.get("complete")} | rulings
    need(got == NINE | rulings, "the flagged set is not the nine of 15.2.6 plus the rulings")
    return got


def certified_label(flagged):
    """15.6.4: the label every statement about the controls carries."""
    return f"listing certified for {60 - len(flagged)} of 60 issues, not blind"


def score_reading(answer, year, issue, decade_listing, decade, flagged):
    v = controls.score_control({**answer, "year": year, "issue": issue}, decade_listing, decade)
    if v != "invented" or (issue is not None and issue not in controls.ISSUES):
        return v
    if issue is not None and (year, issue) in flagged:
        return "unresolved"                                                       # 15.2.1
    if issue is None and year in {y for y, _ in flagged}:
        return "unresolved"                                                       # 15.2.3
    return v


def score_control_b(answer, decade_listing, decade, flagged):
    """The verdict under each reading of the answer's year and issue; unresolved when two readings differ, since then
    the listing cannot say which issue the answer names."""
    need(set(flagged) == NINE | registered_rulings(),
         "the flagged set is not the nine of 15.2.6 plus the addendum's rulings")
    verdicts = {score_reading(answer, y, i, decade_listing, decade, flagged) for y, i in read_fields(answer)}
    return verdicts.pop() if len(verdicts) == 1 else "unresolved"


# ----------------------------------------------------------------------------- headings (15.3.1)
def _title_part(ln):
    t = ln.partition("//")[0] if "//" in ln else ln.rpartition("/")[0]
    return t.rpartition("/")[0] if "/" in t else t


def headings(texts):
    """The heading list in addendum order, as norm forms, from the texts of the saved CASS yearly pages. Issue
    boundaries are read as controls.cass_issues reads them."""
    issues_of = {}
    for text in texts:
        cur = None
        for raw in text.splitlines():
            ln = controls._clean(raw)
            if not ln:
                continue
            if controls.ENGLISH_PART.search(ln):
                cur = None
                continue
            m = controls.ISSUE_HEAD.search(ln)
            if m:
                cur = (int(m.group(1)), int(m.group(2)))
                continue
            if cur is None:
                continue
            if "/" in ln:
                if bk.has_cjk(ln) and controls.latin_line(_title_part(ln)):
                    cur = None
                continue
            n = bk.norm(ln)
            if not bk.has_cjk(ln) or len(n) > MAX_HEADING_LEN:
                continue
            if controls.NONRESEARCH.search(ln) or controls.NONRESEARCH.search(n):
                continue
            if n.startswith("编辑") or n in ("免责声明", "其他"):
                continue
            issues_of.setdefault(n, set()).add(cur)
    ranked = sorted((n for n, s in issues_of.items() if len(s) >= MIN_ISSUES), key=lambda n: (-len(issues_of[n]), n))
    return ranked[:MAX_HEADINGS]


def page_texts(paths):
    out = []
    for p in paths:
        snap = bk.read_json(p)
        need(isinstance(snap, dict) and controls._ok(snap), f"{os.path.basename(p)} is not a saved page with text")
        out.append(bk.fetch_text(snap.get("response")))
    return out


# ----------------------------------------------------------------------------- drafting (15.3.2-15.3.5)
def allocation(n_headings):
    q, r = divmod(N_CANDIDATES, n_headings)
    return [q + (i < r) for i in range(n_headings)]


def fill_prompt(prompt, heading, count):
    return prompt.replace("{heading}", heading).replace("{count}", str(count))


def topics_of(reply):
    """The first JSON list in a reply that holds a topic, else None (15.3.2: retry once)."""
    if not reply:
        return None
    t = re.sub(r"```(?:json)?", "", reply)
    dec = json.JSONDecoder()
    for m in re.finditer(r"\[", t):
        try:
            obj, _ = dec.raw_decode(t[m.start():])
        except ValueError:
            continue
        if isinstance(obj, list) and any(isinstance(x, str) and x.strip() for x in obj):
            return obj
    return None


def draft(hs, prompt, prompt_sha, model, ddir):
    """One call per heading, one retry; every reply is saved before the next call, so a resume asks only what is
    missing. Returns the number of calls made."""
    os.makedirs(ddir, exist_ok=True)
    calls = 0
    for i, (h, n) in enumerate(zip(hs, allocation(len(hs)))):
        path = os.path.join(ddir, f"{i:02d}.json")
        rec = bk.read_json(path) or {"heading": h, "count": n, "model": model, "prompt_sha256": prompt_sha,
                                     "replies": []}
        check_saved(rec, i, h, n, model, prompt_sha)
        while len(rec["replies"]) < 2 and (not rec["replies"] or topics_of(rec["replies"][-1]) is None):
            rec["replies"].append(bk.openrouter_chat(
                model, [{"role": "user", "content": fill_prompt(prompt, h, n)}], f"controls: draft {i:02d}",
                anthropic=False, max_tokens=16000, reasoning_tokens=8000))
            calls += 1
            bk.write_json(path, rec)
    return calls


def check_saved(rec, i, h, n, model, prompt_sha):
    need((rec["heading"], rec["count"], rec["model"], rec["prompt_sha256"]) == (h, n, model, prompt_sha),
         f"saved reply {i:02d} was asked for another heading, count, model or prompt")


def saved_topics(hs, ddir, model, prompt_sha):
    """The topics of the saved replies, which must be those the addendum's model and prompt gave (15.3.4)."""
    out = []
    for i, (h, n) in enumerate(zip(hs, allocation(len(hs)))):
        rec = bk.read_json(os.path.join(ddir, f"{i:02d}.json"))
        need(rec is not None, f"heading {i:02d} has not been drafted")
        check_saved(rec, i, h, n, model, prompt_sha)
        ok = topics_of(rec["replies"][-1]) if rec["replies"] else None
        need(ok is not None or len(rec["replies"]) == 2, f"heading {i:02d} has not been drafted")
        out.append(ok or [])
    return out


def keep(drafted, probe_topics):
    """15.3.5: (kept [(heading index, text)], drops by reason). Duplicates and probe topics are judged after norm: a
    script variant of a topic is the same topic, and the checks that follow read the norm form."""
    probe = {bk.norm(t) for t in probe_topics}
    kept, seen, drops = [], set(), {"format": 0, "duplicate": 0, "probe_topic": 0}
    for hi, items in enumerate(drafted):
        for x in items:
            t = unicodedata.normalize("NFKC", x).strip() if isinstance(x, str) else ""
            if not TOPIC.fullmatch(t):
                drops["format"] += 1
            elif bk.norm(t) in seen:
                drops["duplicate"] += 1
            elif bk.norm(t) in probe:
                drops["probe_topic"] += 1
            else:
                seen.add(bk.norm(t))
                kept.append((hi, t))
    return kept, drops


# ----------------------------------------------------------------------------- checks (15.4.1-15.4.3)
def listing_of(verdicts, added):
    keys = {f"{y}/{i}" for y in range(DECADE, DECADE + 10) for i in controls.ISSUES}
    need(keys <= set(verdicts) and all("listing" in verdicts[k] and "abstracts" in verdicts[k] for k in keys),
         "verdicts.json does not hold a listing and abstracts for all 60 issues")
    groups = [f for k in sorted(keys) for f in verdicts[k]["listing"]] + [[t] for t in added]
    forms = [t for g in groups for t in g]
    return {"forms": forms, "entries": [{"forms": g} for g in groups],
            "abstracts": [bk.norm(a) for k in sorted(keys) for a in verdicts[k]["abstracts"]]}


def title_hit(text, forms):
    return any(bk.leak_reason(text, t) for t in forms)


def abstract_hit(cand, norm_abstracts):
    n = bk.norm(cand)
    grams = {g for g in (n[i:i + 3] for i in range(len(n) - 2)) if bk._CJK3.match(g)}
    return any(g in a for a in norm_abstracts for g in grams)


def survivors(kept, lst):
    out, drops = [], {"title": 0, "abstract": 0}
    for hi, t in kept:
        if title_hit(t, lst["forms"]):
            drops["title"] += 1
        elif abstract_hit(t, lst["abstracts"]):
            drops["abstract"] += 1
        else:
            out.append((hi, t))
    return out, drops


# ----------------------------------------------------------------------------- order and clue (15.5.1-15.5.4)
def order(surv, n_headings):
    rng = random.Random(SEED)
    groups = []
    for h in range(n_headings):
        g = sorted((t for hi, t in surv if hi == h), key=bk.norm)
        rng.shuffle(g)
        groups.append(g)
    return [(h, g[k]) for k in range(max(map(len, groups), default=0)) for h, g in enumerate(groups) if k < len(g)]


def check_template(template):
    """The longest clue a candidate can make must pass 15.5.4's format and digit checks: 15.5.4 says they can drop
    none, and the probe does not run them, so a template that fails one would show only in the walk, after the
    freeze."""
    need(template.count(SLOT) == 1, f"the template must hold {SLOT} exactly once")
    bad = bk.clue_format_check(fill(template, "一" * 16), SYNTH_ST, SYNTH_PAYLOAD)
    need(not bad, f"a clue for a 16-character topic fails the format check: {bad}")
    need(not stray_digit(fill(template, "一" * 16)), "the template holds a digit outside the decade token")


def fill(template, cand):
    pre, _, post = template.partition(SLOT)
    return pre + cand + post


def slot_text(template, clue):
    pre, _, post = template.partition(SLOT)
    return clue[len(pre):len(clue) - len(post)]


def stray_digit(clue):
    """15.5.4: a digit outside the decade token."""
    return bool(re.search(r"\d", unicodedata.normalize("NFKC", clue).replace(TOKEN, "", 1)))


def clue_check(template, cand, forms):
    """15.5.4 on the clue as built: (clue, None) or (clue, reason)."""
    clue = fill(template, cand)
    bad = bk.clue_format_check(clue, SYNTH_ST, SYNTH_PAYLOAD)
    if bad:
        return clue, "format:" + bad
    if stray_digit(clue):
        return clue, "digit"
    if title_hit(slot_text(template, clue), forms):
        return clue, "final_title"
    return clue, None


# ----------------------------------------------------------------------------- the search (15.4.4, 15.8.2)
def search(clue, st):
    """One ds_search; st counts the calls that reach the network and keeps the empty/non-empty history."""
    fn = f"s_{bk.sha(clue + '|10')}.json"              # the file ds_search reads for this query (a clue is <= 120)
    path = os.path.join(bk.SNAP, fn)
    if not os.path.exists(path):
        if st["net"] >= st["cap"]:
            raise Halt("budget")
        st["net"] += 1
    results, got = bk.ds_search(clue, 10, "controls: identifiability")
    need(got == fn, "ds_search names its snapshot differently from this code")
    st["empty"].append(not results)
    if len(st["empty"]) >= EMPTY_WINDOW and sum(st["empty"][-EMPTY_WINDOW:]) > EMPTY_WINDOW / 2:
        st["halted"] = "empty_majority"
        raise Halt("empty_majority")
    return results, path


def ident(clue, lst, st):
    """15.4.4: "pass" or the reason the clue is dropped."""
    results, path = search(clue, st)
    if not results:
        os.remove(path)
        results, path = search(clue, st)
        if not results:
            return "empty"
    zyjy = [r for r in results if (m := ZYJY_URL.search(bk.r_url(r))) and DECADE <= int(m.group(1)) < DECADE + 10]
    st["zyjy_unlisted"] += sum(controls.best([str(r.get("title", "")) if isinstance(r, dict) else ""], lst["entries"])
                               < controls.SIM_MATCH for r in zyjy)
    if zyjy:
        return "url"
    if any(bk.hit_rank(results, t, []) for t in lst["forms"] if len(bk.norm(t)) >= FLOOR):
        return "hit_rank"
    return "pass"


def new_state(cap, key):
    return {"key": key, "next": 0, "passes": [], "drops": {}, "net": 0, "cap": cap, "empty": [], "zyjy_unlisted": 0,
            "halted": None}


def run(items, step, path, cap, key, stop_at=None):
    """Applies step to each item in order, saving the state after each, so a resume (after an InfraError or a
    budget stop) starts again at the item that did not finish. Returns the state."""
    st = bk.read_json(path) or new_state(cap, key)
    need(st["key"] == key, "the saved state belongs to other inputs")
    need(st["halted"] is None, "stopped earlier on empty replies (15.4.4); a new route needs the owner")
    st["cap"] = cap
    try:
        for idx in range(st["next"], len(items)):
            if stop_at is not None and len(st["passes"]) >= stop_at:
                break
            r = step(items[idx], st)
            if r == "pass":
                st["passes"].append(items[idx])
            else:
                st["drops"][r] = st["drops"].get(r, 0) + 1
            st["next"] = idx + 1
            bk.write_json(path, st)     # a killed run keeps its count; the finally also saves the item that stopped
    finally:
        bk.write_json(path, st)
    return st


def walk(items, template, lst, path, cap=MAX_SEARCHES):
    def step(item, st):
        clue, bad = clue_check(template, item[1], lst["forms"])
        return bad or ident(clue, lst, st)
    key = hashlib.sha256(json.dumps([items, template, lst], ensure_ascii=False).encode()).hexdigest()
    return run(items, step, path, cap, key, stop_at=N_CONTROLS)


def probe(topics, template, lst, path):
    need(len(topics) <= PROBE_MAX, f"at most {PROBE_MAX} probe topics")
    return run(topics, lambda t, st: ident(fill(template, t), lst, st), path, PROBE_MAX,
               hashlib.sha256(json.dumps(topics).encode()).hexdigest())


# ----------------------------------------------------------------------------- command line
def report(**counts):
    for k, v in counts.items():
        if isinstance(v, dict):
            for kk, vv in v.items():
                print(f"{k}.{kk}: {vv}")
        else:
            print(f"{k}: {v}")


def parser():
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = p.add_subparsers(dest="cmd", required=True)
    base = argparse.ArgumentParser(add_help=False)
    base.add_argument("--workdir", required=True)
    pages = argparse.ArgumentParser(add_help=False)
    pages.add_argument("--page", action="append", required=True, help="a saved CASS yearly page (snapshot JSON)")
    sub.add_parser("headings", parents=[base, pages])
    d = sub.add_parser("draft", parents=[base, pages])
    w = sub.add_parser("walk", parents=[base, pages])
    pr = sub.add_parser("probe", parents=[base])
    for q in (d, w, pr):
        q.add_argument("--probe-topics", required=True)
    d.add_argument("--prompt", required=True)
    for q in (w, pr):
        for name in ("verdicts", "added-titles", "template"):
            q.add_argument(f"--{name}", required=True)
    w.add_argument("--max-searches", type=int, default=MAX_SEARCHES, help="a higher cap needs the owner's go (15.6.3)")
    return p


def main(argv=None):
    a = parser().parse_args(argv)
    try:
        guard_workdir(a.workdir)
        check_norm_mode()
        bk.W = os.path.realpath(a.workdir)
        bk.SNAP = os.path.join(bk.W, "snapshots")
        os.makedirs(bk.SNAP, exist_ok=True)
        hs = None
        if a.cmd != "probe":
            hs = headings(page_texts(a.page))
            need(list_sha(hs) == registered("headings-sha256").lower(),
                 "sha256 of the heading list is not the one in the addendum")
            bk.write_json(os.path.join(bk.W, "headings.json"), {"headings": hs, "pages": {
                os.path.basename(p): file_sha(p) for p in a.page}})
        if a.cmd == "headings":
            return report(headings=len(hs))
        probe_topics = lines_of(read_private(a.probe_topics, "probe-topics-sha256"))
        ddir = os.path.join(bk.W, "draft")
        if a.cmd == "draft":
            prompt = read_private(a.prompt, "prompt-sha256")
            need("{heading}" in prompt and "{count}" in prompt, "the prompt must hold {heading} and {count}")
            model = registered_model()
            if len(hs) < MIN_HEADINGS:
                return report(headings=len(hs), status="fewer than 3 headings: nothing drafted")
            bk.LEDGER = bk.Ledger(os.path.join(bk.W, "ledger.jsonl"), float(registered("max-usd")))
            calls, status = 0, "drafted"
            try:
                calls = draft(hs, prompt, file_sha(a.prompt), model, ddir)
            except bk.BudgetExceeded:
                status = "budget stop (15.6.3)"
            except bk.InfraError:
                status = "infrastructure error: resume asks the headings not yet answered"
            if status != "drafted":
                return report(headings=len(hs), calls=calls, status=status, spent_usd=round(bk.LEDGER.spent, 4))
            kept, drops = keep(saved_topics(hs, ddir, model, file_sha(a.prompt)), probe_topics)
            return report(headings=len(hs), calls=calls, kept=len(kept), dropped=drops,
                          spent_usd=round(bk.LEDGER.spent, 4))
        verdicts = json.loads(read_private(a.verdicts, "verdicts-sha256"))
        flagged = flagged_set(verdicts)
        lst = listing_of(verdicts, lines_of(read_private(a.added_titles, "added-titles-sha256")))
        template = read_private(a.template, "template-sha256")
        check_template(template)
        bk.write_json(os.path.join(bk.W, "template-lengths.json"), {       # 15.5.3: private, for the owner
            "template": len(fill(template, "")), "clue_4": len(fill(template, "一" * 4)),
            "clue_16": len(fill(template, "一" * 16))})
        status = "done"
        if a.cmd == "probe":
            path = os.path.join(bk.W, "probe.json")
            try:
                st = probe(probe_topics, template, lst, path)
            except (Halt, bk.InfraError) as e:
                st, status = bk.read_json(path), "stopped: " + (str(e) if isinstance(e, Halt) else type(e).__name__)
            return report(topics=len(probe_topics), searched=st["next"], network_searches=st["net"],
                          would_drop=sum(st["drops"].values()), dropped=st["drops"], zyjy_unlisted=st["zyjy_unlisted"],
                          status=status)
        kept, kdrops = keep(saved_topics(hs, ddir, registered_model(), registered("prompt-sha256").lower()),
                            probe_topics)
        surv, sdrops = survivors(kept, lst)
        path = os.path.join(bk.W, "walk.json")
        if a.max_searches > MAX_SEARCHES:       # 15.6.3: the owner's go on a higher cap is recorded in the addendum
            need(registered("max-searches") == str(a.max_searches), "--max-searches is not the addendum's max-searches")
        try:
            st = walk(order(surv, len(hs)), template, lst, path, a.max_searches)
            status = "pass" if len(st["passes"]) >= N_CONTROLS else "null: survivors exhausted (15.6.2)"
        except Halt as e:
            st = bk.read_json(path)
            status = "budget stop (15.6.3)" if str(e) == "budget" else "infrastructure stop: empty replies (15.4.4)"
        except bk.InfraError:
            st, status = bk.read_json(path), "infrastructure error: resume starts at the same candidate"
        return report(kept=len(kept), dropped=kdrops, survivors=len(surv), checks=sdrops, walked=st["next"],
                      walk_drops=st["drops"], zyjy_unlisted=st["zyjy_unlisted"], network_searches=st["net"],
                      controls=len(st["passes"]), status=status, label=certified_label(flagged))
    except Stop as e:
        sys.exit(f"stopped: {e}")


if __name__ == "__main__":
    main()
