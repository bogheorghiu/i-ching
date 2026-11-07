import sys, json, os, time, hashlib, re, datetime, threading
sys.path.insert(0,'/home/user/wt-research/research')
import keys
from opencc import OpenCC
_t2s=OpenCC('t2s')
SNAP='/home/user/wt-research/research/battery2/keys/snapshots'
os.makedirs(SNAP,exist_ok=True)
IDX=SNAP+'/index.jsonl'
COST='/home/user/wt-research/research/battery2/keys/cost.jsonl'
_lock=threading.Lock()
def today(): return datetime.date.today().isoformat()
def _log(path,obj):
    with _lock:
        with open(path,'a') as f: f.write(json.dumps(obj,ensure_ascii=False)+'\n')
def fetch_raw(url,retries=2):
    for i in range(retries+1):
        r=keys._post("https://api.deepseek.com/v1/tools/fetch","DEEPSEEK_API_KEY",{"url":url},timeout=120)
        if isinstance(r,dict) and 'error' in r and r['error'].get('status') in (502,503,429) and i<retries:
            time.sleep(2+i*2); continue
        return r
def snap_fetch(url,route):
    """fetch and save raw response; returns (snapshot_file, text or None)"""
    r=fetch_raw(url)
    h=hashlib.sha1(url.encode()).hexdigest()[:12]
    fn=f"{SNAP}/f_{h}.json"
    ok=isinstance(r,dict) and 'content' in r and len(r['content'])>0
    with open(fn,'w') as f: json.dump({"url":url,"route":route,"date":today(),"response":r},f,ensure_ascii=False)
    _log(IDX,{"kind":"fetch","url":url,"route":route,"date":today(),"file":os.path.basename(fn),"ok":ok})
    return os.path.basename(fn),(r['content'] if ok else None)
def snap_search(q,count=10):
    r=keys._post("https://api.deepseek.com/v1/tools/search","DEEPSEEK_API_KEY",{"query":q,"count":count,"need_content":False})
    h=hashlib.sha1((q+str(count)).encode()).hexdigest()[:12]
    fn=f"{SNAP}/s_{h}.json"
    with open(fn,'w') as f: json.dump({"query":q,"count":count,"date":today(),"response":r},f,ensure_ascii=False)
    _log(IDX,{"kind":"search","query":q,"date":today(),"file":os.path.basename(fn)})
    return r.get('results',[]) if isinstance(r,dict) else []
def llm(prompt,tag,model="deepseek/deepseek-v4.1-flash-1017:exacto",effort="max"):
    body={"model":model,"provider":{"zdr":True},"reasoning":{"effort":effort},"messages":[{"role":"user","content":prompt}],"usage":{"include":True}}
    r=keys.openrouter_chat(body)
    try:
        c=r['choices'][0]['message']['content']; cost=r['usage']['cost']
    except Exception:
        _log(COST,{"tag":tag,"error":str(r)[:300]}); return None
    _log(COST,{"tag":tag,"cost":cost,"gen":r.get('id')})
    return c
def llm_json(prompt,tag):
    c=llm(prompt,tag)
    if not c: return None
    m=re.search(r'\{.*\}',c,re.S)
    try: return json.loads(m.group(0))
    except Exception: return None
def norm(s):
    s=_t2s.convert(s or '')
    s=s.lower()
    return re.sub(r'[\W_]+','',s)   # drops punctuation and whitespace, keeps CJK and alnum
def in_text(field,text):
    """verbatim (after normalisation) containment"""
    nf=norm(field)
    return bool(nf) and nf in norm(text)
def ngram_overlap_cn(a,b,n=3):
    a=norm(a); b=norm(b)
    sa={a[i:i+n] for i in range(len(a)-n+1)}
    return any(a[i:i+n] in b for i in range(len(a)-n+1)) if a else False
def en_2gram(a,b):
    wa=re.findall(r"[a-z0-9']+",_t2s.convert(a).lower()); wb=re.findall(r"[a-z0-9']+",b.lower())
    ga={tuple(wa[i:i+2]) for i in range(len(wa)-1)}
    gb={tuple(wb[i:i+2]) for i in range(len(wb)-1)}
    return bool(ga&gb)
def total_cost():
    t=0
    if os.path.exists(COST):
        for l in open(COST):
            try: t+=json.loads(l).get('cost',0)
            except: pass
    return t
