import sys, glob; sys.path.insert(0,'..'); sys.path.insert(0,'.'); from lib import *
from concurrent.futures import ThreadPoolExecutor
# real URLs (unmasked) from saved search snapshots
def find_url(sub):
    for f in glob.glob(os.path.join(SNAP,'s_*.json')):
        d=json.load(open(f)); r=d['response']
        for x in (r.get('results',[]) if isinstance(r,dict) else []):
            if sub in x.get('url',''): return x['url']
c = json.load(open(os.path.join(SNAP,'f_6362dc8f6953.json')))['response']['content']
i = c.find('作者'); print('CNKI.com.cn author?', re.sub(r'\s+',' ',c[:600]))
F = {"nssd_zy21": find_url('zhouyyj?page=1&activeYear=2021&activeIssue=4'),
 "bsm_xinx": "http://m.bsm.org.cn/?xinx/",
 "ctwx_qkml": "https://www.ctwx.tsinghua.edu.cn/ctwx/qkml.htm",
 "cinii_hon": "https://ci.nii.ac.jp/books/search?isbn=9780791463123",
 "wanfang_zy": find_url('c.wanfangdata.com.cn/magazine/zhouyyj'),
 "ec_listing": "https://www.cambridge.org/core/journals/early-china/listing?pageNum=7",
 "opac_htu": find_url('opac.htu.cn/opac/item.php'),
}
S = ["易学与中国古代哲学研究中心 《周易研究》期目录 作者 zhouyi.sdu.edu.cn",
     "清华大学出土文献研究与保护中心 《出土文献》2022年第2期 目录 作者",
     "简帛网 既刊信息 《简帛》第二十辑 目录",
     "shsjcb.com 上海古籍出版社 易学 研究 著者 出版日期 ISBN",
     "shsjcb.com 中西书局 简牍 研究 著者 出版日期 ISBN",
     "sunypress.edu Books Yijing commentary Chinese philosophy",
     "uhpress.hawaii.edu book early Chinese manuscripts excavated texts",
     "brill.com book Yijing manuscripts Warring States edited"]
def f1(k):
    u=F[k]
    if not u: return k,None,''
    c,fn=fetch(u,route='probe5'); return k,u,c
def s1(q):
    rs,fn=search(q,10,route='probe5'); return q,fn,[(x.get('title','')[:40],x.get('url','')) for x in rs[:10]]
with ThreadPoolExecutor(14) as ex:
    fr=list(ex.map(f1,list(F))); sr=list(ex.map(s1,S))
for k,u,c in fr:
    print('F',k,u and u[:100],len(c)); print('   ',ws(c)[:900]); print('   LINKS', re.findall(r'\]\((https?://[^)\s]+)\)', c)[:12]); print()
for q,fn,rs in sr:
    print('S',q,fn)
    for t,u in rs: print('   ',t,'|',u[:140])
