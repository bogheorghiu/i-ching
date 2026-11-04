import json, sys, re
from lib import *

def S(q, count=8, nc=False, show=True):
    s = search(q, count, need_content=nc, route='probe4')
    res = s['raw'].get('results') or []
    if show:
        print('=== SEARCH', q, '| nc', nc)
        for i, r in enumerate(res[:count]):
            print(' ', i+1, '|', (r.get('title') or '')[:50].replace('\n',' '), '|', (r.get('url') or '')[:140], '|', (r.get('snippet') or '')[:60].replace('\n',' '), '| keys', list(r.keys()) if nc and i==0 else '')
    return res

def F(u, n=400, find=None):
    s = fetch(u, route='probe4')
    raw = s['raw']
    t = snap_text(s)
    print('=== FETCH', u[:140], '| len', len(t), '| ERR' if 'error' in raw else '')
    print('   ', t[:n].replace('\n', ' / '))
    return t

res = S('周易研究 虞氏易集义 乾卦 刘大钧 2018年第5期 知网 维普 万方', 10)
for r in res:
    u = r.get('url') or ''
    if re.search(r'cnki|cqvip|wanfang', u):
        F(u, 500)
        break
t = F('http://zhouyi.sdu.edu.cn/zyyjxk/qkjs.htm', 1500)
S('zhouyi.sdu.edu.cn zyyjxk 周易研究 2019年第3期 目录', 8)
S('zhouyi.sdu.edu.cn 周易研究 往期目录 2016年第1期', 8)
F('https://zyjy.chinajournal.net.cn/EditorGN/PromptPageInfo.aspx?t=v&c=4', 500)
S('brill.com view journals tpao 2019 T\'oung Pao 105 issue 1-2 "Brill" article', 8)
r = S('周易研究 2018 虞氏易集义 刘大钧', 3, nc=True, show=True)
if r: print('content len', len(r[0].get('content') or ''), (r[0].get('content') or '')[:300].replace('\n',' / '))
