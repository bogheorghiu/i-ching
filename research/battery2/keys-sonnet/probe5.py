import json, sys, re
from lib import *

def S(q, count=8, nc=False, dom=None, n=500):
    s = search(q, count, need_content=nc, route='probe5')
    res = s['raw'].get('results') or []
    print('=== SEARCH', q, '| nc', nc, '| nres', len(res))
    for i, r in enumerate(res[:count]):
        u = r.get('url') or ''
        print(' ', i+1, '|', (r.get('title') or '')[:50].replace('\n',' '), '|', u[:130])
        if nc and (dom is None or re.search(dom, u)):
            c = r.get('content') or ''
            print('      content len', len(c), '::', c[:n].replace('\n', ' / '))
    return res

def F(u, n=500):
    s = fetch(u, route='probe5')
    raw = s['raw']
    t = snap_text(s)
    print('=== FETCH', u[:140], '| len', len(t), '| ERR' if 'error' in raw else '')
    print('   ', t[:n].replace('\n', ' / '))
    return t

S('周易研究 1989年02期 目录 天道、人道、道统 陈立夫 cnki.com.cn', 6, nc=True, dom=r'cnki|cqvip|wanfang')
S('中国哲学史 2013年第2期 目录 知网', 6, nc=True, dom=r'cnki|cqvip|wanfang')
F('http://www.cnki.com.cn/Journal/F-F5-ZYJY-1989-02.htm', 600)
F('https://www.cnki.com.cn/Article/CJFDTotal-ZYJY198902001.htm', 600)
F('http://www.shsjcb.com/sjcb/bkview.aspx?bkid=280204&cid=837487', 900)
S('Society for the Study of Early China Early China journal volume contents earlychina.org', 8)
S('T\'oung Pao brill.com/view/journals/tpao 2019 "Volume 105: Issue 1-2" ', 8, nc=False)
S('Early China 2015 vol. 38 article jstor', 6)
