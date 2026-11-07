from tools import *
import time, urllib.parse, collections
from concurrent.futures import ThreadPoolExecutor
def fx(u):
    try:
        r=fetch(u)
    except Exception as e:
        return {}
    return r
qs=["上海古籍出版社 清华简 图书 出版","中西书局 出土文献 图书 详情","中华书局 帛书 周易 图书 出版","北京大学出版社 出土文献 研究 图书","简帛 研究 专著 出版社 书目 ISBN","周易 研究 专著 国家图书馆 馆藏 书目"]
with ThreadPoolExecutor(6) as ex:
    res=list(ex.map(lambda q:search(q,10),qs))
items=[(x['url'],x['title']) for r in res for x in r.get('results',[])]
with ThreadPoolExecutor(12) as ex:
    fs=list(ex.map(lambda t:fx(t[0]),items))
stat=collections.defaultdict(lambda:[0,0])
for (u,t),f in zip(items,fs):
    d=urllib.parse.urlparse(u).netloc
    c=f.get('content','') if isinstance(f,dict) else ''
    stat[d][0]+=1; stat[d][1]+=len(c)>500
for d,(n,o) in sorted(stat.items(),key=lambda t:-t[1][0]): print(d,n,o)
