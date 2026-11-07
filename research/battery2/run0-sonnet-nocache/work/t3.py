from lib import *
import urllib.parse
for q in ["國家圖書館 臺灣期刊論文索引系統 易經 馬王堆 帛書 篇目","readopac.ncl.edu.tw nclJournal 周易 論文","HKU Libraries 馬王堆 帛書 周易 期刊論文 catalogue","Early China article Cambridge Core 'Shaughnessy' Mawangdui Yijing A First Reading JSTOR","Bamboo and Silk journal Brill article Zhouyi manuscript"]:
    print('##',q)
    for x in snap_search(q,10):
        print('  ',x['title'][:60],x['url'][:120])
