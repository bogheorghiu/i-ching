"""The frame test of CONTROLS-RULE.md section 17: the topics record, the pool and the draw, the dry runs, the frames,
the judge rounds, the score and the template check. The agent calls are made by the person running the test; this
script writes every prompt, records every run from its transcript, and refuses any step section 17 does not allow.

Usage: python3 -I frame_test.py SUBCOMMAND --workdir W ...   (SUBCOMMAND -h for its arguments)
Order: topics, (topics record merged), pool, dry-prompts, dry-record x3, dry-score, frames add/lists/verdicts/strike,
frames finish, (record of 17.8.2 merged), rounds, run x20, score, then the next frame as 17.7 allows; template.
Standard output holds counts, sha256 and the words of a verdict. A stop prints "stop: <cause>" and exits 2; a void
run prints "void: <reason>" and exits 3 (run it again).
"""
import argparse
import datetime
import glob
import json
import os
import random
import re
import subprocess
import sys
import unicodedata

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import build_keys as bk  # noqa: E402
import control_topics as ct  # noqa: E402
import frame_power as fp  # noqa: E402

POOL_N, ROUNDS, DRAWN_N, THRESHOLD = 90, 20, 80, 7
JUDGE_MODEL, JUDGE_EFFORT = "claude-opus-5-5", "medium"
FRAME0_MAX, LONG_MIN, LONG_MAX = 40, 56, 72
SEED_TEXT = "b2-frametest-2026-11-23:"
REF = "origin/main"
RULE_PATH = "research/battery2/pipeline/CONTROLS-RULE.md"
PARTS = ("期刊论文", "易学", "周易研究", "2010年代")
BANDS = ((4, 6), (7, 9), (10, 12), (13, 16))
HANDBACK = "SubagentHandback"
ROLES = ("writer", "checker", "judge")
PROMPT_FILES = {"writer": ("writer-prompt.txt", ("examples", "rewrite")),
                "checker": ("checker-prompt.txt", ("frames",)),
                "judge": ("judge-prompt.txt", ("questions",))}
DRY_FILES = {"writer": "dry-writer-request.txt", "checker": "dry-checker-request.txt", "judge": "dry-judge-prompt.txt"}
TOPICS_RECORD = ("probe-topics-sha256", "verdicts-sha256", "norm-mode", "writer-prompt-sha256", "checker-prompt-sha256",
                 "judge-prompt-sha256")
LONG_VERDICT, PASS_VERDICT = "judge can tell (fails)", "passes"
CAUGHT, NOT_CAUGHT = "caught", "null: frame 0 not caught"
REWRITE = ("This is a new request. It replaces the instruction above about the reply: write only the frames listed "
           'below, and reply with a JSON list of objects {"frame": K, "text": "..."}, one per frame listed, and '
           "nothing else.\n")
need = ct.need


class Found(ct.Stop):
    """A stop of 17.7.5 that the script finds in the runs: the only kind after which a frame's rounds may be run
    again (17.7.5); a refused command (a wrong attempt, a wrong order) is not one."""


def found(cond, msg):
    if not cond:
        raise Found(msg)

# 17.5.5: invented content for the dry runs; none is a real clue, topic or frame of the test.
DRY_CLUES = ["一篇2010年代刊于《周易研究》的易学期刊论文，考察虚构的云端小镇如何用骰子记账。",
             "一篇2010年代《周易研究》所载易学期刊论文，比较两部虚构的海底图书馆目录。",
             "一篇2010年代发表在《周易研究》的易学期刊论文，追溯一只会写诗的虚构机器猫的书信。",
             "一篇2010年代见于《周易研究》的易学期刊论文，评估虚构王国里雨伞税的征收办法。"]
DRY_FRAMES = ["一篇2010年代刊于《周易研究》的易学期刊论文，讨论{topic}。",
              "一篇2010年代刊于《周易研究》的易学期刊论文，以{topic}为对象，梳理其材料来源与前后变化，并说明相关说法如何形成，"
              "兼及其写法。",
              "一篇2010年代发表在《周易研究》的易学期刊论文，先辨析{topic}的几种说法，再比较各说的依据与得失，"
              "最后评估诸说的价值。",
              "一篇2010年代见于《周易研究》的易学期刊论文，所考察者并非泛论，而是围绕{topic}展开的问题，"
              "文中再逐层追溯其来龙去脉。"]
DRY_TOPIC = "火星蘑菇农场的账簿"
DRY_GRAMS = [("讨论火", 2, 0), ("梳理其", 0, 3)]


# ----------------------------------------------------------------------------- small pieces
def sha_text(text):
    return ct.list_sha([text])


def read_text(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


def write_text(path, text):
    with open(path, "w", encoding="utf-8", newline="") as f:
        f.write(text)


def write_json(path, obj):
    write_text(path, json.dumps(obj, ensure_ascii=False, indent=1))


def read_json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def read_jsonl(path):
    if not os.path.exists(path):
        return []
    with open(path, encoding="utf-8") as f:
        return [json.loads(ln) for ln in f if ln.strip()]


def append_jsonl(path, obj):
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(obj, ensure_ascii=False) + "\n")


def now():
    return datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")


def put(template, **parts):
    """Fills each {name} in one pass, so a filled text that holds a placeholder's name is not filled again."""
    return re.sub(r"\{(" + "|".join(parts) + r")\}", lambda m: parts[m.group(1)], template)


def numbered(clues):
    return "\n".join(f"{i}. {c}" for i, c in enumerate(clues, 1))


def is_int(x):
    return isinstance(x, int) and not isinstance(x, bool)


def threshold():
    """17.6.2: recomputed from frame_power.py, which must give the registered 7."""
    t = fp.threshold(fp.total(fp.hyper_pmf(5, 1, 1), ROUNDS))
    found(t == THRESHOLD, f"the threshold recomputed from frame_power.py is {t}, not {THRESHOLD}")
    return t


