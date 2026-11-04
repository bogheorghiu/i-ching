from lib import *
from concurrent.futures import ThreadPoolExecutor
import urllib.parse
qs=["张克宾 海昏竹书《易占》干支配卦探微 哲学研究 2021 维普","张克宾 海昏竹书易占干支配卦探微 知网 cnki 哲学研究2021年08期","海昏竹书《易占》干支配卦探微 万方"]
res=[]
for q in qs:
    for x in snap_search(q,10):
        res.append((q,x['url'],x['title']))
print(len(res))
def f(t):
    fn,c=snap_fetch(t[1],"explore")
    return t,c
with ThreadPoolExecutor(8) as ex:
    for t,c in ex.map(f,res):
        print(t[1][:120],len(c or ''), ('张克宾' in (c or '')))
