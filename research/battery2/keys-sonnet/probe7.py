import json, sys, re
from concurrent.futures import ThreadPoolExecutor
from lib import *

def F(u, n=260):
    try:
        s = fetch(u, route='probe7')
    except BaseException as e:
        return (u, 'EXC '+repr(e)[:100], '')
    raw = s['raw']; t = snap_text(s)
    err = isinstance(raw, dict) and 'error' in raw
    return (u, ('ERR ' if err else 'ok  ')+str(len(t)), t[:n].replace('\n',' / '))

def S(q, count=8):
    try:
        s = search(q, count, route='probe7')
    except BaseException as e:
        return (q, [('EXC', repr(e)[:100], '')])
    res = s['raw'].get('results') or []
    return (q, [((r.get('title') or '')[:50].replace('\n',' '), (r.get('url') or '')[:170], (r.get('snippet') or '')[:50].replace('\n',' ')) for r in res[:count]])

urls = [
 'https://zyjy.chinajournal.net.cn/',
 'https://zyjy.chinajournal.net.cn/WKA/WebPublication/index.aspx?mid=zyjy',
 'http://zhouyi.sdu.edu.cn/',
 'https://zgzxs.cbpt.cnki.net/',
 'http://zgzxs.cssn.cn/',
 'http://mp.weixin.qq.com/s?__biz=MjM5ODA3MTYzOA==&mid=[PHONE]&idx=1&sn=2a1cc69872046920dbf8ba8a4e13aa63',
 'https://www.cnki.com.cn/Article/CJFDTotal-ZYJY201805003.htm',
 'https://www.cnki.com.cn/Article/CJFDTOTAL-ZYJY201805003.htm',
 'https://d.wanfangdata.com.cn/periodical/zhouyyj201805003',
 'https://kns.cnki.net/kcms/detail/detail.aspx?dbcode=CJFD&dbname=CJFD2018&filename=ZYJY201805003',
 'https://earlychina.org/category/early-china-journal/new-publication/',
 'http://opac.nlc.cn/F/?func=find-b&find_code=ISB&request=9787547514511',
 'http://ilasweb.kmlib.yn.cn/NTRdrBookRetr.aspx?strType=text&strKeyValue=978-7-5325-8317-1',
 'https://ci.nii.ac.jp/books/search?isbn=9787532583171',
 'https://www.loc.gov/books/?q=Zhouyi+commentary&fo=json&c=3',
 'https://katalog.slub-dresden.de/id/0-770027008',
 'https://www.cambridge.org/core/journals/early-china/listing?pageNum=8',
 'https://brill.com/view/journals/tpao/tpao-overview.xml',
 'https://vufind.library.sh.cn/Record/28fa5c7b-ad72-4187-8165-88a45323c77f?lng=en',
 'https://www.zhbc.com.cn/',
 'https://www.guji.com.cn/',
 'http://www.shsjcb.com/',
]
qs = ['虞氏易集义 乾卦 刘大钧 维普 cqvip.com doc journal',
      '周易研究 chinajournal.net.cn paperDigest 摘要 关键词 刘大钧 虞氏易集义',
      '简帛网 bsm.org.cn 《简帛》 第二十辑 目录',
      '出土文献 2021年第1期 目录 清华大学出土文献研究与保护中心 中西书局 杂志',
      'Early China Cambridge Core article "Excavated" manuscript Zhouyi hexagram early-china article',
      "brill.com view journals tpao article 2022 Yijing OR Zhouyi OR Yi jing OR divination",
      '中华书局 周易 图书 出版时间 ISBN 9787101 zhbc.com.cn 易学',
      '上海古籍出版社 图书 易学 出版时间 guji.com.cn 周易 新著 2019']
with ThreadPoolExecutor(8) as ex:
    fr = list(ex.map(F, urls))
    sr = list(ex.map(S, qs))
for u, st, t in fr:
    print('F', st, '|', u[:110], '\n    ', t)
for q, rs in sr:
    print('S', q)
    for r in rs: print('   ', ' | '.join(r))