# ----------------------------------------------------------------------------- section 16 (17.3.3, 17.8.2)
def section16(text):
    """Every (label, value) line of section 16, sliced as control_topics.registered slices it (it exports no slicer)."""
    head = re.search(r"^## 16\.", text, re.M)
    if not head:
        return []
    after = re.search(r"^## ", text[head.end():], re.M)
    section = text[head.start():head.end() + after.start()] if after else text[head.start():]
    return re.findall(r"^- `([^`\n]+)`: `([^`\n]+)`[ \t]*$", section, re.M)


def labels():
    """17.3.3: registered takes the last value of a label and compares nothing, so a label standing twice stops."""
    names = [k for k, _ in section16(read_text(ct.RULE))]
    twice = sorted({k for k in names if names.count(k) > 1})
    need(not twice, f"a label of section 16 stands twice: {', '.join(twice)}")
    return len(names)


def expect(label, value):
    need(ct.registered(label).lower() == str(value).lower(), f"{label} in section 16 is not what was found")


def topics_record(w, verdicts_path):
    expect("probe-topics-sha256", ct.file_sha(os.path.join(w, "test-topics.txt")))
    expect("verdicts-sha256", ct.file_sha(verdicts_path))
    need(ct.registered("norm-mode") == ct.norm_mode(), "norm-mode in section 16 is not this machine's")
    for role in ROLES:
        expect(f"{role}-prompt-sha256", ct.file_sha(os.path.join(w, PROMPT_FILES[role][0])))


# ----------------------------------------------------------------------------- the seed commit (17.2.2)
def git(repo, *args):
    r = subprocess.run(["git", "-C", repo, *args], capture_output=True, text=True)
    return r.returncode, r.stdout


def seed_line(text):
    vals = [v.lower() for k, v in section16(text) if k == "probe-topics-sha256" and re.fullmatch(r"[0-9a-fA-F]{64}", v)]
    return vals[-1] if vals else None


def seed_commit(repo):
    """The oldest first-parent commit of REF whose rule file holds the topics record's line in section 16, found by
    parsing section 16 (a pickaxe would also match prose that names the label, as section 17 does)."""
    rc, out = git(repo, "rev-parse", "--is-shallow-repository")
    need(rc == 0 and out.strip() == "false", "the repository is shallow (or not a repository)")
    rc, out = git(repo, "log", "--first-parent", "--reverse", "--format=%H", REF, "--", RULE_PATH)
    need(rc == 0, f"{REF} has no history of the rule file")
    values = []
    for commit in out.split():
        rc, text = git(repo, "show", f"{commit}:{RULE_PATH}")
        values.append((commit, seed_line(text) if rc == 0 else None))
    first = next((i for i, (_, v) in enumerate(values) if v), None)
    need(first is not None, "no commit holds the topics record's line")
    value = values[first][1]
    need(all(v == value for _, v in values[first + 1:]), "the topics record's line has another value in a later commit")
    need(seed_line(read_text(ct.RULE)) == value, "the topics record's line has another value in the rule file")
    return values[first][0]


# ----------------------------------------------------------------------------- topics (17.3)
def test_topics(w, verdicts):
    path = os.path.join(w, "test-topics.txt")
    with open(path, "rb") as f:
        raw = f.read()
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        text = None
    lines = text.split("\n")[:-1] if text else []
    need(text is not None and lines and raw == ("\n".join(lines) + "\n").encode("utf-8")
         and not text.startswith("\ufeff") and all(t and t == t.strip() for t in lines),
         "the topics file is not in the canonical form of 17.3.3")
    need(len(lines) == ROUNDS, f"the topics file holds {len(lines)} topics, not {ROUNDS}")
    need(all(ct.TOPIC.fullmatch(t) for t in lines), "a topic is not 4-16 CJK characters")
    bands = [sum(lo <= len(t) <= hi for t in lines) for lo, hi in BANDS]
    need(bands == [5, 5, 5, 5], "the topics are not five in each length band")
    need(len({bk.norm(t) for t in lines}) == ROUNDS, "two topics are equal after norm")
    surv, _ = ct.survivors([(0, t) for t in lines], ct.listing_of(verdicts, []))
    need(len(surv) == ROUNDS, "a topic does not survive 15.4.1-15.4.2")
    return lines, bands


def check_prompts(w):
    for role, (name, holes) in PROMPT_FILES.items():
        path = os.path.join(w, name)
        need(os.path.isfile(path), f"{name} is missing")
        text = read_text(path)
        need(all(text.count("{" + h + "}") == 1 for h in holes), f"{name} does not hold its placeholders exactly once")


def cmd_topics(a):
    verdicts = read_json(a.verdicts)
    _, bands = test_topics(a.workdir, verdicts)
    check_prompts(a.workdir)
    print(f"probe-topics-sha256: {ct.file_sha(os.path.join(a.workdir, 'test-topics.txt'))}")
    print(f"verdicts-sha256: {ct.file_sha(a.verdicts)}")
    print(f"norm-mode: {ct.norm_mode()}")
    for role in ROLES:
        print(f"{role}-prompt-sha256: {ct.file_sha(os.path.join(a.workdir, PROMPT_FILES[role][0]))}")
    for (lo, hi), n in zip(BANDS, bands):
        print(f"topics {lo}-{hi}: {n}")


# ----------------------------------------------------------------------------- pool and draw (17.2)
def in_pool(r):
    entry = (r.get("clues_by_writer") or {}).get(r.get("clue_writer")) or {}
    clue = r.get("clue")
    year = (r.get("key") or {}).get("year")
    return ((r.get("stratum") or {}).get("type") == "article" and (r.get("stratum") or {}).get("language") == "zh"
            and (r.get("key") or {}).get("venue") == "周易研究" and is_int(year) and 2010 <= year <= 2019
            and entry.get("anchor") == "venue" and isinstance(clue, str)
            and bk.norm("周易研究") in bk.norm(clue) and bk.norm("2010年代") in bk.norm(clue))


