import json, sys, re, glob
from lib import *

def S(q, count=8, nc=False, n=300, dom=None):
    s = search(q, count, need_content=nc, route='probe6')
    res = s['raw'].get('results') or []
    print('=== SEARCH', q, '| nres', len(res))
    for i, r in enumerate(res[:count]):
        u = r.get('url') or ''
        print(' ', i+1, '|', (r.get('title') or '')[:60].replace('\n',' '), '|', u[:120])
        if nc and (dom is None or re.search(dom, u)):
            print('      content:', (r.get('content') or '')[:n].replace('\n',' / '))
    return res

def F(u, n=500, tag=''):
    s = fetch(u, route='probe6')
    raw = s['raw']
    t = snap_text(s)
    print('=== FETCH', u[:150], '| len', len(t), '| ERR' if 'error' in raw else '')
    print('   ', t[:n].replace('\n', ' / '))
    return t

F('https://ci.nii.ac.jp/books/opensearch/search?q=%E5%B8%9B%E6%9B%B8%E5%91%A8%E6%98%93&format=json&count=3', 700)
F('https://api.crossref.org/journals/0362-5028/works?sample=4&select=DOI,title,author,issued,volume,issue,page,is-referenced-by-count,type', 1500)
F('https://api.crossref.org/journals/1568-5322/works?sample=3&select=DOI,title,author,issued,volume,issue,page,is-referenced-by-count,type', 900)
t = F('https://doi.org/10.1017/S0362502800006957', 1200)
S('Hsu "The Concept of Predetermination and Fate in the Han" Early China 1975', 8)
# weixin TOC from saved search snapshot
for fn in glob.glob('snapshots/search_*.json'):
    d = json.load(open(fn, encoding='utf-8'))
    for r in (d['raw'].get('results') or []):
        if 'mp.weixin.qq.com' in (r.get('url') or '') and (r.get('title') or '').startswith('期刊目录'):
            t = F(r['url'], 1500); break
S('北京大学出版社 周易 出版时间 ISBN pup.cn 图书', 6)
S('上海古籍出版社 guji.com.cn 简帛 第十五辑 出版时间', 6)
S('社会科学文献出版社 ssap.com.cn 周易 出版时间', 6)
F('http://zhouyi.sdu.edu.cn', 800)
