#!/usr/bin/env python3
"""messages.py: count cross-session messages without storing any of their text.

Why: the owner wants to see whether sessions coordinate with each other, between whom, and
whether sends work, not to read the messages (coordination.md#counting-messages).

Commands:
  hook    run by Claude Code on send_message (PreToolUse, PostToolUse, PostToolUseFailure,
          PermissionDenied): reads the hook's JSON on stdin and appends one line, ids and
          codes only, to this session's spool file. Prints nothing, always exits 0.
  stats   reads exported `messages`, `sessions` and `decisions` rows and writes the
          dashboard's data file (one JSON array, each row tagged with its `table`), plus a
          batch for one decision card when new tags need the owner's look.

The spool is turned into `messages` rows by board.py register/checkin (`flush` below), as a
separate batch like the beat prune, so a refused message write never costs a heartbeat.

Stdlib only. Python 3.9+.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from board import KIT_VERSION, decide, git, load_rows, now_iso, session_key, slugify, strict_slug  # noqa: E402

# The first batch of tags, chosen with the owner on 2026-10-21. Any other tag is "new" until the
# owner answers a card that lists it (stats writes that card).
SEED_TAGS = ("merge", "handover", "review", "status", "blocked", "clash", "delegate", "test")
# One or two lowercase words of 3-10 letters: no digits, ids, URLs or sentences (the debate of
# 2026-10-21: a tag is read by later sessions, so it must be too short to carry an instruction).
TAG_RE = re.compile(r"[a-z]{3,10}(?:-[a-z]{3,10})?")
TOKEN_RE = re.compile(r"\[t:([^\]\n]{0,32})\]")
RESULTS = ("delivered", "not_found", "unverified", "device", "refused", "error", "attempted")
RANK = {"delivered": 3, "not_found": 2, "unverified": 2, "device": 2, "refused": 2, "error": 2, "attempted": 1}
SPOOL_MAX = 2_000_000          # bytes read from one spool; a runaway file is cut, not loaded
TOOL = "mcp__claude-code-remote__send_message"
FAIL_WORDS = ("not found", "not_found", "could not be verified", "trusted device", "untrusted_device", "denied", "permission", "error", "failed")
CARD_PREFIX = "d-msg-tags-"
BATCH_MAX = 50                 # the store's batch limit (platform.md); the rest stays spooled
SETTLE_S = 600                 # a bare attempt this young may still get its result: not written yet


def tag_of(message) -> str:
    """The tag in a leading `[t:<tag>]`, else 'untagged'. Position 0 only, so a token quoted
    later in a message (from a message it answers) is never taken for this one's."""
    m = TOKEN_RE.match(message) if isinstance(message, str) else None
    t = m.group(1) if m else None
    return t if t and TAG_RE.fullmatch(t) else "untagged"


def result_of(event: str, payload) -> str:
    if event == "PreToolUse":
        return "attempted"
    if event == "PermissionDenied":
        return "refused"
    text = payload.lower() if isinstance(payload, str) else json.dumps(payload).lower()
    if event == "PostToolUse" and (re.search(r"status\W{1,6}delivered", text) or not any(w in text for w in FAIL_WORDS)):
        # PostToolUse fired only for delivered sends in the one transcript checked (platform.md,
        # Hooks), so a response without a failure word counts as delivered whatever its shape.
        return "delivered"
    if "not found" in text or "not_found" in text:
        return "not_found"
    if "trusted device" in text or "untrusted_device" in text:
        return "device"
    if "could not be verified" in text:
        # A mis-cased id got this, not "not found", on 2026-10-21 (ship check, session 01No2F1V).
        return "unverified"
    if "denied" in text or "permission" in text:
        return "refused"
    return "error"


def session_doc(sid) -> str:
    """A session id as the board's doc ids write it: session_X / cse_X -> cse-x, lowercased,
    so a send to a mis-cased id still joins its session's row (the result says it failed)."""
    s = sid.strip() if isinstance(sid, str) else ""
    for p in ("session_", "cse_", "cse-"):
        if s.lower().startswith(p):
            s = "cse-" + s[len(p):]
            break
    return strict_slug(s, 64) or "unknown"


