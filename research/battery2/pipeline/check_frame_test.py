"""Checks of frame_test.py (CONTROLS-RULE.md 17.8.5) on invented texts: no network, no private file.
Usage: python3 -I check_frame_test.py [PIPELINE_DIR]
PIPELINE_DIR holds frame_test.py and what it imports; the default is this file's folder. Give a folder holding a
broken copy to see the checks fail. Exit status 1 if one fails."""
import contextlib
import importlib.util
import io
import json
import os
import random
import shutil
import subprocess
import sys
import tempfile

d = os.path.abspath(sys.argv[1] if len(sys.argv) > 1 else os.path.dirname(os.path.abspath(__file__)))
spec = importlib.util.spec_from_file_location("frame_test_under_test", os.path.join(d, "frame_test.py"))
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
ct, bk = m.ct, m.bk
TMP = tempfile.mkdtemp(prefix="frametest-")
GIT_ENV = {**os.environ, "GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_NOSYSTEM": "1"}
RNG = random.Random("frame-test-fixtures")


def cjk(n):
    """Invented text: random ideographs, plainly no real topic or clue."""
    return "".join(chr(RNG.randrange(0x4E00, 0x9FA0)) for _ in range(n))


LENGTHS = [4, 5, 6, 4, 5, 7, 8, 9, 7, 8, 10, 11, 12, 10, 11, 13, 14, 15, 16, 13]
TOPICS = [cjk(n) for n in LENGTHS]
TOPICS_TEXT = "\n".join(TOPICS) + "\n"
FRAMES = ["一篇2010年代刊于《周易研究》的易学期刊论文，讨论{topic}。",
          "一篇2010年代刊于《周易研究》之中的易学期刊论文，以{topic}为对象，加以讨论，梳理其材料来源与前后变化，"
          "并说明相关说法如何形成。",
          "一篇2010年代刊于《周易研究》的易学期刊论文，先辨析{topic}的几种说法，再比较各说的依据与得失，"
          "最后评估诸说在后世的价值。",
          "一篇2010年代见于《周易研究》的易学期刊论文，所考察者并非泛论，而是围绕{topic}展开的问题，"
          "文中再逐层追溯其来龙去脉。"]
PROMPTS = {"writer-prompt.txt": "Invented writer prompt.\nExamples:\n{examples}\n{rewrite}End.\n",
           "checker-prompt.txt": "Invented checker prompt.\n{frames}\nEnd.\n",
           "judge-prompt.txt": "Invented judge prompt.\n{questions}\nEnd.\n"}
INSTR = [{"path": "/home/x/.claude/rules/a.md", "type": "User", "content": "An invented standing rule."},
         {"path": "/home/x/.claude/rules/b.md", "type": "User", "content": "Another invented rule."}]
RULE_PATH = "research/battery2/pipeline/CONTROLS-RULE.md"
FIXED_C = "0123456789abcdef0123456789abcdef01234567"
# The golden draw for ids B2-g000..B2-g089, topics t00..t19 and FIXED_C, computed once by a separate five-line
# reimplementation of 17.2.2 (random.Random(seed).sample, shuffle, shuffle), not by frame_test.draw.
GOLD_FIRST = ["B2-g088", "B2-g049", "B2-g040", "B2-g031", "B2-g012", "B2-g000"]
GOLD_LAST = ["B2-g087", "B2-g080"]
GOLD_TOPICS = ["t03", "t14", "t10", "t00", "t18", "t11", "t08", "t01", "t09", "t15", "t19", "t02", "t07", "t17", "t12",
               "t13", "t04", "t06", "t05", "t16"]
GOLD_POS = [0, 1, 3, 4, 3, 0, 4, 4, 3, 1, 4, 2, 0, 0, 2, 1, 2, 1, 2, 3]
GOLD_UNDRAWN = ["B2-g002", "B2-g004", "B2-g014", "B2-g025", "B2-g047", "B2-g052", "B2-g055", "B2-g059", "B2-g061",
                "B2-g062"]


# ----------------------------------------------------------------------------- fixtures
def verdicts():
    out = {f"{y}/{i}": {"complete": True, "listing": [], "abstracts": []}
           for y in range(2010, 2020) for i in range(1, 7)}
    out["2013/2"] = {"complete": True, "listing": [["加以讨论之法"], ["甲于之中乙"], ["丙究之中丁"]],
                     "abstracts": ["本文梳理其源流。"]}
    return out


def item(i, clue=None, typ="article", lang="zh", venue="周易研究", year=2015, anchor="venue"):
    clue = clue or f"一篇2010年代《周易研究》上的易学期刊论文，考察{cjk(6)}。"
    return {"id": i, "stratum": {"type": typ, "language": lang}, "key": {"venue": venue, "year": year}, "clue": clue,
            "clue_writer": "opus", "clues_by_writer": {"opus": {"anchor": anchor, "clue": clue},
                                                       "sonnet": {"anchor": "author", "clue": "x"}}}


GOOD = [item(f"B2-g{i:03d}") for i in range(90)]
# 7 ids in two runs, each copy with its own clue; 2 of them meet the rule (as 17.2.1 counted)
REPEATS = [(item(f"B2-r{i}"), item(f"B2-r{i}")) if i < 2 else (item(f"B2-r{i}", anchor="author"),
                                                                 item(f"B2-r{i}", anchor="author")) for i in range(7)]
OFF = [item("B2-x1", typ="book"), item("B2-x2", lang="en"), item("B2-x3", venue="周易研究所刊"), item("B2-x4", year=2009),
       item("B2-x5", year=2020), item("B2-x6", anchor="author"), item("B2-x7", clue="一篇2010年代的易学期刊论文，考察某事。"),
       item("B2-x8", clue="一篇《周易研究》上的易学期刊论文，考察某事。")]


def item_files(base, good=GOOD):
    files = [[] for _ in range(4)]
    for n, r in enumerate(good + OFF):
        files[n % 4].append(r)
    for a, b in REPEATS:
        files[0].append(a)
        files[1].append(b)
    paths = []
    for n, rows in enumerate(files, 1):
        p = os.path.join(base, f"items-{n}.jsonl")
        with open(p, "w", encoding="utf-8") as f:
            f.write("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows))
        paths.append(p)
    return paths


PROSE = "## 17. Frame test\n\nThe label is written thus:\n- `probe-topics-sha256`: `" + "ab" * 32 + "`\n"


def rule_text(lines):
    s16 = ("## 16. Addendum\n\n" + "".join(f"- `{k}`: `{v}`\n" for k, v in lines) + "\n") if lines else ""
    return "# Rule\n\n## 15. Controls\n\nText.\n\n" + s16 + PROSE


def git(*args):
    return subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@example.org", *args], check=True,
                          capture_output=True, text=True, env=GIT_ENV).stdout


def repo(values):
    """A repository whose first-parent commits hold the rule file with these topics-record values (None: no section
    16, but prose in section 17 that names the label); origin/main points at the last."""
    root = tempfile.mkdtemp(dir=TMP)
    git("init", "-q", root)
    os.makedirs(os.path.join(root, os.path.dirname(RULE_PATH)))
    for n, v in enumerate(values):
        with open(os.path.join(root, RULE_PATH), "w", encoding="utf-8") as f:
            f.write(rule_text([("probe-topics-sha256", v)] if v else []) + f"\nRevision {n}.\n")
        git("-C", root, "add", "-A")
        git("-C", root, "commit", "-q", "-m", f"r{n}")
    git("-C", root, "update-ref", "refs/remotes/origin/main", "HEAD")
    return root, git("-C", root, "rev-list", "--first-parent", "--reverse", "HEAD").split()


class C:
    pass


