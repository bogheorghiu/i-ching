"""Shared helpers for key building. Every network call is cached under snapshots/ and logged in calls.jsonl.
Snapshot = the raw tool response wrapped with url/query/route/date. Nothing here decides whether a key is right.
"""
import sys, os, json, time, hashlib, re, datetime, unicodedata
sys.path.insert(0, '../..')
import keys
from opencc import OpenCC

_t2s = OpenCC('t2s')
SNAP = 'snapshots'
os.makedirs(SNAP, exist_ok=True)
LOG = 'calls.jsonl'


def utcnow():
    return datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')


def sid(s):
    return hashlib.sha1(s.encode('utf-8')).hexdigest()[:10]


def _log(rec):
    with open(LOG, 'a', encoding='utf-8') as f:
        f.write(json.dumps(rec, ensure_ascii=False) + '\n')


def search(query, count=10, need_content=False, route='', force=False):
    fn = f"{SNAP}/search_{sid(query)}_{count}_{int(need_content)}.json"
    if os.path.exists(fn) and not force:
        return json.load(open(fn, encoding='utf-8'))
    raw = keys._post(f"{keys.DEEPSEEK}/search", "DEEPSEEK_API_KEY",
                     {"query": query, "count": count, "need_content": need_content})
    snap = {"kind": "search", "query": query, "count": count, "need_content": need_content,
            "route": route, "date": utcnow(), "raw": raw}
    json.dump(snap, open(fn, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    _log({"kind": "search", "query": query, "file": fn, "date": snap["date"]})
    return snap


def fetch(url, route='', force=False):
    fn = f"{SNAP}/fetch_{sid(url)}.json"
    if os.path.exists(fn) and not force:
        return json.load(open(fn, encoding='utf-8'))
    raw = keys._post(f"{keys.DEEPSEEK}/fetch", "DEEPSEEK_API_KEY", {"url": url})
    snap = {"kind": "fetch", "url": url, "route": route, "date": utcnow(), "raw": raw}
    json.dump(snap, open(fn, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    _log({"kind": "fetch", "url": url, "file": fn, "date": snap["date"]})
    return snap


def strings_of(obj):
    """All string values in a JSON object, concatenated with newlines (the text a verbatim check runs over)."""
    out = []
    def rec(o):
        if isinstance(o, str):
            out.append(o)
        elif isinstance(o, dict):
            for v in o.values():
                rec(v)
        elif isinstance(o, list):
            for v in o:
                rec(v)
    rec(obj)
    return "\n".join(out)


def snap_text(snap):
    return strings_of(snap.get('raw'))


_PUNCT = re.compile(r"[\s\u3000\-_—–―─·•‧・,.，。、；;:：!！?？\"'“”‘’《》〈〉「」『』（）()\[\]【】〔〕{}<>/\\|~`@#$%^&*+=…]+")


def norm(s):
    """traditional->simplified, NFKC, lower-case, punctuation/space stripped."""
    s = unicodedata.normalize('NFKC', s or '')
    s = _t2s.convert(s)
    s = s.lower()
    return _PUNCT.sub('', s)


def norm_tokens(s):
    """Latin-script names: lower-case, strip punctuation, split to a token set (order-free)."""
    s = unicodedata.normalize('NFKD', s or '')
    s = ''.join(c for c in s if not unicodedata.combining(c))
    s = s.lower().replace("'", '').replace('\u2019', '')
    return frozenset(t for t in re.split(r"[^a-z0-9]+", s) if t)


def has_cjk(s):
    return bool(re.search(r"[\u4e00-\u9fff]", s or ''))


def llm(messages, model="deepseek/deepseek-v4.1-flash-1017:exacto", effort="max", json_mode=False, max_tokens=None):
    body = {"model": model, "messages": messages, "provider": {"zdr": True}, "reasoning": {"effort": effort},
            "usage": {"include": True}}
    if json_mode:
        body["response_format"] = {"type": "json_object"}
    if max_tokens:
        body["max_tokens"] = max_tokens
    r = keys.openrouter_chat(body)
    u = (r or {}).get('usage') or {}
    _log({"kind": "llm", "model": model, "date": utcnow(), "cost": u.get('cost'), "usage": u,
          "id": (r or {}).get('id'), "error": (r or {}).get('error')})
    return r


def llm_text(r):
    try:
        return r['choices'][0]['message']['content']
    except Exception:
        return None