def pool_of(item_paths):
    rows = [r for p in item_paths for r in read_jsonl(p)]
    count = {}
    for r in rows:
        count[r.get("id")] = count.get(r.get("id"), 0) + 1
    pool = sorted(({"id": r["id"], "clue": r["clue"]} for r in rows if count[r.get("id")] == 1 and in_pool(r)),
                  key=lambda x: x["id"])
    need(len(pool) == POOL_N, f"the pool holds {len(pool)} ids, not {POOL_N}")
    return pool


def draw(ids, topics, c):
    """17.2.2, given the pool's ids sorted, the topics in file order and the seed commit."""
    rng = random.Random(SEED_TEXT + c)
    drawn = rng.sample(ids, DRAWN_N)
    topics = list(topics)
    rng.shuffle(topics)
    pos = [0, 1, 2, 3, 4] * 4
    rng.shuffle(pos)
    return drawn, topics, pos


def writer_text(w, rewrite):
    undrawn = read_json(os.path.join(w, "undrawn.json"))
    return put(read_text(os.path.join(w, "writer-prompt.txt")), examples=numbered([u["clue"] for u in undrawn]),
               rewrite=rewrite)


def cmd_pool(a):
    w = a.workdir
    labels()
    topics_record(w, a.verdicts)
    c = seed_commit(a.repo)
    topics, _ = test_topics(w, read_json(a.verdicts))
    pool = pool_of(a.items)
    drawn, order, pos = draw([p["id"] for p in pool], topics, c)
    clue = {p["id"]: p["clue"] for p in pool}
    undrawn = [{"id": i, "clue": clue[i]} for i in sorted(set(clue) - set(drawn))]
    write_json(os.path.join(w, "pool.json"), pool)
    write_text(os.path.join(w, "drawn-ids.txt"), "".join(i + "\n" for i in drawn))
    write_json(os.path.join(w, "undrawn.json"), undrawn)
    write_json(os.path.join(w, "rounds.json"), [{"round": r, "topic": order[r], "ids": drawn[4 * r:4 * r + 4],
                                                 "pos": pos[r]} for r in range(ROUNDS)])
    write_json(os.path.join(w, "inputs.json"), {
        "items": [{"path": os.path.realpath(p), "sha256": ct.file_sha(p)} for p in a.items],
        "verdicts": {"path": os.path.realpath(a.verdicts), "sha256": ct.file_sha(a.verdicts)},
        "seed_commit": c, "repo": os.path.realpath(a.repo)})
    write_text(os.path.join(w, "writer-request.txt"), writer_text(w, ""))
    print(f"pool-count: {len(pool)}\ndrawn: {len(drawn)}\nundrawn: {len(undrawn)}\nrounds: {ROUNDS}")
    for n, p in enumerate(a.items, 1):
        print(f"pool-file-{n}-sha256: {ct.file_sha(p)}")
    print(f"drawn-sha256: {ct.file_sha(os.path.join(w, 'drawn-ids.txt'))}\nseed-commit: {c}")


# ----------------------------------------------------------------------------- transcripts (17.5.3)
def read_run(path):
    rows = []
    with open(path, encoding="utf-8") as f:
        for ln in f:
            if ln.strip():
                try:
                    rows.append(json.loads(ln))
                except ValueError:
                    found(False, "transcript lacks JSON lines")
    first = next((r for r in rows if r.get("type") == "user"), None)
    found(first is not None and isinstance((first.get("message") or {}).get("content"), str),
          "transcript lacks the first user message")
    assistants = [r for r in rows if r.get("type") == "assistant"]
    found(assistants, "transcript lacks an assistant row")
    tools, handbacks = [], []
    for r in assistants:
        msg = r.get("message") or {}
        found(msg.get("model") and r.get("effort"), "transcript lacks the model or the effort")
        found(isinstance(msg.get("content"), list), "transcript lacks the content blocks")
        for b in msg["content"]:
            if isinstance(b, dict) and b.get("type") == "tool_use":
                found(isinstance(b.get("name"), str), "transcript lacks a tool call's name")
                tools.append(b["name"])
                if b["name"] == HANDBACK:
                    inp = b.get("input")
                    handbacks.append(inp.get("message") if isinstance(inp, dict) else None)
    instr = [r for r in rows
             if r.get("type") == "attachment" and (r.get("attachment") or {}).get("type") == "instructions"]
    found(instr, "transcript lacks the instructions row")
    files = []
    for r in instr:
        for f in r["attachment"].get("files") or []:
            found(isinstance(f, dict) and isinstance(f.get("path"), str) and isinstance(f.get("content"), str),
                  "transcript lacks an instruction file's path or content")
            files.append([f["path"], sha_text(f["content"])])
    return {"first": first["message"]["content"], "assistants": assistants, "tools": tools, "handbacks": handbacks,
            "pairs": {(r["message"]["model"], r["effort"]) for r in assistants}, "instructions": sorted(files)}


def first_message(path):
    """The first user message of any transcript in the folder, or None: used only to find runs left out."""
    try:
        with open(path, encoding="utf-8") as f:
            for ln in f:
                r = json.loads(ln) if ln.strip() else {}
                if r.get("type") == "user":
                    c = (r.get("message") or {}).get("content")
                    return c if isinstance(c, str) else None
    except (OSError, ValueError):
        return None
    return None


def answer_ok(obj, role, frames):
    if role == "judge":
        return (isinstance(obj, dict) and set(obj) == {"pick", "reason"} and is_int(obj["pick"])
                and 1 <= obj["pick"] <= 5 and isinstance(obj["reason"], str))
    if role == "writer" and frames is None:
        return isinstance(obj, list) and len(obj) == 4 and all(isinstance(x, str) for x in obj)
    keys = {"frame", "text"} if role == "writer" else {"frame", "verdict", "reason", "gloss"}
    return (isinstance(obj, list) and all(isinstance(x, dict) and set(x) == keys and is_int(x["frame"])
                                          and all(isinstance(x[k], str) for k in keys - {"frame"}) for x in obj)
            and sorted(x["frame"] for x in obj) == sorted(frames)
            and (role == "writer" or all(x["verdict"] in ("passes", "flagged") for x in obj)))


