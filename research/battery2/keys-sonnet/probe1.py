import json, sys
from lib import *

def show_search(q, count=10, nc=False):
    s = search(q, count, need_content=nc, route='probe')
    raw = s['raw']
    print('=== SEARCH', q, '| top keys:', list(raw.keys()) if isinstance(raw, dict) else type(raw))
    res = None
    if isinstance(raw, dict):
        for k in ('results','data','items','web','organic'):
            if k in raw: res = raw[k]; break
        if res is None: print(json.dumps(raw, ensure_ascii=False)[:800])
    if res is not None:
        if isinstance(res, dict): print('res dict keys', list(res.keys())); res = res.get('results') or res.get('items') or []
        for i, r in enumerate(res[:count]):
            print(i+1, '|', (r.get('title') or '')[:70], '|', r.get('url'), '|', (r.get('snippet') or '')[:100].replace('\n',' '))
    return s

def show_fetch(u):
    s = fetch(u, route='probe')
    raw = s['raw']
    print('=== FETCH', u, '| type', type(raw).__name__, '| keys', list(raw.keys()) if isinstance(raw, dict) else '')
    t = snap_text(s)
    print('len', len(t)); print(t[:700].replace('\n', ' / '))
    return s

show_search('周易研究 2018年第5期 目录', 10)
show_search('Early China volume 40 2017 Cambridge Core table of contents', 10)
for u in ['https://www.cambridge.org/core/journals/early-china/issue/ACEBA21B5A9D7C6B0E3E4D6B0E9CF0A8',
          'https://www.cambridge.org/core/journals/early-china/all-issues',
          'https://brill.com/view/journals/tpao/tpao-overview.xml',
          'https://ci.nii.ac.jp/books/search?q=%E5%91%A8%E6%98%93%E7%A0%94%E7%A9%B6&count=20',
          'https://api.crossref.org/works?query.container-title=Early+China&rows=3&select=DOI,title,author,issued,volume,issue,container-title,publisher,type',
          ]:
    try:
        show_fetch(u)
    except Exception as e:
        print('ERR', u, e)
