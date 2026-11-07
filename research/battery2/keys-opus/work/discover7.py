import sys, glob; sys.path.insert(0,'..'); sys.path.insert(0,'.'); from lib import *
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import quote
# publisher URLs seen in earlier search snapshots
PUB=['zhbc.com.cn','cp.com.cn','csspw','wanjuan','hmmc','huamulan','guji.com.cn','zxpress','sunypress','cup.columbia','uhpress','cambridge.org/core/books','brill.com/display','press.uchicago','hup.harvard','press.princeton','ssap.com.cn','pup.cn','ecnupress','qlss','bashu','fhcb']
seen={}
for f in glob.glob(os.path.join(SNAP,'s_*.json')):
    d=json.load(open(f)); r=d['response']
    for x in (r.get('results',[]) if isinstance(r,dict) else []):
        u=x.get('url','')
        if any(p in u for p in PUB): seen[u.split('#')[0]]=x.get('title','')[:60]
print('PUBLISHER URLS SEEN:'); [print('  ',t,'|',u[:130]) for u,t in list(seen.items())[:30]]
CI='https://ci.nii.ac.jp/books/search?count=100&sortorder=3&'
F={'ctwx3062':'https://www.ctwx.tsinghua.edu.cn/info/1093/3062.htm',
   'zy1686':'http://zhouyi.sdu.edu.cn/info/1033/1686.htm',
   'nssd_zy2025_3_p1':'https://search.napstic.cn/literature/oaj/zhouyyj?page=1&activeYear=2025&activeIssue=3',
   'nssd_zy2025_3_p2':'https://search.napstic.cn/literature/oaj/zhouyyj?page=2&activeYear=2025&activeIssue=3',
   'nssd_ctwx2023_4_p2':'https://search.napstic.cn/literature/oaj/ctwx?page=2&activeYear=2023&activeIssue=4',
   'ci_yijing':CI+'title='+quote('Yijing'),
   'ci_iching':CI+'title='+quote('I ching'),
   'ci_manus':CI+'q='+quote('bamboo manuscripts China'),
   'ci_zy_guji':CI+'title='+quote('周易')+'&publisher='+quote('上海古籍出版社'),
   'ci_zy_zhbc':CI+'title='+quote('周易')+'&publisher='+quote('中華書局'),
   'ci_yx':CI+'title='+quote('易學')+'&year_from=1985',
   'ci_jb_zx':CI+'title='+quote('簡')+'&publisher='+quote('中西書局'),
}
S=['《简帛》第十五辑 上海古籍出版社 shsjcb 著者 武汉大学简帛研究中心 2017',
   '每期目录：《周易研究》2024年第4期 zhouyi.sdu.edu.cn',
   '《出土文献》2022年第3期（总第11期） ctwx.tsinghua.edu.cn info 1093']
def f1(k): c,fn=fetch(F[k],route='discover7'); return k,fn,c
def s1(q): rs,fn=search(q,10,route='discover7'); return q,fn,rs
with ThreadPoolExecutor(16) as ex:
    fr=list(ex.map(f1,list(F))); sr=list(ex.map(s1,S))
out={}
for k,fn,c in fr:
    out[k]={'file':fn,'len':len(c)}
    w=ws(c)
    print('\n##',k,fn,len(c))
    if k.startswith('ci_'):
        i=w.find('検索結果'); print('  ',w[i:i+2600] if i>=0 else w[:300])
    else: print('  ',w[:1800])
for q,fn,rs in sr:
    print('\nS',q,fn)
    for x in rs[:10]: print('   ',x.get('title','')[:50],'|',x.get('url','')[:120])
json.dump(out,open('work/discover7.json','w'),ensure_ascii=False,indent=1)
