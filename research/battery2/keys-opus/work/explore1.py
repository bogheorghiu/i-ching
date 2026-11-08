import sys; sys.path.insert(0,'..'); from lib import *
from concurrent.futures import ThreadPoolExecutor
F = ["https://www.cambridge.org/core/journals/early-china/all-issues",
"https://www.jstor.org/journal/earlychina",
"https://www.degruyterbrill.com/journal/key/tpao/html",
"https://zyyj.cbpt.cnki.net/",
"http://www.bsm.org.cn/",
"https://read.cnki.net/web/Journal/List/ZYJY201503.html",
"https://wap.cnki.net/touch/web/Journal/Article/ZYJY201906001.html",
"https://ci.nii.ac.jp/books/search?q=%E6%98%93%E5%AD%B8&count=100&sortorder=1",
"https://www.zxpress.com.cn/",
"https://www.guji.com.cn/",
"https://api.crossref.org/works?query.container-title=Early+China&rows=3",
]
S = ["《中国哲学史》杂志 2016年第3期 目录", "《周易研究》 当期目录 山东大学人文社科期刊社 rwskjournals", "《简帛》第十八辑 目录 武汉大学简帛研究中心",
"《出土文献》2021年第2期 目录 清华大学出土文献研究与保护中心", "Early China volume 41 2018 Cambridge Core article", "T'oung Pao article Book of Changes degruyterbrill",
"上海古籍出版社 图书详情 周易 ISBN 出版时间", "中西书局 图书 清华简 研究 ISBN 出版时间", "维普 周易研究 2010年 论文 象数"]
def f1(u):
    c, fn = fetch(u, route='probe')
    return u, len(c), ws(c)[:350]
def s1(q):
    rs, fn = search(q, 10, route='probe')
    return q, [(x.get('title','')[:40], x.get('url','')[:110]) for x in rs[:8]]
with ThreadPoolExecutor(12) as ex:
    fr = list(ex.map(f1, F)); sr = list(ex.map(s1, S))
for u, n, c in fr: print('F', u, n, '|', c, '\n')
for q, rs in sr:
    print('S', q)
    for t, u in rs: print('   ', t, '|', u)
