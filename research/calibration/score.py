#!/usr/bin/env python3
"""Score calibration run 1 mechanically, by the rules in PREREG.md. Reads results/raw.json."""
import json
import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import keys  # noqa: E402

HERE = pathlib.Path(__file__).resolve().parent
VENUES = {
    1: ["考古學報", "考古学报", "kaoguxuebao"],
    2: ["周易研究", "zhouyiyanjiu"],
    3: ["歷史語言研究所集刊", "历史语言研究所集刊", "bihp", "bulletinoftheinstituteofhistoryandphilology"],
    4: ["bulletinofthejaotsung-iacademyofsinology", "饒宗頤國學院院刊", "饶宗颐国学院院刊"],
}
YEARS = {1: 1980, 2: 2014, 3: 2006, 4: 2018, 5: 2021}


def norm(s):
    return re.sub(r"\s+", "", str(s or "")).lower()


def parse(content):
    m = re.search(r"\{.*\}", content or "", re.S)
    try:
        return json.loads(m.group()) if m else None
    except json.JSONDecodeError:
        return None


def year_of(v):
    m = re.search(r"(19|20)\d\d", str(v or ""))
    return int(m.group()) if m else None


def title_probe(title):
    t = str(title).strip()
    if re.search(r"[㐀-鿿]", t):
        return re.sub(r"[\s《》〈〉「」“”\"']", "", t)[:8]
    return " ".join(t.split()[:4]).lower()


def found(title, log):
    res = keys.deepseek_search(title, count=5)
    log.append({"query": title, "response": res})
    probe = title_probe(title)
    for hit in res.get("results", []):
        hay = (hit.get("title", "") + hit.get("snippet", "") + hit.get("summary", ""))
        hay = re.sub(r"[\s《》〈〉「」“”\"']", "", hay) if re.search(r"[㐀-鿿]", probe) else hay.lower()
        if probe in hay:
            return True
    return False


def score(row, log):
    r = row["response"]
    if "error" in r:
        return "void", None
    rec = parse(r["choices"][0]["message"].get("content"))
    if rec is None or "unknown" in rec or (not rec.get("venue") and not rec.get("year")):
        return "dont-know", rec
    q = row["q"]
    year_ok = year_of(rec.get("year")) == YEARS[q]
    if q == 5:
        venue_ok = any(k in str(rec.get("title", "")) for k in ("数字卦", "數字卦"))
    else:
        venue_ok = any(k in norm(rec.get("venue")) for k in VENUES[q])
    if venue_ok and year_ok:
        return "confirmed", rec
    if rec.get("title") and not found(rec["title"], log):
        return "fabricated", rec
    return "wrong", rec


def main():
    name = sys.argv[1] if len(sys.argv) > 1 else "raw.json"
    rows = json.loads((HERE / "results" / name).read_text(encoding="utf-8"))
    log, table = [], {}
    for row in rows:
        verdict, rec = score(row, log)
        row["verdict"], row["parsed"] = verdict, rec
        table.setdefault(row["arm"], []).append((row["q"], verdict))
    (HERE / "results" / name.replace("raw", "scored")).write_text(json.dumps(rows, ensure_ascii=False, indent=1), encoding="utf-8")
    (HERE / "results" / name.replace("raw", "search-log")).write_text(json.dumps(log, ensure_ascii=False, indent=1), encoding="utf-8")
    for arm, vs in table.items():
        given = [v for _, v in vs if v not in ("dont-know", "void")]
        n = len(given)
        conf, fab = given.count("confirmed"), given.count("fabricated")
        stays = n >= 3 and conf / n >= 0.6 and fab / n <= 0.2 if n else False
        cost = sum((r.get("generation") or {}).get("total_cost") or 0 for r in rows if r["arm"] == arm)
        print(f"{arm}: {sorted(vs)} | leads {n}, confirmed {conf}, fabricated {fab} | "
              f"{'STAYS' if stays else 'DROPPED'} | cost ${cost:.4f}")


if __name__ == "__main__":
    main()