def void_reason(run, prompt, role, frames=None):
    """17.5.3, the same for every role and for the dry runs. frames: for a later writer request, the frames it asked;
    for the checker, the frames it was given; None for the first writer request and the judge."""
    if any(t != HANDBACK for t in run["tools"]):
        return "a tool call other than SubagentHandback"
    if run["pairs"] != {(JUDGE_MODEL, JUDGE_EFFORT)}:
        return f"a turn not run on {JUDGE_MODEL} at effort {JUDGE_EFFORT}"
    if run["first"] != prompt:
        return "the first user message is not the prompt"
    if not run["handbacks"]:
        return "no SubagentHandback call"
    answer = run["handbacks"][-1]
    if not isinstance(answer, str):
        return "the hand-back holds no message"
    try:
        obj = json.loads(answer.strip())
    except ValueError:
        return "the answer is not JSON alone"
    if not answer_ok(obj, role, frames):
        return "the answer is not the form the request asks"
    return None


def answer_of(run):
    return json.loads(run["handbacks"][-1].strip())


# ----------------------------------------------------------------------------- ledger (17.5.4)
def ledger_path(w):
    return os.path.join(w, "ledger.jsonl")


def transcript(tdir, agent_id):
    need(re.fullmatch(r"[0-9A-Za-z_-]+", agent_id or ""), "an agent id is not a plain name")
    return os.path.join(tdir, f"agent-{agent_id}.jsonl")


def check_reply(run, reply):
    last = run["handbacks"][-1] if run["handbacks"] else None
    found(not isinstance(last, str) or reply == last, "the ledger's reply differs from the transcript's message")


def check_baseline(w, run):
    path = os.path.join(w, "dry-instructions.json")
    found(os.path.isfile(path) and read_json(path) == run["instructions"],
          "instruction files differ from the dry runs'")


def rescore(w, row, tdir, prompt, role, frames=None):
    """A recorded run read again from its transcript: (run, void reason). Trusts nothing the ledger says."""
    path = transcript(tdir, row["agent_id"])
    found(os.path.isfile(path), "a recorded run has no transcript")
    run = read_run(path)
    if not row["purpose"].startswith("dry-"):
        check_baseline(w, run)
    check_reply(run, row["reply"])
    reason = void_reason(run, prompt, role, frames)
    found(("void" if reason else "valid") == row["status"], "the ledger and the transcripts disagree")
    return run, reason


def record(a, purpose, request, prompt, role, frames=None, **extra):
    """Reads the run's transcript at once, applies the void rules, appends the ledger row. (row, run)."""
    w = a.workdir
    ledger = read_jsonl(ledger_path(w))
    need(all(r["agent_id"] != a.agent_id for r in ledger), "this agent's run is already in the ledger")
    path = transcript(a.transcripts, a.agent_id)
    found(os.path.isfile(path), "a recorded run has no transcript")
    run = read_run(path)
    if not purpose.startswith("dry-"):
        check_baseline(w, run)
    reply = read_text(a.reply_file)
    check_reply(run, reply)
    reason = void_reason(run, prompt, role, frames)
    row = {"purpose": purpose, "agent_id": a.agent_id, "time": now(), "request": request, **extra, "reply": reply,
           "status": "void" if reason else "valid", "reason": reason}
    append_jsonl(ledger_path(w), row)
    return row, run


def request_runs(w, purpose, request):
    return [r for r in read_jsonl(ledger_path(w)) if r["purpose"] == purpose and r["request"] == request]


def record_request(a, purpose, request, prompt, role, frames):
    """17.5.3: a void run of the writer or the checker is run once more, once; a second void is a stop."""
    earlier = request_runs(a.workdir, purpose, request)
    need(all(r["status"] == "void" for r in earlier), "this request already has a valid run")
    need(len(earlier) < 2, "two void runs of one request")
    row, run = record(a, purpose, request, prompt, role, frames, attempt=len(earlier) + 1)
    if row["status"] == "void":
        need(len(earlier) == 0, "two void runs of one request")
        print(f"void: {row['reason']}")
        return None
    return run


def account(w, tdir, rows, prompts):
    """17.5.4: every recorded run has its transcript, and every transcript whose first message is one of the test's
    prompts is a ledger row exactly once."""
    ids = [r["agent_id"] for r in read_jsonl(ledger_path(w))]
    for r in rows:
        found(os.path.isfile(transcript(tdir, r["agent_id"])), "a recorded run has no transcript")
    for path in sorted(glob.glob(os.path.join(tdir, "agent-*.jsonl"))):
        if first_message(path) in prompts:
            aid = os.path.basename(path)[len("agent-"):-len(".jsonl")]
            found(ids.count(aid) == 1, "a run whose prompt is the test's is not in the ledger exactly once")


def request_files(w, *patterns):
    return {os.path.basename(p): read_text(p) for pat in patterns for p in glob.glob(os.path.join(w, pat))}


def all_prompts(w):
    prompts = set(request_files(w, "writer-request.txt", "writer-retry-request-*.txt", "checker-request-*.txt",
                                *DRY_FILES.values()).values())
    for path in glob.glob(os.path.join(w, "prompts-frame*.json")):
        prompts |= {p["prompt"] for p in read_json(path)}
    return prompts


# ----------------------------------------------------------------------------- dry runs (17.5.5)
def checker_block(frames, grams):
    """The {frames} text: per frame "Frame K: <text>" and its list of 3-grams with counts."""
    return "\n\n".join(f"Frame {k}: {text}" + "".join(f"\n{g}: titles {n}, abstracts {m}" for g, n, m in grams[k])
                       for k, text in frames)


