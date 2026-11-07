import sys, glob; sys.path.insert(0,'..'); sys.path.insert(0,'.'); from lib import *
from concurrent.futures import ThreadPoolExecutor
S = ["《周易研究》2021年第4期目录 孙功进 太一游宫",
     "山东大学 易学与中国古代哲学研究中心 《周易研究》2022年第1期 目录",
     "《出土文献》2023年第4期 目录 马楠 清华简《大夫食礼》",
     "《中国哲学史》2020年第3期 目录 王顺然",
     "《简帛》第十五辑 里耶秦简医方校读 周波 知网",
     "rwskjournals.sdu.edu.cn 周易研究 期 目录 info"]
F = {"cinii_q": "https://ci.nii.ac.jp/books/search?q=9780791463123",
     "cinii_isbn10": "https://ci.nii.ac.jp/books/search?isbn=0791463125",
     "cinii_title": "https://ci.nii.ac.jp/books/search?title=Yijing+and+Chinese+politics",
     "bsm4164_full": "http://www.bsm.org.cn/?xiaox/4164.html"}
def s1(q):
    rs,fn=search(q,10,route='probe6'); return q,fn,rs
def f1(k):
    c,fn=fetch(F[k],route='probe6'); return k,fn,c
with ThreadPoolExecutor(12) as ex:
    sr=list(ex.map(s1,S)); fr=list(ex.map(f1,list(F)))
for q,fn,rs in sr:
    print('S',q,fn)
    for x in rs[:10]: print('   ',x.get('title','')[:45],'|',x.get('url','')[:130])
for k,fn,c in fr:
    print('F',k,fn,len(c)); i=c.find('検索結果'); print('   ', ws(c[i:i+500]) if i>=0 else ws(c)[:1500])
d=json.load(open(os.path.join(SNAP,'f_3cd2ef22b02e.json')))['response']['content']; print('SUNY:',ws(d)[:1700])
