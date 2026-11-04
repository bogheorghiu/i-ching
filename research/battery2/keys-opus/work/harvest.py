import sys, glob; sys.path.insert(0,'..'); sys.path.insert(0,'.'); from lib import *
from concurrent.futures import ThreadPoolExecutor
S = ["每期目录：《周易研究》2008年", "每期目录：《周易研究》2012年第4期", "每期目录：《周易研究》2016年第2期", "每期目录：《周易研究》2019年第5期",
     "每期目录：《周易研究》2022年第3期", "zhouyi.sdu.edu.cn info 1033 每期目录 周易研究 2004年",
     "ctwx.tsinghua.edu.cn info 1093 《出土文献》2020年第1期（总第1期）", "ctwx.tsinghua.edu.cn 《出土文献》2021年第3期（总第7期）",
     "ctwx.tsinghua.edu.cn 《出土文献》2022年第4期（总第12期）", "ctwx.tsinghua.edu.cn 《出土文献》2024年第2期（总第18期）",
     "shsjcb.com 产品中心 上海古籍 易学 著者 出版日期", "shsjcb.com 产品中心 中西书局 清华简 著者 出版日期", "shsjcb.com 产品中心 上海古籍 周易 研究 定价"]
F = {"zy_toc": "http://zhouyi.sdu.edu.cn/info/1033/1686.htm", "ctwx_toc": "https://www.ctwx.tsinghua.edu.cn/info/1093/3062.htm",
     "cir_ec": "https://cir.nii.ac.jp/all?q=%22The%20Origin%20of%20an%20Yijing%20Line%20Statement%22",
     "ec_list40": "https://www.cambridge.org/core/journals/early-china/listing?pageNum=40",
     "nssd_zgzxs_art": "https://search.napstic.cn/literature/periodical/010zgzxs202003002"}
def s1(q): rs,fn=search(q,10,route='harvest'); return q,fn,rs
def f1(k): c,fn=fetch(F[k],route='harvest'); return k,fn,c
with ThreadPoolExecutor(16) as ex:
    sr=list(ex.map(s1,S)); fr=list(ex.map(f1,list(F)))
H={'zy':{}, 'ctwx':{}, 'shsjcb':{}}
for q,fn,rs in sr:
    for x in rs:
        u=x.get('url',''); t=x.get('title','')
        if 'zhouyi.sdu.edu.cn/info/' in u: H['zy'][u.split('#')[0]]=t
        if 'ctwx.tsinghua.edu.cn/info/' in u: H['ctwx'][u.split('#')[0]]=t
        if 'shsjcb.com/sjcb/view.aspx' in u: H['shsjcb'][u.split('#')[0]]=t
json.dump(H, open('harvest.json','w'), ensure_ascii=False, indent=1)
for k,v in H.items():
    print(k, len(v))
    for u,t in v.items(): print('   ',t[:50],'|',u)
for k,fn,c in fr:
    print('F',k,fn,len(c)); print('   ',ws(c)[:1300])