def cmd_dry_prompts(a):
    w = a.workdir
    check_prompts(w)
    trick = ct.fill(DRY_FRAMES[0], DRY_TOPIC)
    texts = {"writer": put(read_text(os.path.join(w, "writer-prompt.txt")), examples=numbered(DRY_CLUES), rewrite=""),
             "checker": put(read_text(os.path.join(w, "checker-prompt.txt")), frames=checker_block(
                 list(enumerate(DRY_FRAMES)), {k: DRY_GRAMS for k in range(4)})),
             "judge": put(read_text(os.path.join(w, "judge-prompt.txt")), questions=numbered(DRY_CLUES[:2] + [trick]
                                                                                              + DRY_CLUES[2:]))}
    for role, text in texts.items():
        write_text(os.path.join(w, DRY_FILES[role]), text)
        print(f"{DRY_FILES[role]}-sha256: {sha_text(text)}")


def dry_frames(role):
    return set(range(4)) if role == "checker" else None


def cmd_dry_record(a):
    prompt = read_text(os.path.join(a.workdir, DRY_FILES[a.role]))
    row, _ = record(a, f"dry-{a.role}", DRY_FILES[a.role], prompt, a.role, dry_frames(a.role))
    if row["status"] == "void":
        print(f"void: {row['reason']}")
        return 3
    print("valid")


def cmd_dry_score(a):
    w = a.workdir
    ledger = read_jsonl(ledger_path(w))
    need(all(r["purpose"].startswith("dry-") for r in ledger), "real runs are recorded: the baseline is fixed")
    lists = []
    for role in ROLES:
        rows = [r for r in ledger if r["purpose"] == f"dry-{role}"]
        need(rows and rows[-1]["status"] == "valid", "a dry run is invalid")
        try:
            run, reason = rescore(w, rows[-1], a.transcripts, read_text(os.path.join(w, DRY_FILES[role])), role,
                                  dry_frames(role))
        except ct.Stop as e:
            raise ct.Stop(f"a dry run is invalid ({e})")
        need(reason is None, "a dry run is invalid")
        lists.append(run["instructions"])
    need(lists[0] == lists[1] == lists[2], "a dry run is invalid: the dry runs show different instruction files")
    write_json(os.path.join(w, "dry-instructions.json"), lists[0])
    print("".join(f"dry-{role}: valid\n" for role in ROLES) + f"instruction files: {len(lists[0])}")


# ----------------------------------------------------------------------------- frames (17.4)
def rest(frame):
    """The fixed text with each part, and the title marks round 周易研究, replaced by a space."""
    r = ct.fill(frame, "").replace("《周易研究》", "周易研究")
    for p in PARTS:
        r = r.replace(p, " ")
    return r


def frame_problem(k, text):
    """17.4.3: None, or why the frame fails the code checks."""
    try:
        ct.check_template(text)
    except ct.Stop as e:
        return f"the frame must hold {ct.SLOT} once and make a valid clue ({e})"
    fixed = ct.fill(text, "")
    if not all(p in fixed for p in PARTS):
        return "the frame must hold 期刊论文, 易学, 周易研究 and 2010年代"
    if ct.stray_digit(fixed):
        return "the frame must hold no digit outside 2010年代"
    r = rest(text)
    if re.search("[《》〈〉]", r) or re.search("[A-Za-z]", unicodedata.normalize("NFKC", r)):
        return "the frame must hold no title mark except round 周易研究 and no Latin letter"
    if not text.endswith("。"):
        return "the frame must end with 。"
    if k == 0 and len(fixed) > FRAME0_MAX:
        return f"frame 0's fixed text must be at most {FRAME0_MAX} characters"
    if k > 0 and not LONG_MIN <= len(fixed) <= LONG_MAX:
        return f"the fixed text must be {LONG_MIN} to {LONG_MAX} characters"
    return None


def grams_of(frame, lst):
    """17.4.5: the 3-character CJK sequences of the rest found in a listing title or an abstract, with counts. The
    rest is split at the spaces before norm, which would otherwise remove them and join across a part."""
    out = []
    for piece in rest(frame).split():
        n = bk.norm(piece)
        for g in dict.fromkeys(n[i:i + 3] for i in range(len(n) - 2)):
            if not bk._CJK3.match(g) or g in [x[0] for x in out]:
                continue
            titles = sum(ct.title_hit(g, [t]) for t in lst["forms"])
            abstracts = sum(ct.abstract_hit(g, [x]) for x in lst["abstracts"])
            if titles or abstracts:
                out.append((g, titles, abstracts))
    return out


def log_path(w):
    return os.path.join(w, "frames-log.jsonl")


def frames_state(w):
    st = {k: {"codes": [], "verdicts": {}, "struck": False} for k in range(4)}
    requests, answered = {"writer": {"writer-request.txt": None}, "checker": {}}, set()
    for e in read_jsonl(log_path(w)):
        if e["event"] == "code":
            st[e["frame"]]["codes"].append(e)
            answered.add(e["request"])
        elif e["event"] == "verdict":
            st[e["frame"]]["verdicts"][e["attempt"]] = e
            answered.add(e["request"])
        elif e["event"] == "strike":
            st[e["frame"]]["struck"] = True
        elif e["event"] == "request":
            requests[e["kind"]][e["name"]] = e["frames"]
    return st, requests, answered


def status(f):
    """17.4.3-17.4.6: kept, waiting (for the checker), rewrite, dropped-code, dropped-checker, struck, missing."""
    if f["struck"]:
        return "struck"
    if not f["codes"]:
        return "missing"
    last = f["codes"][-1]
    if last["code"] == "fail":
        return "dropped-code" if last["attempt"] == 2 else "rewrite"
    v = f["verdicts"].get(last["attempt"])
    if v is None:
        return "waiting"
    if v["verdict"] == "passes":
        return "kept"
    return "dropped-checker" if last["attempt"] == 2 else "rewrite"


