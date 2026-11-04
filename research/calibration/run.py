#!/usr/bin/env python3
"""Calibration run 1 (PREREG.md beside this file): ask each arm the five questions cold.

Usage: python3 research/calibration/run.py   (writes research/calibration/results/raw-*.json)
"""
import json
import pathlib
import sys
import time
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import keys  # noqa: E402

HERE = pathlib.Path(__file__).resolve().parent
ARMS = ["deepseek/deepseek-v4.1-flash-1017:exacto", "deepseek/deepseek-v4-pro:exacto", "moonshotai/kimi-k3.1-pro:exacto"]
QUESTIONS = [
    "Zhang Zhenglang's article that first identified numerical sequences on early Zhou bronze inscriptions as Yi hexagrams.",
    "Jia Lianxiang's article on the number systems (用数体系) of excavated numerical hexagrams.",
    "Li Zongkun's article arguing that numerical diagrams and yin-yang line hexagrams are two separate systems.",
    "Adam C. Schwartz's English-language article on numbers and hexagram pictures in excavated texts, published in a Hong Kong sinology journal.",
    "Jia Lianxiang's book collecting and annotating excavated numerical-hexagram documents.",
]
PROMPT = """Give the bibliographic record of this work, from memory:

{q}

Answer with one JSON object and nothing else, with these keys: "author", "title" (in the original language), "venue" (journal or, for a book, publisher), "year", "issue", "pages", "url" (where it is online), "search_terms" (Chinese terms to find it). Use null for anything you do not know. If you do not know the work, answer {{"unknown": "不知道"}}. Saying you do not know is a good answer; an invented record is the worst one."""


def ask(arm, qi, effort="max"):
    body = {"model": arm, "messages": [{"role": "user", "content": PROMPT.format(q=QUESTIONS[qi])}],
            "provider": {"zdr": True}, "reasoning": {"effort": effort}, "max_tokens": 16000}
    t = time.time()
    r = keys.openrouter_chat(body)
    if "error" in r and effort == "max" and "effort" in json.dumps(r["error"]).lower():
        return ask(arm, qi, "xhigh")
    return {"arm": arm, "q": qi + 1, "effort": effort, "seconds": round(time.time() - t, 1), "request": body, "response": r}


def main():
    out = HERE / "results"
    out.mkdir(exist_ok=True)
    jobs = [(a, i) for a in ARMS for i in range(len(QUESTIONS))]
    with ThreadPoolExecutor(8) as ex:
        rows = list(ex.map(lambda j: ask(*j), jobs))
    for row in rows:
        gid = row["response"].get("id")
        row["generation_id"] = gid
        if gid:
            time.sleep(1)
            row["generation"] = keys.openrouter_generation(gid).get("data")
    (out / "raw.json").write_text(json.dumps(rows, ensure_ascii=False, indent=1), encoding="utf-8")
    for row in rows:
        r = row["response"]
        print(row["arm"], row["q"], row["effort"], "ERROR" if "error" in r else "ok", row.get("generation_id"))


if __name__ == "__main__":
    main()
