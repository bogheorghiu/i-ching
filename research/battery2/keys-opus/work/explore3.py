import sys, glob; sys.path.insert(0,'..'); from lib import *
from concurrent.futures import ThreadPoolExecutor
F = {"ctwx_qkml": "https://www.ctwx.tsinghua.edu.cn/ctwx/qkml/4.htm",
 "napstic_zy": "https://search.napstic.cn/literature/oaj/zhouyyj?page=1&activeYear=2016&activeIssue=3",
 "cnki_com": "https://www.cnki.com.cn/Article/CJFDTOTAL-ZYJY201503001.htm",
 "kns": "https://kns.cnki.net/kcms/detail/detail.aspx?dbcode=CJFD&filename=ZYJY201503001",
 "camb_art": "https://www.cambridge.org/core/journals/early-china/article/abs/origin-of-an-yijing-line-statement/AB57B198B1793C284DA2E5DA02687FB9",
 "camb_art2": "http://core-prod.cambridgecore.org/core/journals/early-china/article/abs/origin-of-an-yijing-line-statement/AB57B198B1793C284DA2E5DA02687FB9",
 "suny": "https://sunypress.edu/Books/T/The-Yijing-and-Chinese-Politics",
 "cinii_en": "https://ci.nii.ac.jp/books/search?q=Yijing+and+Chinese+politics",
 "zhouyi_c": "http://zhouyi.sdu.edu.cn/zyyjxk.htm",
}
S = ["zhouyi.sdu.edu.cn 《周易研究》 2016年第3期 目录", "philosophy.cass.cn 《中国哲学史》 2019年第2期 目录", "简帛网 bsm.org.cn 《简帛》第十五辑 目录",
     "中华书局 bookinfo 易学 图书 作者 出版时间", "University of Hawaii Press book Yijing", "Columbia University Press book Chinese manuscripts Warring States"]
def f1(k):
    c, fn = fetch(F[k], route='probe3'); return k, F[k], len(c), c
def s1(q):
    rs, fn = search(q, 10, route='probe3'); return q, [(x.get('title','')[:45], x.get('url','')) for x in rs[:8]]
with ThreadPoolExecutor(12) as ex:
    fr = list(ex.map(f1, list(F))); sr = list(ex.map(s1, S))
for k, u, n, c in fr:
    print('F', k, n, '|', ws(c)[:1100] if k in ('ctwx_qkml','napstic_zy','cnki_com','kns','camb_art','camb_art2','suny','cinii_en') else ws(c)[:300]); print()
for q, rs in sr:
    print('S', q)
    for t, u in rs: print('   ', t, '|', u[:150])