def pending(requests, answered, kind):
    return {k for name, fr in requests[kind].items() if name not in answered for k in (fr or range(4))}


def listing(w):
    return ct.listing_of(read_json(read_json(os.path.join(w, "inputs.json"))["verdicts"]["path"]), [])


def cmd_frames_add(a):
    w = a.workdir
    st, requests, answered = frames_state(w)
    need(a.request in requests["writer"] and a.request not in answered, f"{a.request} is not an open writer request")
    asked = requests["writer"][a.request]
    run = record_request(a, "writer", a.request, read_text(os.path.join(w, a.request)), "writer",
                         None if asked is None else set(asked))
    if run is None:
        return 3
    reply = answer_of(run)
    texts = dict(enumerate(reply)) if asked is None else {x["frame"]: x["text"] for x in reply}
    counts = {"pass": 0, "fail": 0}
    for k, text in sorted(texts.items()):
        attempt = len(st[k]["codes"]) + 1
        need(attempt <= 2, "a frame has at most 2 attempts")
        why = frame_problem(k, text)
        counts["fail" if why else "pass"] += 1
        append_jsonl(log_path(w), {"event": "code", "frame": k, "attempt": attempt, "text": text,
                                   "code": "fail" if why else "pass", "reason": why, "request": a.request})
    print(f"valid\nframes passing code: {counts['pass']}\nframes failing code: {counts['fail']}")


def cmd_frames_lists(a):
    w = a.workdir
    st, requests, answered = frames_state(w)
    with_checker, asked = pending(requests, answered, "checker"), pending(requests, answered, "writer")
    waiting = [k for k in range(4) if status(st[k]) == "waiting" and k not in with_checker]
    rewrite = [k for k in range(4) if status(st[k]) == "rewrite" and k not in asked]
    if waiting:
        lst = listing(w)
        frames = [(k, st[k]["codes"][-1]["text"]) for k in waiting]
        name = f"checker-request-{len(requests['checker']) + 1}.txt"
        write_text(os.path.join(w, name), put(read_text(os.path.join(w, "checker-prompt.txt")), frames=checker_block(
            frames, {k: grams_of(t, lst) for k, t in frames})))
        append_jsonl(log_path(w), {"event": "request", "kind": "checker", "name": name, "frames": waiting})
    if rewrite:
        lines = []
        for k in rewrite:
            last = st[k]["codes"][-1]
            why = last["reason"] if last["code"] == "fail" else st[k]["verdicts"][last["attempt"]]["reason"]
            lines.append(f"- frame {k}: {why}")
        name = f"writer-retry-request-{len(requests['writer'])}.txt"
        write_text(os.path.join(w, name), writer_text(w, REWRITE + "\n".join(lines) + "\n"))
        append_jsonl(log_path(w), {"event": "request", "kind": "writer", "name": name, "frames": rewrite})
    print(f"frames for the checker: {len(waiting)}\nframes for a rewrite: {len(rewrite)}")


def cmd_frames_verdicts(a):
    w = a.workdir
    st, requests, answered = frames_state(w)
    need(a.request in requests["checker"] and a.request not in answered, f"{a.request} is not an open checker request")
    given = requests["checker"][a.request]
    run = record_request(a, "checker", a.request, read_text(os.path.join(w, a.request)), "checker", set(given))
    if run is None:
        return 3
    gpath = os.path.join(w, "glosses.json")
    glosses = read_json(gpath) if os.path.exists(gpath) else {}
    for x in sorted(answer_of(run), key=lambda x: x["frame"]):
        attempt = len(st[x["frame"]]["codes"])
        append_jsonl(log_path(w), {"event": "verdict", "frame": x["frame"], "attempt": attempt, "verdict": x["verdict"],
                                   "reason": x["reason"], "request": a.request})
        glosses.setdefault(str(x["frame"]), []).append({"attempt": attempt, "verdict": x["verdict"],
                                                        "reason": x["reason"], "gloss": x["gloss"]})
    write_json(gpath, glosses)
    st, _, _ = frames_state(w)
    print("valid\n" + "\n".join(f"frames {s}: {sum(status(st[k]) == s for k in range(4))}"
                                for s in ("kept", "rewrite", "dropped-checker")))


def cmd_frames_strike(a):
    need(a.frame in range(4), "a frame is 0 to 3")
    need(not os.path.exists(os.path.join(a.workdir, "frames-kept.json")), "the frames are already closed")
    append_jsonl(log_path(a.workdir), {"event": "strike", "frame": a.frame})
    print("struck: 1")


def cmd_frames_finish(a):
    w = a.workdir
    st, requests, answered = frames_state(w)
    states = {k: status(st[k]) for k in range(4)}
    need(all(s in ("kept", "dropped-code", "dropped-checker", "struck") for s in states.values()),
         "a frame is still waiting or needs a rewrite")
    rows = [r for r in read_jsonl(ledger_path(w)) if r["purpose"] in ("writer", "checker")]
    files = request_files(w, "writer-request.txt", "writer-retry-request-*.txt", "checker-request-*.txt")
    account(w, a.transcripts, rows, set(files.values()))
    for r in rows:
        need(read_run(transcript(a.transcripts, r["agent_id"]))["first"] == files.get(r["request"]),
             "a writer or checker transcript's first message is not its request")
    if states[0] != "kept":
        print("null: frame 0 not kept")
        return 2
    kept = [k for k in range(4) if states[k] == "kept"]
    if kept == [0]:
        print("null: no longer frame kept")
        return 2
    shas = {}
    for k in kept:
        path = os.path.join(w, f"frame-{k}.txt")
        write_text(path, st[k]["codes"][-1]["text"])
        shas[str(k)] = ct.file_sha(path)
        print(f"frame-{k}-sha256: {shas[str(k)]}")
    write_json(os.path.join(w, "frames-kept.json"), {"kept": kept, "sha256": shas})
    count = {s: sum(v == s for v in states.values()) for s in ("kept", "dropped-code", "dropped-checker", "struck")}
    print("\n".join(f"frames {s}: {n}" for s, n in count.items()))
    print(f"writer requests: {len(requests['writer'])}\nchecker requests: {len(requests['checker'])}")
    print(f"void runs: {sum(r['status'] == 'void' for r in rows)}")


