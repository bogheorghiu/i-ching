"""Build seed rows for build_keys.py's seeded intake (stage s) from a CASS yearly table of contents.

Why: the seeds so far came from the owner's Kimi runs. A CASS yearly TOC lists every article of a year
by issue, and CNKI article URLs follow CJFDTotal-<journal code><year><issue:02><seq:03>.htm, so the
pairs can be found without a model: probe the CNKI ids of each issue in order and keep a page whose
heading title equals a TOC entry of that issue (after norm). The output has the same shape as the Kimi
seed files; stage s and the parsers in build_keys.py then do all checking, so nothing here is trusted.

Usage: python3 -I seed_from_toc.py --toc URL [--toc URL ...] --workdir DIR --out seeds.jsonl
       [--journal 周易研究 --code ZYJY --years 2019,2020 --max-seq 30]
"""
import argparse
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import build_keys as bk  # noqa: E402

ISSUE_HEAD = r"《{j}》\s*(\d{{4}})\s*年\s*第\s*(\d+)\s*期"


def toc_sections(text, journal):
    """{(year, issue): [line, ...]} from a yearly TOC page's text."""
    out, cur = {}, None
    for ln in (x.strip() for x in text.splitlines()):
        m = re.search(ISSUE_HEAD.format(j=re.escape(journal)), ln)
        if m:
            cur = (int(m.group(1)), int(m.group(2)))
            out.setdefault(cur, [])
        elif cur and "/" in ln:
            out[cur].append(ln)
    return out


def entry_title(ln):
    return (ln.partition("//") if "//" in ln else ln.rpartition("/"))[0].strip()


def cnki_title(url):
    F = bk.ds_fetch(url, "seed: cnki id probe")
    if not F["ok"]:
        return None
    h1 = re.search(r"^#\s+(.+)$", F["text"], re.M)
    return h1.group(1).strip() if h1 else None


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--toc", action="append", required=True)
    p.add_argument("--workdir", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--journal", default="周易研究")
    p.add_argument("--code", default="ZYJY")
    p.add_argument("--years", default="", help="comma-separated; empty = every year on the pages")
    p.add_argument("--max-seq", type=int, default=30)
    a = p.parse_args()
    years = {int(y) for y in a.years.split(",") if y.strip()}
    bk.W = os.path.abspath(a.workdir)
    bk.SNAP = os.path.join(bk.W, "snapshots")
    os.makedirs(bk.SNAP, exist_ok=True)
    rows, misses_log = [], []
    for toc in a.toc:
        F = bk.ds_fetch(toc, "seed: institute toc")
        if not F["ok"]:
            print(f"[seed] TOC unfetchable: {toc}")
            continue
        for (year, issue), lines in sorted(toc_sections(F["text"], a.journal).items()):
            if years and year not in years:
                continue
            want = {bk.norm(entry_title(ln)): ln for ln in lines if entry_title(ln)}
            found, miss_run = 0, 0
            for seq in range(1, a.max_seq + 1):
                url = f"https://www.cnki.com.cn/Article/CJFDTotal-{a.code}{year}{issue:02d}{seq:03d}.htm"
                t = cnki_title(url)
                if t is None:
                    miss_run += 1
                    if miss_run >= 4 and seq > 5:
                        break
                    continue
                miss_run = 0
                ln = want.get(bk.norm(t))
                if ln is None:
                    misses_log.append({"cnki": url, "cnki_title": t, "year": year, "issue": issue})
                    continue
                rows.append({"journal": a.journal, "year": year, "issue": issue, "title": t,
                             "sources": [{"url": url, "site_type": "cnki", "fields_seen": {"title": t}},
                                         {"url": toc, "site_type": "institute_toc",
                                          "fields_seen": {"title": entry_title(ln), "toc_line": ln}}],
                             "seeded_by": "seed_from_toc.py"})
                found += 1
            print(f"[seed] {year}/{issue}: TOC entries {len(want)}, matched CNKI pages {found}")
    with open(a.out, "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    with open(a.out + ".unmatched.jsonl", "w", encoding="utf-8") as f:
        for r in misses_log:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"[seed] wrote {len(rows)} seed rows to {a.out} ({len(misses_log)} CNKI pages matched no TOC entry)")


if __name__ == "__main__":
    main()
