import json, sys
from lib import *

def S(q, count=8):
    s = search(q, count, route='probe2')
    res = s['raw'].get('results') or []
    print('=== SEARCH', q)
    for i, r in enumerate(res[:count]):
        print(' ', i+1, '|', (r.get('title') or '')[:60].replace('\n',' '), '|', (r.get('url') or '')[:150], '|', (r.get('snippet') or '')[:90].replace('\n',' '))

def F(u, n=500):
    s = fetch(u, route='probe2')
    raw = s['raw']
    t = snap_text(s)
    print('=== FETCH', u[:140], '| len', len(t), '| err' if 'error' in raw else '')
    print('   ', t[:n].replace('\n', ' / '))

for q in ['周易研究 编辑部 官方网站 往期目录 山东大学', '中国哲学史 杂志 编辑部 官网 过刊目录 2019年第2期',
          '出土文献 中西书局 辑刊 目录 2020年第1期', '简帛 上海古籍出版社 第十五辑 目录',
          'T\'oung Pao Volume 105 issue brill.com table of contents']:
    S(q)

F('https://www.cambridge.org/core/journals/early-china/volume/88C8D37E3E0B6748C2BD70458CBED300', 1500)
F('https://ci.nii.ac.jp/ncid/BC09213224', 1200)
F('https://www.cqvip.com/journal/3004/index.html', 400)
F('https://c.wanfangdata.com.cn/magazine/zhouyyj?tabId=article&publishYear=2015&issueNum=1&page=1&isSync=0', 800)
F('https://www.haoqikan.com/zhouyiyanjiu/201805/', 800)
