import sys, json, os, time, hashlib, re, datetime, threading, unicodedata, urllib.request
sys.path.insert(0, '/home/user/wt-research/research')
import keys
from opencc import OpenCC
_t2s = OpenCC('t2s')
HERE = os.path.dirname(os.path.abspath(__file__))
SNAP = os.path.join(HERE, 'snapshots')
os.makedirs(SNAP, exist_ok=True)
_lock = threading.Lock()
def today(): return datetime.datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')
def _log(fn, rec):
    with _lock:
        with open(os.path.join(HERE, fn), 'a') as f: f.write(json.dumps(rec, ensure_ascii=False) + '\n')
def _save(kind, url, route, query, resp):
    h = hashlib.sha1((kind + (url or '') + (query or '') + today()).encode()).hexdigest()[:12]
    fn = f'{kind}_{h}.json'
    rec = {'file': 'snapshots/' + fn, 'kind': kind, 'url': url, 'route': route, 'query': query, 'date': today()}
    with open(os.path.join(SNAP, fn), 'w') as f:
        json.dump({**rec, 'response': resp}, f, ensure_ascii=False)
    _log('snapshots/index.jsonl', rec)
    return 'snapshots/' + fn
def fetch(url, route='', query=None, retries=3):
    r = None
    for i in range(retries):
        try:
            r = keys._post('https://api.deepseek.com/v1/tools/fetch', 'DEEPSEEK_API_KEY', {'url': url}, timeout=120)
        except Exception as e:
            r = {'error': {'status': 'exc', 'body': str(e)[:300]}}
        _log('toolcalls.jsonl', {'t': 'fetch', 'url': url, 'date': today(), 'ok': 'content' in (r or {})})
        if isinstance(r, dict) and r.get('content'): break
        time.sleep(2 + 2 * i)
    fn = _save('f', url, route, query, r)
    return (r.get('content') if isinstance(r, dict) else None) or '', fn
def search(query, count=10, route=''):
    try:
        r = keys.deepseek_search(query, count)
    except Exception as e:
        r = {'error': str(e)[:300]}
    _log('toolcalls.jsonl', {'t': 'search', 'q': query, 'date': today()})
    fn = _save('s', None, route, query, r)
    return (r.get('results') if isinstance(r, dict) else None) or [], fn
PUNCT_RE = re.compile(r'[\W_]+', re.U)
def t2s(s): return _t2s.convert(s or '')
def norm(s):
    s = unicodedata.normalize('NFKC', s or '')
    s = t2s(s).lower()
    return PUNCT_RE.sub('', s)
def ws(s): return re.sub(r'\s+', ' ', s or '').strip()
def verbatim(field, text):
    if not field: return False
    if field in text: return 'exact'
    if ws(field) in ws(text): return 'ws'
    if re.sub(r'\s+', '', field) in re.sub(r'\s+', '', text): return 'nows'
    return False
MODEL = "deepseek/deepseek-v4.1-flash-1017:exacto"
def llm(prompt, tag=''):
    body = {"model": MODEL, "provider": {"zdr": True}, "reasoning": {"effort": "max"},
            "messages": [{"role": "user", "content": prompt}], "usage": {"include": True},
            "response_format": {"type": "json_object"}}
    for i in range(3):
        r = keys.openrouter_chat(body)
        cost = (r.get('usage') or {}).get('cost', 0) if isinstance(r, dict) else 0
        _log('costs.jsonl', {'tag': tag, 'id': r.get('id') if isinstance(r, dict) else None, 'cost': cost, 'date': today(), 'err': r.get('error') if isinstance(r, dict) else None})
        try:
            txt = r['choices'][0]['message']['content']
            txt = txt.strip()
            if txt.startswith('```'): txt = re.sub(r'^```\w*|```$', '', txt).strip()
            return json.loads(txt)
        except Exception:
            time.sleep(2)
    return None