# ----------------------------------------------------------------------------- rounds, runs, score (17.5-17.7)
def scores(w):
    path = os.path.join(w, "scores.json")
    return read_json(path) if os.path.exists(path) else {}


def kept_frames(w):
    path = os.path.join(w, "frames-kept.json")
    need(os.path.exists(path), "the frames are not closed (frames finish)")
    return read_json(path)["kept"]


def check_order(w, k):
    """17.7: frame 0 first; a longer frame only after frame 0 was caught and every earlier kept longer frame failed;
    nothing after a longer frame passed."""
    kept, sc = kept_frames(w), scores(w)
    need(k in kept, f"frame {k} is not kept")
    need(not any(sc.get(str(j), {}).get("verdict") == PASS_VERDICT for j in kept if j > 0 and j != k),
         "a longer frame has passed: no other frame is judged")
    if k > 0:
        need(sc.get("0", {}).get("verdict") == CAUGHT, "frame 0 was not scored caught")
        need(all(sc.get(str(j), {}).get("verdict") == LONG_VERDICT for j in kept if 0 < j < k),
             "an earlier kept longer frame was not scored as failing")


def check_record(w):
    """17.8.2: the record before the first judge call, against the files and the code's own findings."""
    labels()
    inputs = read_json(os.path.join(w, "inputs.json"))
    topics_record(w, inputs["verdicts"]["path"])
    expect("seed-commit", seed_commit(inputs["repo"]))
    expect("drawn-sha256", ct.file_sha(os.path.join(w, "drawn-ids.txt")))
    for n, item in enumerate(inputs["items"], 1):
        expect(f"pool-file-{n}-sha256", ct.file_sha(item["path"]))
    need(ct.registered("pool-count") == str(POOL_N) and len(read_json(os.path.join(w, "pool.json"))) == POOL_N,
         "pool-count is not 90 and the pool's")
    kept = kept_frames(w)
    for k in kept:
        expect(f"frame-{k}-sha256", ct.file_sha(os.path.join(w, f"frame-{k}.txt")))
    expect("judge-model", JUDGE_MODEL)
    expect("judge-effort", JUDGE_EFFORT)
    expect("threshold", threshold())
    need(os.path.isfile(os.path.join(w, "dry-instructions.json")), "the dry runs have no baseline")


def cmd_rounds(a):
    w = a.workdir
    check_record(w)
    check_order(w, a.frame)
    frame = read_text(os.path.join(w, f"frame-{a.frame}.txt"))
    clue = {p["id"]: p["clue"] for p in read_json(os.path.join(w, "pool.json"))}
    out = []
    for r in read_json(os.path.join(w, "rounds.json")):
        qs = [clue[i] for i in r["ids"]]
        qs.insert(r["pos"], ct.fill(frame, r["topic"]))
        out.append({"round": r["round"], "prompt": put(read_text(os.path.join(w, "judge-prompt.txt")),
                                                       questions=numbered(qs))})
    write_json(os.path.join(w, f"prompts-frame{a.frame}.json"), out)
    print(f"rounds: {len(out)}")


def judge_rows(w, k, n=None):
    return [r for r in read_jsonl(ledger_path(w))
            if r["purpose"] == "judge" and r["frame"] == k and (n is None or r["run"] == n)]


def cmd_run(a):
    w = a.workdir
    need(a.attempt in (1, 2) and a.round in range(ROUNDS) and a.run >= 1, "attempt is 1 or 2, round 0-19, run 1 on")
    if a.run > 1:
        need(any(s["frame"] == a.frame and s["run"] == a.run - 1 for s in read_jsonl(os.path.join(w, "stops.jsonl"))),
             "a frame's rounds are run again only after a stop the script found in the run before")
    same = [r for r in judge_rows(w, a.frame, a.run) if r["round"] == a.round]
    need(all(r["attempt"] != a.attempt for r in same), "this attempt of this round is already recorded")
    if a.attempt == 2:
        need(any(r["attempt"] == 1 and r["status"] == "void" for r in same), "attempt 2 only after a void attempt 1")
    prompts = read_json(os.path.join(w, f"prompts-frame{a.frame}.json"))
    row, run = record(a, "judge", f"prompts-frame{a.frame}.json", prompts[a.round]["prompt"], "judge",
                      frame=a.frame, round=a.round, attempt=a.attempt, run=a.run)
    if row["status"] == "void":
        print(f"void: {row['reason']}")
        return 3
    print(f"valid pick {answer_of(run)['pick']}")