def new(topics_text=TOPICS_TEXT, prompts=PROMPTS, good=GOOD):
    c = C()
    c.base = tempfile.mkdtemp(dir=TMP)
    c.W, c.T = os.path.join(c.base, "w"), os.path.join(c.base, "t")
    os.makedirs(c.W)
    os.makedirs(c.T)
    with open(os.path.join(c.W, "test-topics.txt"), "wb") as f:
        f.write(topics_text.encode("utf-8") if isinstance(topics_text, str) else topics_text)
    for name, text in prompts.items():
        write(os.path.join(c.W, name), text)
    c.V = os.path.join(c.base, "verdicts.json")
    write(c.V, json.dumps(verdicts(), ensure_ascii=False))
    c.items = item_files(c.base, good)
    c.rule = os.path.join(c.base, "CONTROLS-RULE.md")
    c.labels = []
    ct.RULE = c.rule
    write(c.rule, rule_text([]))
    return c


def write(path, text):
    with open(path, "w", encoding="utf-8", newline="") as f:
        f.write(text)


def read(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


def set_rule(c, lines, replace=()):
    c.labels = [(k, v) for k, v in c.labels if k not in replace] + list(lines)
    write(c.rule, rule_text(c.labels))
    ct.RULE = c.rule


def cli(*args):
    out = io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(io.StringIO()):
        try:
            code = m.main([str(x) for x in args])
        except SystemExit as e:
            code = e.code
    return code, out.getvalue()


def parsed(out):
    return dict(ln.split(": ", 1) for ln in out.splitlines() if ": " in ln)


def stops(res, words=""):
    code, out = res
    return code == 2 and out.startswith("stop: ") and words in out


def ok(res):
    if res[0] != 0:
        raise AssertionError(f"step failed: {res}")
    return res[1]


IDS = [0]


def transcript(c, prompt, answer, model="claude-opus-5-5", effort="medium", tools=(), instr=INSTR, handback=True,
               drop=(), text=None, handbacks=None):
    IDS[0] += 1
    aid = f"a{IDS[0]:05d}"
    user = {"type": "user", "message": {"role": "user", "content": prompt}}
    rows = [user, {"type": "user", "isMeta": True, "message": {"role": "user", "content": "a reminder"}}]
    if instr is not None:
        rows.append({"type": "attachment", "attachment": {"type": "instructions", "files": instr}})
    blocks = [{"type": "tool_use", "name": t, "input": {}} for t in tools]
    if text is not None:
        blocks.append({"type": "text", "text": text})
    rows.append({"type": "assistant", "effort": effort, "perTurnEffort": effort,
                 "message": {"model": model, "content": blocks + [{"type": "thinking", "thinking": ""}]}})
    for msg in (handbacks if handbacks is not None else [answer] if handback else []):
        rows.append({"type": "assistant", "effort": effort, "perTurnEffort": effort,
                     "message": {"model": model, "content": [{"type": "tool_use", "name": "SubagentHandback",
                                                              "input": {} if msg is None else {"message": msg}}]}})
    for field in drop:
        if field == "user":
            rows = [r for r in rows if r.get("type") != "user"]
        elif field == "instructions":
            rows = [r for r in rows if r.get("type") != "attachment"]
        else:
            for r in rows:
                if r.get("type") == "assistant":
                    (r["message"] if field == "model" else r).pop(field, None)
    write(os.path.join(c.T, f"agent-{aid}.jsonl"), "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows))
    return aid


def dorun(c, args, prompt, answer, reply=None, **kw):
    aid = transcript(c, prompt, answer, **kw)
    rf = os.path.join(c.base, f"reply-{aid}.txt")
    write(rf, answer if reply is None else reply)
    return cli(*args, "--workdir", c.W, "--agent-id", aid, "--reply-file", rf, "--transcripts", c.T)


def js(obj):
    return json.dumps(obj, ensure_ascii=False)


def checker_answer(frames, verdict=lambda k: "passes"):
    return js([{"frame": k, "verdict": verdict(k), "reason": "invented reason", "gloss": "An invented gloss."}
               for k in frames])


# ----------------------------------------------------------------------------- the stages
def st_topics(c, values=None):
    out = parsed(ok(cli("topics", "--workdir", c.W, "--verdicts", c.V)))
    set_rule(c, [(k, out[k]) for k in m.TOPICS_RECORD])
    x = out["probe-topics-sha256"]
    c.repo, c.shas = repo([None, x, x] if values is None else [v if v != "X" else x for v in values])


def st_pool(c):
    c.pool = parsed(ok(cli("pool", "--workdir", c.W, "--items", *c.items, "--verdicts", c.V, "--repo", c.repo)))


def st_dry(c, answers=None):
    ok(cli("dry-prompts", "--workdir", c.W))
    answers = answers or {"writer": js(["甲", "乙", "丙", "丁"]), "checker": checker_answer(range(4)),
                          "judge": js({"pick": 2, "reason": "invented"})}
    for role in m.ROLES:
        ok(dorun(c, ["dry-record", "--role", role], read(os.path.join(c.W, m.DRY_FILES[role])), answers[role]))
    ok(cli("dry-score", "--workdir", c.W, "--transcripts", c.T))


def writer(c, request, answer, **kw):
    return dorun(c, ["frames", "add", "--request", request], read(os.path.join(c.W, request)), answer, **kw)


def checker(c, request, answer, **kw):
    return dorun(c, ["frames", "verdicts", "--request", request], read(os.path.join(c.W, request)), answer, **kw)


def lists(c):
    return ok(cli("frames", "lists", "--workdir", c.W))


def finish(c):
    return cli("frames", "finish", "--workdir", c.W, "--transcripts", c.T)


def st_frames(c, frames=FRAMES):
    ok(writer(c, "writer-request.txt", js(frames)))
    lists(c)
    ok(checker(c, "checker-request-1.txt", checker_answer(range(4))))
    c.frames = parsed(ok(finish(c)))


def st_record2(c):
    lines = [("seed-commit", c.pool["seed-commit"]), ("drawn-sha256", c.pool["drawn-sha256"])]
    lines += [(f"pool-file-{n}-sha256", c.pool[f"pool-file-{n}-sha256"]) for n in range(1, 5)]
    lines += [("pool-count", "90")] + [(k, v) for k, v in c.frames.items() if k.startswith("frame-")]
    set_rule(c, lines + [("judge-model", "claude-opus-5-5"), ("judge-effort", "medium"), ("threshold", "7")])


def pos(c):
    return [r["pos"] for r in json.loads(read(os.path.join(c.W, "rounds.json")))]


def prompts(c, k):
    return [p["prompt"] for p in json.loads(read(os.path.join(c.W, f"prompts-frame{k}.json")))]


def judge(c, k, r, pick, attempt=1, run=1, **kw):
    answer = kw.pop("answer", None) or js({"pick": pick, "reason": "invented"})
    return dorun(c, ["run", "--frame", k, "--round", r, "--attempt", attempt, "--run", run], prompts(c, k)[r], answer,
                 **kw)


def pick_for(c, r, hit):
    p = pos(c)[r]
    return p + 1 if hit else (p + 1) % 5 + 1


def score(c, k, run=1, *extra):
    return cli("score", "--workdir", c.W, "--frame", k, "--run", run, "--transcripts", c.T, *extra)


def st_frame(c, k, hits, run=1, score_it=True):
    ok(cli("rounds", "--workdir", c.W, "--frame", k))
    for r in range(20):
        ok(judge(c, k, r, pick_for(c, r, r < hits), run=run))
    return parsed(ok(score(c, k, run))) if score_it else None


def build(upto, **kw):
    c = new(**{k: v for k, v in kw.items() if k in ("topics_text", "prompts", "good")})
    for name, step in (("topics", lambda: st_topics(c, kw.get("values"))), ("pool", lambda: st_pool(c)),
                       ("dry", lambda: st_dry(c)), ("frames", lambda: st_frames(c, kw.get("frames", FRAMES))),
                       ("record2", lambda: st_record2(c)), ("frame0", lambda: st_frame(c, 0, kw.get("h0", 10)))):
        step()
        if name == upto:
            return c
    return c


def raises(fn):
    try:
        fn()
    except ct.Stop:
        return True
    return False


# ----------------------------------------------------------------------------- 17.3 topics
def topics_with(lines):
    return "\n".join(lines) + "\n"


def topics_case(text):
    c = new(topics_text=text)
    return cli("topics", "--workdir", c.W, "--verdicts", c.V)


def case_topics_ok():
    c = new()
    out = parsed(ok(cli("topics", "--workdir", c.W, "--verdicts", c.V)))
    return (out["probe-topics-sha256"] == ct.file_sha(os.path.join(c.W, "test-topics.txt"))
            and out["verdicts-sha256"] == ct.file_sha(c.V) and out["norm-mode"] == ct.norm_mode()
            and all(out[f"topics {lo}-{hi}"] == "5" for lo, hi in m.BANDS)
            and sorted(os.listdir(c.W)) == sorted(["test-topics.txt", *PROMPTS]))


def case_topics_form():
    bad = [TOPICS_TEXT[:-1], TOPICS_TEXT.replace("\n", "\r\n"), TOPICS_TEXT + "\n", " " + TOPICS_TEXT,
           TOPICS_TEXT.replace("\n", " \n", 1), "﻿" + TOPICS_TEXT, "\n".join(TOPICS[:10]) + "\n\n" +
           "\n".join(TOPICS[10:]) + "\n", TOPICS_TEXT.encode("utf-16")]
    return all(stops(topics_case(t), "canonical") for t in bad)


def case_topics_count():
    return stops(topics_case(topics_with(TOPICS[:19])), "not 20")


def case_topics_pattern():
    return stops(topics_case(topics_with(["A" + TOPICS[0][1:]] + TOPICS[1:])), "4-16 CJK")


def case_topics_bands():
    return stops(topics_case(topics_with(TOPICS[:5] + [cjk(6)] + TOPICS[6:])), "band")


def case_topics_norm_duplicate():
    """Two topics that differ only in a traditional and a simplified character are one topic."""
    tail = TOPICS[3][1:]
    return stops(topics_case(topics_with(TOPICS[:3] + ["國" + tail, "国" + tail] + TOPICS[5:])),
                 "equal after norm")


def case_topics_survivors():
    return stops(topics_case(topics_with(["以讨论" + cjk(1)] + TOPICS[1:])), "survive")


def case_topics_prompts():
    c = new(prompts={**PROMPTS, "checker-prompt.txt": "{frames} {frames}"})
    c2 = new(prompts={k: v for k, v in PROMPTS.items() if k != "judge-prompt.txt"})
    c3 = new(prompts={**PROMPTS, "writer-prompt.txt": "{examples} only"})
    return all(stops(cli("topics", "--workdir", x.W, "--verdicts", x.V)) for x in (c, c2, c3))


# ----------------------------------------------------------------------------- section 16
def case_labels():
    c = build("topics")
    n = parsed(ok(cli("labels", "--workdir", c.W)))["labels"] == "6"
    set_rule(c, [("norm-mode", ct.norm_mode())])
    return n and stops(cli("labels", "--workdir", c.W), "stands twice") and stops(
        cli("pool", "--workdir", c.W, "--items", *c.items, "--verdicts", c.V, "--repo", c.repo), "stands twice")


# ----------------------------------------------------------------------------- 17.2 pool and draw
def pool_cmd(c):
    return cli("pool", "--workdir", c.W, "--items", *c.items, "--verdicts", c.V, "--repo", c.repo)


def case_pool_ok():
    c = build("pool")
    w = c.W
    pool = json.loads(read(os.path.join(w, "pool.json")))
    drawn = read(os.path.join(w, "drawn-ids.txt"))
    undrawn = json.loads(read(os.path.join(w, "undrawn.json")))
    rounds = json.loads(read(os.path.join(w, "rounds.json")))
    req = read(os.path.join(w, "writer-request.txt"))
    ids = [p["id"] for p in pool]
    exp = m.draw(ids, TOPICS, c.shas[1])
    return (c.pool["seed-commit"] == c.shas[1] and c.pool["pool-count"] == "90" and ids == sorted(g["id"] for g in GOOD)
            and drawn == "".join(i + "\n" for i in exp[0]) and c.pool["drawn-sha256"] == ct.file_sha(
                os.path.join(w, "drawn-ids.txt"))
            and [u["id"] for u in undrawn] == sorted(set(ids) - set(exp[0]))
            and [(r["topic"], r["ids"], r["pos"]) for r in rounds] == [(exp[1][r], exp[0][4 * r:4 * r + 4], exp[2][r])
                                                                         for r in range(20)]
            and all(sorted(exp[2]).count(p) == 4 for p in range(5))
            and req == PROMPTS["writer-prompt.txt"].replace("{examples}", "\n".join(
                f"{n}. {u['clue']}" for n, u in enumerate(undrawn, 1))).replace("{rewrite}", "")
            and all(c.pool[f"pool-file-{n}-sha256"] == ct.file_sha(p) for n, p in enumerate(c.items, 1)))


def case_golden():
    drawn, topics, p = m.draw([f"B2-g{i:03d}" for i in range(90)], [f"t{i:02d}" for i in range(20)], FIXED_C)
    return (drawn[:6] == GOLD_FIRST and drawn[-2:] == GOLD_LAST and len(set(drawn)) == 80 and topics == GOLD_TOPICS
            and p == GOLD_POS and sorted(set(f"B2-g{i:03d}" for i in range(90)) - set(drawn)) == GOLD_UNDRAWN)


def case_pool_count():
    more = build("topics", good=GOOD + [item("B2-g090")])
    less = build("topics", good=GOOD[:-1])
    return stops(pool_cmd(more), "91") and stops(pool_cmd(less), "89")


def case_pool_record():
    out = []
    for label in ("verdicts-sha256", "norm-mode", "writer-prompt-sha256", "probe-topics-sha256"):
        c = build("topics")
        set_rule(c, [(label, "0" * 64)], replace=(label,))
        out.append(stops(pool_cmd(c), label))
    return all(out)


def case_seed_later_commit_differs():
    return stops(pool_cmd(build("topics", values=[None, "X", "X", "f" * 64])), "later commit")


def case_seed_file_differs():
    c = build("topics")
    set_rule(c, [("probe-topics-sha256", "e" * 64)], replace=("probe-topics-sha256",))
    git("-C", c.repo, "status")
    return stops(pool_cmd(c), "probe-topics-sha256")   # the record no longer matches the file either


def case_seed_line_in_file_checked():
    """The rule file as it stands must hold the seed line's value: a later value there stops the draw."""
    c = build("topics")
    return raises(lambda: (setattr(ct, "RULE", c.rule), write(c.rule, rule_text(
        [(k, ("d" * 64 if k == "probe-topics-sha256" else v)) for k, v in c.labels])), m.seed_commit(c.repo)))


def case_seed_none():
    return stops(pool_cmd(build("topics", values=[None, None])), "no commit")


def case_seed_shallow():
    c = build("topics", values=[None, None, "X", "X"])
    clone = os.path.join(tempfile.mkdtemp(dir=TMP), "shallow")
    git("clone", "-q", "--depth", "1", "file://" + c.repo, clone)
    c.repo = clone
    return stops(pool_cmd(c), "shallow")


def case_seed_prose_not_matched():
    """A commit whose only line of the label's form is prose in section 17 is not the seed commit."""
    c = build("topics")
    return m.seed_commit(c.repo) == c.shas[1]


# ----------------------------------------------------------------------------- 17.5.5 dry runs
def case_dry_ok():
    c = build("dry")
    base = json.loads(read(os.path.join(c.W, "dry-instructions.json")))
    texts = {r: read(os.path.join(c.W, m.DRY_FILES[r])) for r in m.ROLES}
    return (base == sorted([f["path"], m.sha_text(f["content"])] for f in INSTR)
            and all(s not in texts["writer"] + texts["judge"] for s in ("{examples}", "{rewrite}", "{questions}"))
            and ct.fill(m.DRY_FRAMES[0], m.DRY_TOPIC) in texts["judge"] and "Frame 3: " in texts["checker"])


def case_dry_invalid():
    c = build("pool")
    ok(cli("dry-prompts", "--workdir", c.W))
    answers = {"writer": js(["甲", "乙", "丙", "丁"]), "checker": checker_answer(range(4)),
               "judge": js({"pick": 2, "reason": "x"})}
    for role in m.ROLES:
        ok(dorun(c, ["dry-record", "--role", role], read(os.path.join(c.W, m.DRY_FILES[role])), answers[role]))
    void = dorun(c, ["dry-record", "--role", "judge"], read(os.path.join(c.W, m.DRY_FILES["judge"])),
                 answers["judge"], tools=("Bash",))
    return void[0] == 3 and stops(cli("dry-score", "--workdir", c.W, "--transcripts", c.T), "dry run is invalid") \
        and not os.path.exists(os.path.join(c.W, "dry-instructions.json"))


def case_dry_instructions_differ():
    c = build("pool")
    ok(cli("dry-prompts", "--workdir", c.W))
    answers = {"writer": js(["甲", "乙", "丙", "丁"]), "checker": checker_answer(range(4)),
               "judge": js({"pick": 2, "reason": "x"})}
    for role in m.ROLES:
        ok(dorun(c, ["dry-record", "--role", role], read(os.path.join(c.W, m.DRY_FILES[role])), answers[role],
                 instr=INSTR[:1] if role == "judge" else INSTR))
    return stops(cli("dry-score", "--workdir", c.W, "--transcripts", c.T), "dry run is invalid")


# ----------------------------------------------------------------------------- 17.4 frames
def pad(frame, n):
    return frame[:-1] + "乙" * n + "。"


def case_frame_code_good():
    lens = [len(ct.fill(f, "")) for f in FRAMES]
    return (all(m.frame_problem(k, f) is None for k, f in enumerate(FRAMES))
            and m.frame_problem(0, pad(FRAMES[0], 40 - lens[0])) is None
            and m.frame_problem(1, pad(FRAMES[1], 56 - lens[1])) is None
            and m.frame_problem(1, pad(FRAMES[1], 72 - lens[1])) is None)


def case_frame_code_bad():
    lens = [len(ct.fill(f, "")) for f in FRAMES]
    f1 = FRAMES[1]
    bad = [(0, pad(FRAMES[0], 41 - lens[0]), "at most 40"), (1, f1.replace("加以讨论，", "").replace("并说明", ""), "56 to 72"),
           (1, pad(f1, 73 - lens[1]), "56 to 72"), (1, f1[:-1] + "乙", "。"), (1, f1.replace("易学", "乙乙"), "期刊论文"),
           (1, f1.replace("乙", "").replace("加以讨论", "加以第3论"), "digit"),
           (1, f1.replace("加以讨论", "加以〈论〉"), "title mark"), (1, f1.replace("加以讨论", "加以ABCD"), "Latin"),
           (1, f1.replace("加以讨论", "加以ＡＢ论"), "Latin"), (1, f1.replace("梳理其", "{topic}"), "once"),
           (1, f1.replace("{topic}", "乙乙"), "once"), (0, FRAMES[0].replace("期刊论文", "文章"), "期刊论文")]
    got = [(m.frame_problem(k, t) or "") for k, t, _ in bad]
    return all(w in g for g, (_, _, w) in zip(got, bad))


def case_title_marks_round_venue_allowed():
    return m.frame_problem(1, FRAMES[1]) is None and "《" in FRAMES[1] and "《" not in m.rest(FRAMES[1])


def frames_until_checker(frames=FRAMES):
    c = build("dry")
    ok(writer(c, "writer-request.txt", js(frames)))
    return c


def case_grams_listed():
    c = frames_until_checker()
    lists(c)
    req = read(os.path.join(c.W, "checker-request-1.txt"))
    block1 = req.split("Frame 1: ")[1].split("Frame 2: ")[0]
    return ("以讨论: titles 1, abstracts 0" in block1 and "梳理其: titles 0, abstracts 1" in block1
            and "于之中" not in req and "究之中" not in req and all(f"Frame {k}: {FRAMES[k]}" in req for k in range(4)))


def case_code_fail_rewrite():
    c = frames_until_checker([FRAMES[0], BAD1, FRAMES[2], FRAMES[3]])
    out = parsed(lists(c))
    req = read(os.path.join(c.W, "checker-request-1.txt"))
    retry = read(os.path.join(c.W, "writer-retry-request-1.txt"))
    return (out["frames for the checker"] == "3" and out["frames for a rewrite"] == "1" and "Frame 1: " not in req
            and m.REWRITE in retry and "- frame 1: the fixed text must be 56 to 72 characters" in retry
            and "{rewrite}" not in retry)


def flow(writer_rounds, checker_rounds, strike=()):
    """Runs the frames: writer_rounds[i] maps frame -> text for writer request i; checker_rounds[i] maps frame ->
    verdict for checker request i (absent frames pass). Returns (context, finish result)."""
    c = build("dry")
    ok(writer(c, "writer-request.txt", js([writer_rounds[0][k] for k in range(4)])))
    wi = ci = 1
    for _ in range(6):
        lists(c)
        events = [json.loads(x) for x in read(os.path.join(c.W, "frames-log.jsonl")).splitlines()]
        new = {e["kind"]: e for e in events if e["event"] == "request" and e["name"] in (
            f"checker-request-{ci}.txt", f"writer-retry-request-{wi}.txt")}
        if "checker" in new:
            verdicts_i = checker_rounds[ci - 1] if ci - 1 < len(checker_rounds) else {}
            ok(checker(c, new["checker"]["name"], checker_answer(new["checker"]["frames"],
                                                                  lambda k: verdicts_i.get(k, "passes"))))
            ci += 1
        if "writer" in new:
            ok(writer(c, new["writer"]["name"], js([{"frame": k, "text": writer_rounds[wi][k]}
                                                    for k in new["writer"]["frames"]])))
            wi += 1
        if not new:
            break
    for k in strike:
        ok(cli("frames", "strike", "--workdir", c.W, "--frame", k))
    return c, finish(c)


BAD1 = FRAMES[1].replace("加以讨论，", "").replace("并说明", "")
ALL = dict(enumerate(FRAMES))


def case_second_code_failure_drops():
    c, res = flow([{**ALL, 1: BAD1}, {1: BAD1}], [])
    out = parsed(ok(res))
    return out["frames dropped-code"] == "1" and "frame-1-sha256" not in out and out["frames kept"] == "3"


def case_code_failure_then_fixed_kept():
    c, res = flow([{**ALL, 1: BAD1}, {1: FRAMES[1]}], [])
    out = parsed(ok(res))
    return out["frames kept"] == "4" and read(os.path.join(c.W, "frame-1.txt")) == FRAMES[1]


def case_flag_then_rewrite_kept():
    c, res = flow([ALL, {2: pad(FRAMES[2], 2)}], [{2: "flagged"}])
    out = parsed(ok(res))
    return out["frames kept"] == "4" and read(os.path.join(c.W, "frame-2.txt")) == pad(FRAMES[2], 2)


def case_flag_twice_drops():
    c, res = flow([ALL, {2: pad(FRAMES[2], 2)}], [{2: "flagged"}, {2: "flagged"}])
    out = parsed(ok(res))
    return out["frames dropped-checker"] == "1" and not os.path.exists(os.path.join(c.W, "frame-2.txt"))


def case_code_rewrite_then_flagged_drops():
    c, res = flow([{**ALL, 1: BAD1}, {1: FRAMES[1]}], [{}, {1: "flagged"}])
    out = parsed(ok(res))
    return out["frames dropped-checker"] == "1" and "frame-1-sha256" not in out


def case_struck_not_kept():
    c, res = flow([ALL], [], strike=(3,))
    out = parsed(ok(res))
    return out["frames struck"] == "1" and "frame-3-sha256" not in out and json.loads(
        read(os.path.join(c.W, "frames-kept.json")))["kept"] == [0, 1, 2]


def case_null_frame0():
    _, res = flow([ALL], [], strike=(0,))
    return res == (2, "null: frame 0 not kept\n")


def case_null_no_longer():
    c, res = flow([ALL], [], strike=(1, 2, 3))
    return res == (2, "null: no longer frame kept\n") and stops(cli("rounds", "--workdir", c.W, "--frame", 0))


def case_finish_waits():
    c = frames_until_checker()
    lists(c)
    return stops(finish(c), "waiting")


def case_glosses_private():
    c = frames_until_checker()
    lists(c)
    res = checker(c, "checker-request-1.txt", checker_answer(range(4)))
    g = json.loads(read(os.path.join(c.W, "glosses.json")))
    return res[0] == 0 and "gloss" not in res[1].lower() and g["0"][0]["gloss"] == "An invented gloss."


def case_writer_void_once_then_valid():
    c = build("dry")
    first = writer(c, "writer-request.txt", js(FRAMES), tools=("Read",))
    second = writer(c, "writer-request.txt", js(FRAMES))
    third = writer(c, "writer-request.txt", js(FRAMES))
    return first[0] == 3 and first[1].startswith("void: ") and second[0] == 0 and stops(third)


def case_writer_void_twice_stops():
    c = build("dry")
    first = writer(c, "writer-request.txt", js(FRAMES), tools=("Read",))
    second = writer(c, "writer-request.txt", js(FRAMES), tools=("Read",))
    third = writer(c, "writer-request.txt", js(FRAMES))
    return first[0] == 3 and stops(second, "two void runs") and stops(third, "two void runs")


def case_checker_void_twice_stops():
    c = frames_until_checker()
    lists(c)
    first = checker(c, "checker-request-1.txt", checker_answer(range(4)), tools=("Grep",))
    second = checker(c, "checker-request-1.txt", checker_answer(range(4)), tools=("Grep",))
    return first[0] == 3 and stops(second, "two void runs")


def case_later_writer_reply_shape():
    c = frames_until_checker([FRAMES[0], BAD1, FRAMES[2], FRAMES[3]])
    lists(c)
    extra = writer(c, "writer-retry-request-1.txt", js([{"frame": 1, "text": FRAMES[1]}, {"frame": 2, "text": "x"}]))
    strings = writer(c, "writer-retry-request-1.txt", js([FRAMES[1]]))
    return extra[0] == 3 and stops(strings, "two void runs")


def case_finish_accounting_writer():
    c = frames_until_checker()
    lists(c)
    ok(checker(c, "checker-request-1.txt", checker_answer(range(4))))
    transcript(c, read(os.path.join(c.W, "writer-request.txt")), js(FRAMES))         # a writer run left out
    return stops(finish(c), "not in the ledger")


def case_finish_accounting_checker():
    c = frames_until_checker()
    lists(c)
    ok(checker(c, "checker-request-1.txt", checker_answer(range(4))))
    transcript(c, read(os.path.join(c.W, "checker-request-1.txt")), checker_answer(range(4)))
    return stops(finish(c), "not in the ledger")


def case_finish_missing_transcript():
    c = frames_until_checker()
    lists(c)
    res = checker(c, "checker-request-1.txt", checker_answer(range(4)))
    aid = json.loads(read(os.path.join(c.W, "ledger.jsonl")).splitlines()[-1])["agent_id"]
    os.remove(os.path.join(c.T, f"agent-{aid}.jsonl"))
    return res[0] == 0 and stops(finish(c), "no transcript")


def case_finish_first_message_compared():
    c = build("dry")
    first = writer(c, "writer-request.txt", js(FRAMES), **{})
    ledger = os.path.join(c.W, "ledger.jsonl")
    aid = json.loads(read(ledger).splitlines()[-1])["agent_id"]
    lists(c)
    ok(checker(c, "checker-request-1.txt", checker_answer(range(4))))
    path = os.path.join(c.T, f"agent-{aid}.jsonl")
    rows = [json.loads(x) for x in read(path).splitlines()]
    rows[0]["message"]["content"] += " changed after the review"
    write(path, "".join(js(r) + "\n" for r in rows))
    return first[0] == 0 and stops(finish(c))


def case_baseline_fixed_after_real_runs():
    c = frames_until_checker()
    return stops(cli("dry-score", "--workdir", c.W, "--transcripts", c.T), "baseline is fixed")


def case_agent_recorded_once():
    c = frames_until_checker()
    lists(c)
    aid = json.loads(read(os.path.join(c.W, "ledger.jsonl")).splitlines()[-1])["agent_id"]
    rf = os.path.join(c.base, "reply-again.txt")
    write(rf, js(FRAMES))
    return stops(cli("frames", "verdicts", "--request", "checker-request-1.txt", "--workdir", c.W, "--agent-id", aid,
                     "--reply-file", rf, "--transcripts", c.T), "already in the ledger")


def case_strike_after_finish_refused():
    c, res = flow([ALL], [])
    return res[0] == 0 and stops(cli("frames", "strike", "--workdir", c.W, "--frame", 2))


# ----------------------------------------------------------------------------- 17.5.3 runs and void rules
RC = {}


def record_ctx():
    """One context at the record of 17.8.2 with frame 0's prompts written, shared by the run cases: each case uses
    rounds of its own."""
    if "c" not in RC:
        c = build("record2")
        ok(cli("rounds", "--workdir", c.W, "--frame", 0))
        RC["c"], RC["next"] = c, 0
    ct.RULE = RC["c"].rule
    RC["next"] += 1
    if RC["next"] >= 20:
        RC.clear()
        return record_ctx()
    return RC["c"], RC["next"] - 1


def case_valid_run():
    c, r = record_ctx()
    res = judge(c, 0, r, 3)
    return res == (0, "valid pick 3\n")


def case_void_picks():
    out = []
    for answer in ('{"pick": 0, "reason": "x"}', '{"pick": 6, "reason": "x"}', '{"pick": "3", "reason": "x"}',
                   '{"pick": true, "reason": "x"}', '{"pick": 2.0, "reason": "x"}', '{"pick": 2}',
                   '{"pick": 2, "reason": "x", "extra": 1}', '{"pick": 2, "reason": 5}', '[2, "x"]'):
        c, r = record_ctx()
        out.append(judge(c, 0, r, 0, answer=answer)[0] == 3)
    return all(out)


def case_void_prose():
    out = []
    for answer in ('Pick: {"pick": 2, "reason": "x"}', '```json\n{"pick": 2, "reason": "x"}\n```',
                   '{"pick": 2, "reason": "x"} done'):
        c, r = record_ctx()
        out.append(judge(c, 0, r, 0, answer=answer)[0] == 3)
    c, r = record_ctx()
    return all(out) and judge(c, 0, r, 0, answer=' {"pick": 2, "reason": "x"}\n')[0] == 0


def case_void_tool_judge():
    c, r = record_ctx()
    return judge(c, 0, r, 2, tools=("ToolSearch",))[0] == 3


def case_void_tool_writer_checker():
    c = build("dry")
    w = writer(c, "writer-request.txt", js(FRAMES), tools=("Bash",))
    c2 = frames_until_checker()
    lists(c2)
    k = checker(c2, "checker-request-1.txt", checker_answer(range(4)), tools=("WebFetch",))
    return w[0] == 3 and k[0] == 3


def case_void_model_effort_message():
    out = []
    for kw in ({"model": "claude-haiku-5-5"}, {"effort": "high"}, {"effort": "low"}):
        c, r = record_ctx()
        out.append(judge(c, 0, r, 2, **kw)[0] == 3)
    c, r = record_ctx()
    aid = transcript(c, prompts(c, 0)[r] + " ", js({"pick": 2, "reason": "x"}))
    rf = os.path.join(c.base, "reply-msg.txt")
    write(rf, js({"pick": 2, "reason": "x"}))
    res = cli("run", "--workdir", c.W, "--frame", 0, "--round", r, "--attempt", 1, "--run", 1, "--agent-id", aid,
              "--reply-file", rf, "--transcripts", c.T)
    return all(out) and res[0] == 3


def case_void_no_handback():
    c, r = record_ctx()
    a = judge(c, 0, r, 2, handback=False)
    c, r = record_ctx()
    b = judge(c, 0, r, 2, handback=False, text=js({"pick": 2, "reason": "x"}))
    c, r = record_ctx()
    e = judge(c, 0, r, 2, handbacks=[None])
    return a[0] == 3 and b[0] == 3 and e[0] == 3


def case_last_handback_counts():
    good, bad = js({"pick": 2, "reason": "x"}), "not json"
    c, r = record_ctx()
    a = judge(c, 0, r, 2, answer=bad, handbacks=[good, bad])
    c, r = record_ctx()
    b = judge(c, 0, r, 2, answer=good, handbacks=[bad, good])
    c, r = record_ctx()
    t = judge(c, 0, r, 2, answer=bad, text=good)          # text outside the hand-back is not the answer
    return a[0] == 3 and b == (0, "valid pick 2\n") and t[0] == 3


def case_reply_mismatch_stops():
    c, r = record_ctx()
    return stops(judge(c, 0, r, 2, reply=js({"pick": 3, "reason": "x"})), "differs")


def case_answer_from_transcript_not_ledger():
    c, r = record_ctx()
    return judge(c, 0, r, 2, handback=False, reply=js({"pick": 2, "reason": "x"}))[0] == 3


def case_missing_field_stops():
    out = []
    for field in ("effort", "model", "instructions", "user"):
        c, r = record_ctx()
        out.append(stops(judge(c, 0, r, 2, drop=(field,)), "transcript lacks"))
    return all(out)


def case_instructions_differ_stop():
    c, r = record_ctx()
    return stops(judge(c, 0, r, 2, instr=INSTR + [{"path": "/repo/AGENTS.md", "type": "Project", "content": "x"}]),
                 "instruction files differ")


def case_attempts():
    c, r = record_ctx()
    a2_first = judge(c, 0, r, 2, attempt=2)
    v = judge(c, 0, r, 2, tools=("Bash",))
    a2 = judge(c, 0, r, 2, attempt=2)
    a2_again = judge(c, 0, r, 2, attempt=2)
    a1_again = judge(c, 0, r, 2)
    c, r2 = record_ctx()
    ok(judge(c, 0, r2, 2))
    after_valid = judge(c, 0, r2, 2, attempt=2)
    a3 = judge(c, 0, r, 2, attempt=3)
    return (stops(a2_first, "attempt 2 only") and v[0] == 3 and a2[0] == 0 and stops(a2_again, "already recorded")
            and stops(a1_again, "already recorded") and stops(after_valid, "attempt 2 only") and stops(a3))


def case_rerun_needs_script_stop():
    """A refused command is not a stop the script found; a run whose transcript lacks a field is."""
    c = build("record2")
    ok(cli("rounds", "--workdir", c.W, "--frame", 0))
    refused = judge(c, 0, 0, 2, attempt=2)
    before = judge(c, 0, 0, 2, run=2)
    found = judge(c, 0, 0, 2, drop=("effort",))
    after = judge(c, 0, 0, 2, run=2)
    return stops(refused) and stops(before, "only after a stop") and stops(found, "lacks") and after[0] == 0


# ----------------------------------------------------------------------------- 17.6, 17.7 scoring and order
def scored(h0=None, hits=None, voids=(), doubles=(), k=0, extra_rounds=()):
    """A context at record2 with frame k's 20 rounds run: rounds in voids have a void attempt 1 and a valid attempt
    2; rounds in doubles have both void; the rest valid, hits on the rounds in hits."""
    c = build("record2") if k == 0 else build("frame0", h0=h0)
    ok(cli("rounds", "--workdir", c.W, "--frame", k))
    for r in range(20):
        hit = r in hits
        if r in voids or r in doubles:
            assert judge(c, k, r, 1, tools=("Bash",))[0] == 3
            if r in doubles:
                assert judge(c, k, r, 1, attempt=2, tools=("Bash",))[0] == 3
                continue
            ok(judge(c, k, r, pick_for(c, r, hit), attempt=2))
        elif r not in extra_rounds:
            ok(judge(c, k, r, pick_for(c, r, hit)))
    return c


def case_frame0_caught_at_7():
    c = scored(hits=range(7))
    out = parsed(ok(score(c, 0)))
    return out["H"] == "7" and out["verdict"] == "caught" and json.loads(read(os.path.join(c.W, "scores.json")))[
        "0"]["H"] == 7


def case_frame0_not_caught_at_6():
    c = scored(hits=range(6))
    out = parsed(ok(score(c, 0)))
    return out["H"] == "6" and out["verdict"] == "null: frame 0 not caught" and stops(
        cli("rounds", "--workdir", c.W, "--frame", 1), "not scored caught")


def case_long_frame_fails_at_7():
    c = scored(h0=12, hits=range(7), k=1)
    out = parsed(ok(score(c, 1)))
    return out["verdict"] == "judge can tell (fails)" and "frame test passed" not in "".join(out)


def case_long_frame_passes_at_6():
    c = scored(h0=12, hits=range(6), k=1)
    code, text = score(c, 1)
    return (code == 0 and parsed(text)["verdict"] == "passes"
            and "frame test passed: judge claude-opus-5-5, 20 rounds, 6 hits (frame 0: 12)" in text
            and stops(cli("rounds", "--workdir", c.W, "--frame", 2), "has passed")
            and stops(cli("rounds", "--workdir", c.W, "--frame", 0), "has passed"))


def case_double_void_frame0_miss():
    c = scored(hits=range(6), doubles=(19,))
    out = parsed(ok(score(c, 0)))
    return out["H"] == "6" and out["double voids"] == "1" and out["void first attempts"] == "1"


def case_double_void_long_hit():
    c = scored(h0=12, hits=range(6), doubles=(19,), k=1)
    out = parsed(ok(score(c, 1)))
    return out["H"] == "7" and out["verdict"] == "judge can tell (fails)"


def case_three_voids_scored():
    c = scored(hits=range(8), voids=(0, 10, 19))
    out = parsed(ok(score(c, 0)))
    return out["void first attempts"] == "3" and out["H"] == "8"


def case_four_voids_stop():
    c = scored(hits=range(8), voids=(0, 5, 10, 19))
    res = score(c, 0, 1, "--final-stop")
    return (stops(res, "void infrastructure") and "null: stopped" in res[1]
            and not os.path.exists(os.path.join(c.W, "scores.json")))


def case_rerun_listed():
    c = build("record2")
    ok(cli("rounds", "--workdir", c.W, "--frame", 0))
    for r in range(20):
        if r == 4:
            assert judge(c, 0, r, 1, tools=("Bash",))[0] == 3
        else:
            ok(judge(c, 0, r, pick_for(c, r, True)))
    code, out = score(c, 0)
    return code == 3 and "rounds to run: 1 (4)" in out and not os.path.exists(os.path.join(c.W, "scores.json"))


def case_score_accounting_left_out():
    c = scored(hits=range(8))
    transcript(c, prompts(c, 0)[3], js({"pick": 1, "reason": "x"}))       # a round run again, result not kept
    return stops(score(c, 0), "not in the ledger")


def case_score_accounting_missing():
    c = scored(hits=range(8))
    aid = json.loads(read(os.path.join(c.W, "ledger.jsonl")).splitlines()[-1])["agent_id"]
    os.remove(os.path.join(c.T, f"agent-{aid}.jsonl"))
    return stops(score(c, 0), "no transcript")


def case_score_rereads_transcripts():
    c = scored(hits=range(8))
    path = os.path.join(c.W, "ledger.jsonl")
    rows = [json.loads(x) for x in read(path).splitlines()]
    rows[-1]["status"] = "void"
    write(path, "".join(js(r) + "\n" for r in rows))
    c2 = scored(hits=range(8))
    path2 = os.path.join(c2.W, "ledger.jsonl")
    rows = [json.loads(x) for x in read(path2).splitlines()]
    aid = rows[-1]["agent_id"]
    tpath = os.path.join(c2.T, f"agent-{aid}.jsonl")
    trows = [json.loads(x) for x in read(tpath).splitlines()]
    trows[-1]["message"]["content"][0]["input"]["message"] = js({"pick": 5, "reason": "edited"})
    write(tpath, "".join(js(r) + "\n" for r in trows))
    return stops(score(c, 0), "disagree") and stops(score(c2, 0), "differs")


def case_first_scored_run_decides():
    c = scored(hits=range(9))
    first = parsed(ok(score(c, 0)))
    refused = judge(c, 0, 0, 1, run=2)                       # no stop found in run 1 yet
    os.remove(os.path.join(c.T, f"agent-a{IDS[0]:05d}.jsonl"))   # the refused run is not left behind
    stray = transcript(c, prompts(c, 0)[0], js({"pick": 1, "reason": "x"}))
    stop = score(c, 0)                                       # a stop the script finds in run 1
    os.remove(os.path.join(c.T, f"agent-{stray}.jsonl"))
    for r in range(20):
        ok(judge(c, 0, r, pick_for(c, r, False), run=2))
    later = score(c, 0, 2)
    sc = json.loads(read(os.path.join(c.W, "scores.json")))
    return (first["verdict"] == "caught" and stops(refused, "only after a stop") and stops(stop) and later[0] == 0
            and "decision stands from run 1: caught" in later[1] and sc["0"]["run"] == 1 and sc["0"]["H"] == 9
            and sc["0"]["later"][0]["H"] == 0)


def case_threshold_recomputed():
    c = scored(hits=range(7))
    saved = m.fp.ALPHA
    try:
        m.fp.ALPHA = 0.05
        res = score(c, 0)
    finally:
        m.fp.ALPHA = saved
    return stops(res, "threshold") and m.threshold() == 7 and m.THRESHOLD == 7


def case_score_reads_no_clue():
    c = scored(hits=range(7))
    for name in ("pool.json", "undrawn.json", "frame-0.txt", "test-topics.txt", "writer-request.txt"):
        os.remove(os.path.join(c.W, name))
    return parsed(ok(score(c, 0)))["H"] == "7"


def case_order():
    c = build("record2")
    early = cli("rounds", "--workdir", c.W, "--frame", 1)
    st_frame(c, 0, 9)
    skip = cli("rounds", "--workdir", c.W, "--frame", 2)
    st_frame(c, 1, 8)
    st_frame(c, 2, 8)
    last = st_frame(c, 3, 8)
    c2 = build("frame0", h0=9)
    out = st_frame(c2, 1, 8)
    return (stops(early, "not scored caught") and stops(skip, "earlier kept longer frame")
            and last["verdict"] == "judge can tell (fails)" and "null" in "".join(last)
            and "null: no longer frame passed" not in "".join(out))


def case_no_longer_passed_printed():
    c = build("frame0", h0=9)
    st_frame(c, 1, 8)
    st_frame(c, 2, 8)
    ok(cli("rounds", "--workdir", c.W, "--frame", 3))
    for r in range(20):
        ok(judge(c, 3, r, pick_for(c, r, r < 8)))
    code, out = score(c, 3)
    return code == 0 and "null: no longer frame passed" in out


def case_record_checked():
    out = []
    for label, value in (("seed-commit", "0" * 40), ("drawn-sha256", "0" * 64), ("pool-file-2-sha256", "0" * 64),
                         ("pool-count", "89"), ("frame-0-sha256", "0" * 64), ("judge-model", "claude-sonnet-5-5"),
                         ("judge-effort", "low"), ("threshold", "8"), ("verdicts-sha256", "0" * 64),
                         ("norm-mode", "other")):
        c = build("record2")
        set_rule(c, [(label, value)], replace=(label,))
        out.append(stops(cli("rounds", "--workdir", c.W, "--frame", 0), label))
    c = build("record2")
    set_rule(c, [], replace=("frame-2-sha256",))
    out.append(stops(cli("rounds", "--workdir", c.W, "--frame", 0), "frame-2-sha256"))
    c = build("record2")
    os.remove(os.path.join(c.W, "dry-instructions.json"))
    out.append(stops(cli("rounds", "--workdir", c.W, "--frame", 0), "baseline"))
    c = build("record2")
    git("-C", c.repo, "commit", "-q", "--allow-empty", "-m", "later")
    with open(os.path.join(c.repo, RULE_PATH), "a", encoding="utf-8") as f:
        f.write("More.\n")
    git("-C", c.repo, "commit", "-q", "-am", "later, same value")
    git("-C", c.repo, "update-ref", "refs/remotes/origin/main", "HEAD")
    out.append(cli("rounds", "--workdir", c.W, "--frame", 0)[0] == 0)
    return all(out)


def case_rounds_content():
    c = build("record2")
    ok(cli("rounds", "--workdir", c.W, "--frame", 0))
    rounds = json.loads(read(os.path.join(c.W, "rounds.json")))
    clue = {p["id"]: p["clue"] for p in json.loads(read(os.path.join(c.W, "pool.json")))}
    undrawn = {u["clue"] for u in json.loads(read(os.path.join(c.W, "undrawn.json")))}
    drawn = read(os.path.join(c.W, "drawn-ids.txt")).split()
    reals, ok_rounds = [], True
    tricks = {ct.fill(FRAMES[0], t) for t in TOPICS}
    for r, p in zip(rounds, json.loads(read(os.path.join(c.W, "prompts-frame0.json")))):
        body = p["prompt"][len("Invented judge prompt.\n"):-len("\nEnd.\n")]
        lines = body.split("\n")
        qs = [ln.split(". ", 1)[1] for ln in lines]
        ok_rounds &= ([ln.split(". ", 1)[0] for ln in lines] == ["1", "2", "3", "4", "5"]
                      and qs[r["pos"]] == ct.fill(FRAMES[0], r["topic"]) and sum(q in tricks for q in qs) == 1
                      and [q for i, q in enumerate(qs) if i != r["pos"]] == [clue[i] for i in r["ids"]])
        reals += [q for i, q in enumerate(qs) if i != r["pos"]]
    return (ok_rounds and reals == [clue[i] for i in drawn] and len(set(reals)) == 80 and not set(reals) & undrawn
            and sorted(r["topic"] for r in rounds) == sorted(TOPICS))


def case_frame_not_kept():
    c, res = flow([ALL], [], strike=(2,))
    c.frames = parsed(ok(res))
    st_record2(c)
    return stops(cli("rounds", "--workdir", c.W, "--frame", 2), "not kept") and cli(
        "rounds", "--workdir", c.W, "--frame", 0)[0] == 0


# ----------------------------------------------------------------------------- 17.8.3 template
def template_cmd(c, path, *extra):
    return cli("template", "--workdir", c.W, "--file", path, *extra)


def case_template():
    c = scored(h0=12, hits=range(4), k=1)
    ok(score(c, 1))
    f1 = os.path.join(c.W, "frame-1.txt")
    set_rule(c, [("template-sha256", ct.file_sha(f1))])
    good = template_cmd(c, f1)
    f0 = os.path.join(c.W, "frame-0.txt")
    set_rule(c, [("template-sha256", ct.file_sha(f0))], replace=("template-sha256",))
    wrong = template_cmd(c, f0)
    route = template_cmd(c, f0, "--null-route")
    other = os.path.join(c.base, "other.txt")
    write(other, "x")
    return (good[0] == 0 and stops(wrong, "frame-N-sha256") and stops(route, "no null route")
            and stops(template_cmd(c, other), "template file"))


def case_template_null_route():
    c = build("frame0", h0=9)
    for k in (1, 2, 3):
        st_frame(c, k, 9)
    f0 = os.path.join(c.W, "frame-0.txt")
    set_rule(c, [("template-sha256", ct.file_sha(f0))])
    return template_cmd(c, f0, "--null-route")[0] == 0 and stops(template_cmd(c, f0), "null route was not given")


# ----------------------------------------------------------------------------- run
GROUPS = [
    ("topics (17.3)", [("topics: canonical file, five per band, survivors, prompts: hashes printed, nothing written",
                        case_topics_ok),
                       ("topics: any other form of the file stops", case_topics_form),
                       ("topics: 19 topics stop", case_topics_count),
                       ("topics: a topic not 4-16 CJK stops", case_topics_pattern),
                       ("topics: six in one band stops", case_topics_bands),
                       ("topics: two equal after norm stop", case_topics_norm_duplicate),
                       ("topics: a topic sharing a 3-gram with a title stops", case_topics_survivors),
                       ("topics: a prompt without its placeholders exactly once stops", case_topics_prompts)]),
    ("section 16 (17.3.3)", [("labels: counted; a label standing twice stops labels and pool", case_labels)]),
    ("pool and draw (17.2)", [("pool: 90 ids, the seed commit found, the draw written as 17.2.2 says", case_pool_ok),
                              ("draw: golden ids, topic order and positions for a fixed commit", case_golden),
                              ("pool: 91 or 89 ids stop", case_pool_count),
                              ("pool: the topics record must match the files and the norm mode", case_pool_record),
                              ("seed: a later commit with another value stops", case_seed_later_commit_differs),
                              ("seed: the rule file as it stands with another value stops", case_seed_file_differs),
                              ("seed: the file as it stands is compared by the seed rule itself",
                               case_seed_line_in_file_checked),
                              ("seed: no commit holding the line stops", case_seed_none),
                              ("seed: a shallow repository stops", case_seed_shallow),
                              ("seed: prose naming the label is not the line; the oldest commit is chosen",
                               case_seed_prose_not_matched)]),
    ("dry runs (17.5.5)", [("dry: three valid runs make the baseline", case_dry_ok),
                           ("dry: the latest dry run of a role void stops dry-score", case_dry_invalid),
                           ("dry: different instruction files stop dry-score", case_dry_instructions_differ)]),
    ("frames (17.4)", [("code: the four frames and the length bounds pass", case_frame_code_good),
                       ("code: each rule of 17.4.3 fails its frame", case_frame_code_bad),
                       ("code: title marks round 周易研究 are allowed", case_title_marks_round_venue_allowed),
                       ("lists: 3-grams of the rest with counts, none across a join", case_grams_listed),
                       ("lists: a code failure asks a rewrite with its reason", case_code_fail_rewrite),
                       ("frames: a second code failure drops the frame", case_second_code_failure_drops),
                       ("frames: a rewrite that passes is kept", case_code_failure_then_fixed_kept),
                       ("frames: flagged once, rewritten, passed: kept", case_flag_then_rewrite_kept),
                       ("frames: flagged twice: dropped", case_flag_twice_drops),
                       ("frames: rewritten for code, then flagged: dropped", case_code_rewrite_then_flagged_drops),
                       ("frames: a struck frame is not kept", case_struck_not_kept),
                       ("frames: frame 0 struck: null: frame 0 not kept", case_null_frame0),
                       ("frames: no longer frame kept: null, and no round", case_null_no_longer),
                       ("frames: finish refused while a frame waits", case_finish_waits),
                       ("frames: glosses written to the work directory, not printed", case_glosses_private),
                       ("writer: one void run, then a valid one; a third run refused",
                        case_writer_void_once_then_valid),
                       ("writer: two void runs of one request stop", case_writer_void_twice_stops),
                       ("checker: two void runs of one request stop", case_checker_void_twice_stops),
                       ("writer: a later reply with another frame or another shape is void",
                        case_later_writer_reply_shape),
                       ("finish: a writer run left out of the ledger stops", case_finish_accounting_writer),
                       ("finish: a checker run left out of the ledger stops", case_finish_accounting_checker),
                       ("finish: a recorded run without its transcript stops", case_finish_missing_transcript),
                       ("finish: a transcript's first message is compared with its request",
                        case_finish_first_message_compared),
                       ("dry: the baseline is not replaced once real runs are recorded",
                        case_baseline_fixed_after_real_runs),
                       ("ledger: one agent's run is recorded once", case_agent_recorded_once),
                       ("frames: no strike after finish", case_strike_after_finish_refused)]),
    ("runs (17.5.3)", [("run: a valid judge run", case_valid_run),
                       ("run: pick 0, 6, a string, a boolean, a float, a wrong shape: void", case_void_picks),
                       ("run: prose or a fence round the JSON: void; whitespace is not prose", case_void_prose),
                       ("run: a tool call voids a judge", case_void_tool_judge),
                       ("run: a tool call voids the writer and the checker", case_void_tool_writer_checker),
                       ("run: another model, effort or first message: void", case_void_model_effort_message),
                       ("run: no hand-back, or one without message: void", case_void_no_handback),
                       ("run: the last hand-back is the answer, not text outside it", case_last_handback_counts),
                       ("run: a reply differing from the transcript stops", case_reply_mismatch_stops),
                       ("run: the answer is read from the transcript, not the reply file",
                        case_answer_from_transcript_not_ledger),
                       ("run: a missing transcript field stops, not void", case_missing_field_stops),
                       ("run: instruction files other than the dry runs' stop", case_instructions_differ_stop),
                       ("run: attempt 2 only after a void attempt 1, once", case_attempts),
                       ("run: a second run of a frame needs a stop the script found", case_rerun_needs_script_stop)]),
    ("score and order (17.6, 17.7)", [
        ("score: frame 0 with 7 hits is caught", case_frame0_caught_at_7),
        ("score: frame 0 with 6 hits is null, and frame 1 is refused", case_frame0_not_caught_at_6),
        ("score: a longer frame with 7 hits fails", case_long_frame_fails_at_7),
        ("score: a longer frame with 6 hits passes, with its label; nothing judged after", case_long_frame_passes_at_6),
        ("score: a double void is a miss for frame 0", case_double_void_frame0_miss),
        ("score: a double void is a hit for a longer frame", case_double_void_long_hit),
        ("score: 3 void first attempts, re-run, are scored", case_three_voids_scored),
        ("score: 4 void first attempts stop; --final-stop says null: stopped", case_four_voids_stop),
        ("score: a void round without its re-run is listed, nothing written", case_rerun_listed),
        ("score: a judge run left out of the ledger stops", case_score_accounting_left_out),
        ("score: a recorded judge run without its transcript stops", case_score_accounting_missing),
        ("score: the transcripts are read again, the ledger is not trusted", case_score_rereads_transcripts),
        ("score: the first scored run decides; a re-run needs a script stop", case_first_scored_run_decides),
        ("score: the threshold is recomputed from frame_power.py", case_threshold_recomputed),
        ("score: no clue file is read", case_score_reads_no_clue),
        ("order: frame 0 first, then 1, 2, 3 after failures; null: no longer frame passed", case_order),
        ("order: the last longer frame failing prints the null", case_no_longer_passed_printed),
        ("rounds: every label of the records is checked", case_record_checked),
        ("rounds: one trick at its position, 80 distinct drawn clues, no undrawn clue", case_rounds_content),
        ("rounds: a frame not kept is refused", case_frame_not_kept)]),
    ("template (17.8.3)", [("template: the passed frame's hash; anything else stops", case_template),
                           ("template: frame 0 only on the null route", case_template_null_route)]),
]

bad = 0
total = 0
for group, cases in GROUPS:
    group_bad = 0
    for name, fn in cases:
        try:
            good = bool(fn())
        except Exception as exc:  # an exception in the code under test counts as a failed case
            good = False
            name += f"  [{type(exc).__name__}: {exc}]"
        group_bad += not good
        print("PASS" if good else "FAIL", "-", name)
    print(f"{len(cases) - group_bad} of {len(cases)} pass: {group}")
    bad += group_bad
    total += len(cases)
print(f"{total - bad} of {total} pass")
shutil.rmtree(TMP, ignore_errors=True)
sys.exit(1 if bad else 0)
