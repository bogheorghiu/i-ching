from lib import *
from concurrent.futures import ThreadPoolExecutor
import urllib.parse
qs=["帛书《缪和》《昭力》传《易》者非孔子说补证 周易研究 2019 刘彬","清华简《筮法》 坎离水火 问题覆议 周易研究","海昏竹书《易占》初探 周易研究 2021","大衍揲扐法与清华简《筮法》揲扐法再探讨"]
res=[]
for q in qs:
    for x in snap_search(q,10):
        d=urllib.parse.urlparse(x['url']).netloc
        if any(k in d for k in ['cnki','cqvip','wanfang']): res.append((q,x['url'],x['title']))
print(len(res))
def f(t):
    fn,c=snap_fetch(t[1],"explore")
    return t,c
with ThreadPoolExecutor(8) as ex:
    for t,c in ex.map(f,res):
        print(t[1][:110],len(c or ''))
        if c and len(c)>300: print('   ',c[:400].replace('\n',' '))