def spool_dir(env=os.environ) -> Path:
    return Path(env.get("BOARD_SPOOL_DIR") or Path.home() / ".claude" / "board-pattern" / "spool")


def spool_path(env=os.environ) -> Path | None:
    key = session_key(env)
    return spool_dir(env) / f"{slugify(key, 64)}.jsonl" if key else None


def hook(stdin_text: str, env=os.environ) -> None:
    """Append one line for a send_message event. Never raises (a hook must not break a send)."""
    try:
        ev = json.loads(stdin_text)
        ti = ev.get("tool_input") or {}
        if ev.get("tool_name") != TOOL or not isinstance(ti, dict):
            return
        event = ev.get("hook_event_name")
        if event not in ("PreToolUse", "PostToolUse", "PostToolUseFailure", "PermissionDenied"):
            return
        tid = strict_slug(str(ev.get("tool_use_id") or ""), 60)
        path = spool_path(env)
        if not tid or not path:
            return
        payload = ev.get("tool_response") if event == "PostToolUse" else ev.get("error", ev.get("reason"))
        line = {"id": tid, "ev": event, "to": session_doc(ti.get("session_id")), "tag": tag_of(ti.get("message")),
                "result": result_of(event, payload), "ts": now_iso()}
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as f:
            _lock(f)
            f.write(json.dumps(line) + "\n")
    except Exception:  # noqa: BLE001
        pass


def _lock(f) -> None:
    """Hold the spool while writing, so a check-in rewriting it never drops a line a hook is
    appending (no-op where fcntl is missing, as on Windows)."""
    try:
        import fcntl
        fcntl.flock(f.fileno(), fcntl.LOCK_EX)
    except (ImportError, OSError):
        pass


def _read_spool(path: Path) -> list[dict]:
    with path.open("rb") as f:
        raw = f.read(SPOOL_MAX).decode("utf-8", "replace")
    out = []
    for ln in raw.splitlines():
        try:
            d = json.loads(ln)
        except ValueError:
            continue
        if isinstance(d, dict) and isinstance(d.get("id"), str) and d.get("result") in RANK:
            out.append(d)
    return out


def _age_s(ts) -> float | None:
    try:
        then = datetime.strptime(str(ts)[:19], "%Y-%m-%dT%H:%M:%S").replace(tzinfo=timezone.utc)
    except ValueError:
        return None
    return (datetime.now(timezone.utc) - then).total_seconds()


def flush(doc_id: str, stored=(), env=os.environ) -> dict:
    """`messages` rows for this session's spooled sends not yet in the store, one per send: the
    best result its events reached (delivered over a failure over a bare attempt), at the first
    time seen. `stored` is the set of message doc ids an export of this session's rows shows;
    those sends are dropped from the spool (the store has them), so a refused or unsent batch
    loses nothing: its sends stay spooled until an export shows them stored. A bare attempt
    younger than SETTLE_S is held back, since its result may still come (a row is written
    once). At most BATCH_MAX rows go out; the rest wait for the next check-in."""
    path = spool_path(env)
    if not path or not path.is_file():
        return {"writes": [], "spool": str(path) if path else None}
    by_id: dict[str, dict] = {}
    for d in _read_spool(path):
        cur = by_id.get(d["id"])
        if cur is None:
            by_id[d["id"]] = dict(d)
        elif RANK[d["result"]] >= RANK[cur["result"]]:
            by_id[d["id"]] = {**d, "ts": cur["ts"]}    # keep the first time seen
    stored = set(stored)
    writes, held, waiting = [], 0, 0
    for tid, d in by_id.items():
        did = f"m-{tid}"[:64]
        if did in stored:
            continue
        age = _age_s(d.get("ts"))
        if d["result"] == "attempted" and age is not None and age < SETTLE_S:   # no readable time: old
            held += 1
            continue
        if len(writes) >= BATCH_MAX:
            waiting += 1
            continue
        writes.append({"op": "set", "collection": "messages", "doc_id": did,
                       "data": {"from": doc_id, "to": session_doc(d.get("to")), "ts": str(d.get("ts", ""))[:20],
                                "tag": d.get("tag") if TAG_RE.fullmatch(str(d.get("tag"))) else "untagged",
                                "result": d["result"], "src": "hook", "kit": KIT_VERSION}})
    if stored:
        _drop_stored(path, stored)
    return {"writes": writes, "spool": str(path), "already_stored": len([t for t in by_id if f"m-{t}"[:64] in stored]),
            "held_back": held, "next_time": waiting}


