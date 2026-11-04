import sys, glob; sys.path.insert(0,'..'); from lib import *
from concurrent.futures import ThreadPoolExecutor
F = {"bsm15": "http://www.bsm.org.cn/?xiaox/4164.html",
 "nssd_ctwx": "https://search.napstic.cn/literature/oaj/ctwx?page=1&activeYear=2023&activeIssue=4",
 "nssd_zy": "https://search.napstic.cn/literature/oaj/zhouyyj?page=1&activeYear=2016&activeIssue=3",
 "shsj_zx": "http://www.shsjcb.com/sjcb/view.aspx?id=2020100001004475",
 "zgzx_cbpt": "https://zgzx.cbpt.cnki.net/",
 "jstor": "https://www.jstor.org/stable/1399337",
 "cnkicom2": "https://www.cnki.com.cn/Article/CJFDTOTAL-ZYJY201001010.htm",
 "suny": "https://sunypress.edu/Books/T/The-Yijing-and-Chinese-Politics",
 "camb": "https://www.cambridge.org/core/journals/early-china/article/abs/origin-of-an-yijing-line-statement/AB57B198B1793C284DA2E5DA02687FB9",
}
S = ["ctwx.tsinghua.edu.cn 《出土文献》2023年第4期 总第16期 目录", "商务印书馆 图书 周易 易学 作者 出版时间 ISBN cp.com.cn", "中国社会科学出版社 图书 易学 出土文献 ISBN",
     "萬卷樓 易學 圖書 作者 出版日期 ISBN", "花木蘭文化 古典文獻研究輯刊 易學 ISBN", "Cambridge University Press book early Chinese manuscripts Zhouyi"]
KW = ['ISBN','出版','Volume','Published','Publication','Pages','Issue','作者','著者','期','卷','pp.']
def f1(k):
    c, fn = fetch(F[k], route='probe4'); return k, len(c), c
def s1(q):
    rs, fn = search(q, 10, route='probe4'); return q, [(x.get('title','')[:45], x.get('url','')) for x in rs[:8]]
with ThreadPoolExecutor(12) as ex:
    fr = list(ex.map(f1, list(F))); sr = list(ex.map(s1, S))
for k, n, c in fr:
    c2 = ws(c)
    print('F', k, n, '|', c2[:700])
    if k in ('suny','camb','cnkicom2','shsj_zx'):
        for kw in ['ISBN','Publication Date','Volume','Published','pp','作者','刊名','年','出版社']:
            i = c2.find(kw)
            if i >= 0: print('   ...', kw, '=>', c2[max(0,i-80):i+160])
    print()
for q, rs in sr:
    print('S', q)
    for t, u in rs: print('   ', t, '|', u[:150])
