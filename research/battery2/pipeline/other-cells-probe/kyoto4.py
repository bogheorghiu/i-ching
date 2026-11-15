"""Kyoto OU parser, fixed for pass 4 (OTHER-CELLS-PASS4.md). Frozen before the pass-4 candidate draw."""
import re, unicodedata
HEADER = re.compile(r"[A-Z](\d{6}|\d{4}-\d{5})")
ARTICLE = re.compile(r"\d{8}")
def ou_parse(t):
    t = unicodedata.normalize("NFKC", t)
    arts, blk, art, last = [], {}, None, None
    for line in t.splitlines():
        s = line.strip()
        if not s or s.startswith("```"): continue
        if HEADER.fullmatch(s):
            blk, art, last = {}, None, None; continue
        if ARTICLE.fullmatch(s):
            art = {"j": blk.get("j"), "d": blk.get("d"), "t": None, "a": []}; arts.append(art); last = None; continue
        m = re.match(r"\$([A-Za-z])(.*)$", s)
        if m:
            k, v = m.group(1), m.group(2).strip()
            if art is None:
                if k in ("j", "d"): blk[k] = v
                last = None
            elif k == "t": art["t"] = v; last = "t"
            elif k in ("a", "A"): art["a"].append(v); last = "a"
            else: last = None
            continue
        if art is not None and last == "t": art["t"] += " " + s
        elif art is not None and last == "a" and art["a"]: art["a"][-1] += " " + s
    return arts
def strip_markup(x): return re.sub(r"<[^>]+>", "", x or "")