def _drop_stored(path: Path, stored: set) -> None:
    """Rewrite the spool without the sends the store already holds, under the hook's lock."""
    with path.open("r+", encoding="utf-8", errors="replace") as f:
        _lock(f)
        keep = [ln for ln in f.read().splitlines(keepends=True)
                if not _stored_line(ln, stored)]
        f.seek(0)
        f.writelines(keep)
        f.truncate()


def _stored_line(ln: str, stored: set) -> bool:
    try:
        d = json.loads(ln)
    except ValueError:
        return False
    return isinstance(d, dict) and isinstance(d.get("id"), str) and f"m-{d['id']}"[:64] in stored


# ---------- stats ----------

def _day(ts) -> str | None:
    s = str(ts or "")[:10]
    try:
        datetime.strptime(s, "%Y-%m-%d")
    except ValueError:
        return None
    return s


def _week(day: str) -> str:
    y, w, _ = datetime.strptime(day, "%Y-%m-%d").isocalendar()
    return f"{y}-W{w:02d}"


def _kit_at_least(v, want=(0, 4, 17)) -> bool:
    m = re.fullmatch(r"(\d+)\.(\d+)\.(\d+)", str(v or ""))
    return bool(m) and tuple(int(x) for x in m.groups()) >= want


def stats(messages_export: str, sessions_export: str, decisions_export: str | None, cwd: str, env=os.environ) -> dict:
    skipped: list = []
    msgs = [r["data"] for r in load_rows(messages_export, skipped)]
    sessions = load_rows(sessions_export, skipped)
    decs = load_rows(decisions_export, skipped) if decisions_export else []
    out: list[dict] = []
    # Per day: how many sends, and how each ended.
    per_day: dict[str, Counter] = defaultdict(Counter)
    weekly: dict[str, dict] = defaultdict(lambda: {"sends": 0, "senders": set(), "pairs": set()})
    pairs: Counter = Counter()
    tags: Counter = Counter()
    for m in msgs:
        day = _day(m.get("ts"))
        res = m.get("result") if m.get("result") in RESULTS else "error"
        if not day:
            continue
        per_day[day][res] += 1
        w = weekly[_week(day)]
        w["sends"] += 1
        w["senders"].add(str(m.get("from")))
        w["pairs"].add((str(m.get("from")), str(m.get("to"))))
        pairs[(str(m.get("from")), str(m.get("to")))] += 1
        tags[m.get("tag") if TAG_RE.fullmatch(str(m.get("tag"))) else "untagged"] += 1
    for day in sorted(per_day):
        c = per_day[day]
        out.append({"table": "daily", "day": day, "delivered": c["delivered"],
                    "failed": sum(c[r] for r in ("not_found", "unverified", "device", "refused", "error")),
                    "not_found": c["not_found"], "unverified": c["unverified"], "device": c["device"], "refused": c["refused"],
                    "error": c["error"], "unconfirmed": c["attempted"]})
    for wk in sorted(weekly):
        w = weekly[wk]
        sends_by = Counter(str(m.get("from")) for m in msgs if _day(m.get("ts")) and _week(_day(m.get("ts"))) == wk)
        out.append({"table": "weekly", "week": wk, "sends": w["sends"], "senders": len(w["senders"]),
                    "pairs": len(w["pairs"]),
                    "top_sender_share": round(max(sends_by.values()) / w["sends"], 2) if w["sends"] else 0})
    for (f, t), n in pairs.most_common(20):
        out.append({"table": "pairs", "pair": f"{f[:12]} > {t[:12]}", "from": f, "to": t, "sends": n})
    # Tags: new = not a seed and not listed on an answered card.
    acked, carded = set(), set()
    open_card = None
    for d in decs:
        if not d["id"].startswith(CARD_PREFIX):
            continue
        tags_field = d["data"].get("tags")
        listed = {t for t in tags_field if isinstance(t, str)} if isinstance(tags_field, list) else set()
        carded |= listed
        dd = d["data"]
        if isinstance(dd.get("verdict"), dict) or isinstance(dd.get("closed"), dict):
            acked |= listed
        else:
            open_card = d["id"]
    new = sorted(t for t in tags if t not in SEED_TAGS and t != "untagged" and t not in acked)
    for t, n in sorted(tags.items(), key=lambda x: (-x[1], x[0])):
        out.append({"table": "tags", "tag": t, "sends": n,
                    "kind": "seed" if t in SEED_TAGS else "untagged" if t == "untagged" else "new" if t in new else "read"})
    # Coverage: is logging alive, and how much of the board can it see?
    hook_rows = [m for m in msgs if m.get("src") == "hook"]
    newest = max((str(m.get("ts")) for m in hook_rows), default="")
    out.append({"table": "coverage", "sessions": len(sessions),
                "sessions_with_hook_kit": sum(1 for s in sessions if _kit_at_least(s["data"].get("kit"))),
                "senders_logged_by_hook": len({m.get("from") for m in hook_rows}),
                "rows_hook": len(hook_rows), "rows_backfill": sum(1 for m in msgs if m.get("src") == "backfill"),
                "newest_hook_row": newest or None, "new_tags": len(new),
                "generated_at": now_iso(), "commit": git(["rev-parse", "--short", "HEAD"], cwd) or None,
                "kit": KIT_VERSION})
    res = {"rows": out, "new_tags": new, "skipped_files": skipped or None, "card": []}
    pending = [t for t in new if t not in carded]
    if pending and not open_card:
        cid = CARD_PREFIX + hashlib.sha256(",".join(pending).encode()).hexdigest()[:8]
        card = decide(cwd, cid, "New message tags appeared. Do they read as plain topic labels?",
                      "Sessions tag their messages with one or two words. These tags are new: "
                      + ", ".join(pending) + ". Answering this card marks exactly these as read; the dashboard "
                      "shows them as new until then.",
                      ["read:Read; they are plain labels", "odd:One looks wrong; tell the sessions"],
                      recommended=None, kind="msg-tags", env=env)
        if card.get("writes"):
            card["writes"][0]["data"]["tags"] = pending
            res["card"] = card["writes"]
        else:
            res["card_error"] = card.get("error")
    elif pending:
        res["card_note"] = f"{len(pending)} new tag(s) wait for {open_card} to be answered first"
    return res


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="messages.py", description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("hook")
    s = sub.add_parser("stats")
    s.add_argument("--messages-export", required=True)
    s.add_argument("--sessions-export", required=True)
    s.add_argument("--decisions-export")
    s.add_argument("--out", required=True, help="the dashboard's data file (a JSON array)")
    s.add_argument("--card-out", help="write the new-tags card batch here (send it with ArtifactData batch)")
    a = ap.parse_args(argv)
    if a.cmd == "hook":
        try:
            hook(sys.stdin.read())
        except Exception:  # noqa: BLE001
            pass
        return 0
    from board import out as print_json, to_batch
    try:
        res = stats(a.messages_export, a.sessions_export, a.decisions_export, os.getcwd())
        Path(a.out).write_text(json.dumps(res["rows"], indent=1), encoding="utf-8")
        summary = {k: v for k, v in res.items() if k != "rows"}
        summary["rows_written"] = len(res["rows"])
        if a.card_out:
            summary["card_batch"] = to_batch(res["card"], a.card_out)
        print_json(summary)
    except OSError as e:
        sys.stderr.write(f"messages.py: {type(e).__name__}: {e}\n")
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