def cmd_score(a):
    w, k = a.workdir, a.frame
    t = threshold()
    kept = kept_frames(w)
    pos = [r["pos"] for r in read_json(os.path.join(w, "rounds.json"))]
    prompts = read_json(os.path.join(w, f"prompts-frame{k}.json"))
    rows = judge_rows(w, k, a.run)
    picks = {}
    for row in rows:
        run, reason = rescore(w, row, a.transcripts, prompts[row["round"]]["prompt"], "judge")
        picks[(row["round"], row["attempt"])] = None if reason else answer_of(run)["pick"]
    account(w, a.transcripts, judge_rows(w, k), all_prompts(w))
    first_void = [r for r in range(ROUNDS) if (r, 1) in picks and picks[(r, 1)] is None]
    found(len(first_void) <= 3, "void infrastructure: more than 3 rounds void at the first attempt")
    todo = [r for r in range(ROUNDS) if (r, 1) not in picks or (picks[(r, 1)] is None and (r, 2) not in picks)]
    if todo:
        print(f"rounds to run: {len(todo)} ({', '.join(map(str, todo))})")
        return 3
    hits = double = 0
    for r in range(ROUNDS):
        pick = picks[(r, 1)] if picks[(r, 1)] is not None else picks[(r, 2)]
        if pick is None:
            double += 1
            hits += k > 0               # 17.5.3: a second void counts against what the frame is for
        else:
            hits += pick - 1 == pos[r]
    if k == 0:
        verdict = CAUGHT if hits >= t else NOT_CAUGHT
    else:
        verdict = LONG_VERDICT if hits >= t else PASS_VERDICT
    ledger_sha = ct.file_sha(ledger_path(w))
    sc = scores(w)
    entry = {"run": a.run, "H": hits, "verdict": verdict, "ledger_sha256": ledger_sha}
    if str(k) in sc:
        sc[str(k)].setdefault("later", []).append(entry)     # 17.7.5: the first scored run decides
    else:
        sc[str(k)] = entry
    write_json(os.path.join(w, "scores.json"), sc)
    print(f"rounds: {ROUNDS}\nvoid first attempts: {len(first_void)}\ndouble voids: {double}\nH: {hits}")
    print(f"ledger-sha256: {ledger_sha}\nverdict: {verdict}")
    decided = sc[str(k)]
    if decided is not entry:
        print(f"decision stands from run {decided['run']}: {decided['verdict']}")
    elif verdict == PASS_VERDICT:
        print(f"frame test passed: judge {JUDGE_MODEL}, {ROUNDS} rounds, {hits} hits (frame 0: {sc['0']['H']})")
    if k > 0 and all(sc.get(str(j), {}).get("verdict") == LONG_VERDICT for j in kept if j > 0):
        print("null: no longer frame passed")


def cmd_template(a):
    labels()
    sc, kept = scores(a.workdir), kept_frames(a.workdir)
    passed = next((j for j in sorted(kept) if j > 0 and sc.get(str(j), {}).get("verdict") == PASS_VERDICT), None)
    if passed is not None:
        need(not a.null_route, "a longer frame passed: there is no null route")
        expected = ct.registered(f"frame-{passed}-sha256")
    else:
        need(a.null_route and 0 in kept, "no longer frame passed, and the null route was not given")
        expected = ct.registered("frame-0-sha256")
    need(ct.file_sha(a.file) == ct.registered("template-sha256").lower(), "the template file is not template-sha256")
    need(ct.registered("template-sha256").lower() == expected.lower(),
         "template-sha256 is not the frame-N-sha256 of the chosen frame")
    print(f"template-sha256: {ct.file_sha(a.file)}")


def cmd_labels(a):
    print(f"labels: {labels()}")


# ----------------------------------------------------------------------------- command line
def parser():
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = p.add_subparsers(dest="cmd", required=True)
    base = argparse.ArgumentParser(add_help=False)
    base.add_argument("--workdir", required=True)
    runp = argparse.ArgumentParser(add_help=False)
    for name in ("--agent-id", "--reply-file", "--transcripts"):
        runp.add_argument(name, required=True)
    sub.add_parser("topics", parents=[base]).add_argument("--verdicts", required=True)
    sub.add_parser("labels", parents=[base])
    pool = sub.add_parser("pool", parents=[base])
    pool.add_argument("--items", nargs=4, required=True)
    pool.add_argument("--verdicts", required=True)
    pool.add_argument("--repo", required=True)
    sub.add_parser("dry-prompts", parents=[base])
    sub.add_parser("dry-record", parents=[base, runp]).add_argument("--role", choices=ROLES, required=True)
    sub.add_parser("dry-score", parents=[base]).add_argument("--transcripts", required=True)
    fr = sub.add_parser("frames").add_subparsers(dest="fcmd", required=True)
    for name in ("add", "verdicts"):
        fr.add_parser(name, parents=[base, runp]).add_argument("--request", required=True)
    fr.add_parser("lists", parents=[base])
    fr.add_parser("strike", parents=[base]).add_argument("--frame", type=int, required=True)
    fr.add_parser("finish", parents=[base]).add_argument("--transcripts", required=True)
    sub.add_parser("rounds", parents=[base]).add_argument("--frame", type=int, required=True)
    r = sub.add_parser("run", parents=[base, runp])
    for name in ("--frame", "--round", "--attempt", "--run"):
        r.add_argument(name, type=int, required=True)
    s = sub.add_parser("score", parents=[base])
    s.add_argument("--frame", type=int, required=True)
    s.add_argument("--run", type=int, required=True)
    s.add_argument("--transcripts", required=True)
    s.add_argument("--final-stop", action="store_true")
    t = sub.add_parser("template", parents=[base])
    t.add_argument("--file", required=True)
    t.add_argument("--null-route", action="store_true")
    return p


COMMANDS = {"topics": cmd_topics, "labels": cmd_labels, "pool": cmd_pool, "dry-prompts": cmd_dry_prompts,
            "dry-record": cmd_dry_record, "dry-score": cmd_dry_score, "rounds": cmd_rounds, "run": cmd_run,
            "score": cmd_score, "template": cmd_template, "add": cmd_frames_add, "lists": cmd_frames_lists,
            "verdicts": cmd_frames_verdicts, "strike": cmd_frames_strike, "finish": cmd_frames_finish}


def main(argv=None):
    a = parser().parse_args(argv)
    guarded = False
    try:
        ct.guard_workdir(a.workdir)
        guarded = True
        a.workdir = os.path.realpath(a.workdir)
        return COMMANDS[a.fcmd if a.cmd == "frames" else a.cmd](a) or 0
    except ct.Stop as e:
        print(f"stop: {e}")
        if guarded and a.cmd in ("run", "score") and isinstance(e, Found):
            append_jsonl(os.path.join(a.workdir, "stops.jsonl"), {"frame": a.frame, "run": a.run, "cause": str(e),
                                                                  "time": now()})
        if getattr(a, "final_stop", False):
            print("null: stopped")
        return 2


if __name__ == "__main__":
    sys.exit(main())
