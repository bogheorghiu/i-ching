import sys, glob; sys.path.insert(0,'..'); from lib import *
from concurrent.futures import ThreadPoolExecutor
def links(c, pat=None):
    L = re.findall(r'\[([^\]]{0,80})\]\((https?://[^)\s]+)\)', c)
    return [(t,u) for t,u in L if (pat is None or re.search(pat, t+u))]
# real URLs from prior search snapshots (display masks digits)
vip = None
for f in glob.glob('../snapshots/s_*.json'):
    d = json.load(open(f))
    for x in (d['response'] or {}).get('results', []) if isinstance(d['response'], dict) else []:
        if 'dianda.cqvip.com' in x.get('url',''): vip = x['url']
F = {"rwsk": "https://rwskjournals.sdu.edu.cn/kwdh/qkdh/zyyj.htm",
 "ctwx": "https://www.ctwx.tsinghua.edu.cn/",
 "napstic": "https://search.napstic.cn/literature/oaj/zgzxs?page=1&activeYear=2020&activeIssue=3",
 "shsjcb": "http://www.shsjcb.com/sjcb/view.aspx?id=2020100001016902",
 "cinii_isbn": "https://ci.nii.ac.jp/books/search?isbn=9787532591886",
 "vip": vip,
 "cnki_wap_art": "https://wap.cnki.net/touch/web/Journal/Article/ZYJY201001010.html",
 "phil_cass": "http://philosophy.cass.cn/",
}
S = ["中国哲学史 杂志 编辑部 官网 过刊目录 中国社会科学院哲学研究所", "简帛网 《简帛》 第十辑 目录 论文", "清华大学出土文献研究与保护中心 《出土文献》 期刊 目录 2022年",
     "Early China Cambridge Core article Yijing divination", "SUNY Press book Yijing Book of Changes", "University of Washington Press book early Chinese manuscripts bamboo",
     "周易研究 编辑部 过刊浏览 山东大学"]
def f1(k):
    u = F[k]
    if not u: return k, None, 0, '', []
    c, fn = fetch(u, route='probe2')
    return k, u, len(c), c, links(c)
def s1(q):
    rs, fn = search(q, 10, route='probe2')
    return q, [(x.get('title','')[:45], x.get('url','')) for x in rs[:8]]
with ThreadPoolExecutor(12) as ex:
    fr = list(ex.map(f1, list(F))); sr = list(ex.map(s1, S))
for k, u, n, c, L in fr:
    print('F', k, u, n)
    if k in ('shsjcb','cinii_isbn','vip','cnki_wap_art','napstic'): print('   ', ws(c)[:900])
    else: print('   ', ws(c)[:250])
    for t, l in L[:25]:
        if k in ('rwsk','ctwx','phil_cass','napstic','cinii_isbn'): print('     L', t[:40], l[:120])
    print()
for q, rs in sr:
    print('S', q)
    for t, u in rs: print('   ', t, '|', u[:150])
