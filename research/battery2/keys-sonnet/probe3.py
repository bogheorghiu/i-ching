import json, sys
from lib import *

def S(q, count=8):
    s = search(q, count, route='probe3')
    res = s['raw'].get('results') or []
    print('=== SEARCH', q)
    for i, r in enumerate(res[:count]):
        print(' ', i+1, '|', (r.get('title') or '')[:50].replace('\n',' '), '|', (r.get('url') or '')[:130], '|', (r.get('snippet') or '')[:70].replace('\n',' '))

def F(u, n=400, find=None):
    s = fetch(u, route='probe3')
    raw = s['raw']
    t = snap_text(s)
    print('=== FETCH', u[:140], '| len', len(t), '| ERR' if 'error' in raw else '')
    print('   ', t[:n].replace('\n', ' / '))
    if find:
        for f in find:
            print('    has', repr(f), f in t)

F('https://brill.com/view/journals/tpao/109/1-2/tpao.109.issue-1-2.xml', 1200)
F('https://www.jstor.org/journal/earlychina', 300)
F('https://lccn.loc.gov/2002066577', 400)
F('https://www.cnki.com.cn/Journal/F-F5-ZYJY-1989-02.htm', 1200)
F('https://cqvip.com/journal/42632/42632/2002', 800)
S('shsjcb.com 出土数字卦文献辑释 贾连翔 中西书局')
S('周易研究 编辑部 投稿 山东大学 官网 zyyj.sdu.edu.cn')
S('《中国哲学史》编辑部 官网 中国社会科学院哲学研究所 期刊 目录 往期')
S('Studies of Zhouyi brill OR cambridge "Early China" volume 12 1987 table of contents')
S('上海古籍出版社 官网 周易 新书 出版 ISBN 978-7-5325')
S('中华书局 zhbc.com.cn 周易 出土文献 新书 图书详情')
