import json, sys, re
from concurrent.futures import ThreadPoolExecutor
from lib import *

def F(u, n=300):
    try:
        s = fetch(u, route='probe8')
    except BaseException as e:
        return (u, 'EXC '+repr(e)[:100], '', None)
    raw = s['raw']; t = snap_text(s)
    err = isinstance(raw, dict) and 'error' in raw
    return (u, ('ERR ' if err else 'ok  ')+str(len(t)), t[:n].replace('\n',' / '), t)

def S(q, count=8):
    try:
        s = search(q, count, route='probe8')
    except BaseException as e:
        return (q, [('EXC', repr(e)[:100], '')])
    res = s['raw'].get('results') or []
    return (q, [((r.get('title') or '')[:50].replace('\n',' '), (r.get('url') or '')[:200], (r.get('snippet') or '')[:60].replace('\n',' ')) for r in res[:count]])

# 1. full old-CNKI article page
d = json.load(open('snapshots/fetch_ec167cd6c8.json')) # placeholder to keep imports quiet
import glob
for fn in glob.glob('snapshots/fetch_*.json'):
    dd = json.load(open(fn, encoding='utf-8'))
    if dd['url'].endswith('CJFDTotal-ZYJY201805003.htm'):
        t = snap_text(dd); i = t.find('【相似文献】'); print('OLD CNKI 2018-05-003 similar-lit section:\n', t[i:i+700]); break

urls = [
 'https://www.ctwx.tsinghua.edu.cn/ctwx/qkml/2.htm',
 'https://www.ctwx.tsinghua.edu.cn/ctwx/qkml/1.htm',
 'https://wap.cnki.net/touch/web/Journal/Article/ZYJY201805003.html',
 'https://wap.cnki.net/touch/web/Journal/Info/CUWX.html',
 'http://search.cnki.com.cn/cjfd/Detail/Navi/CUWX',
 'http://www.zhbc.com.cn/zhsj/fg/home/searchcontent.html?conds=9787101003529&type=1',
 'http://www.zhbc.com.cn/zhsj/fg/home/searchcontent.html?conds=9787101115673&type=1',
 'http://opac.nlc.cn/F/?func=find-b&find_code=ISB&request=9787547516911',
 'http://opac.nlc.cn/F/?func=find-b&find_code=ISB&request=9787532583171',
 'https://book.cnki.net/book?id=1893855',
 'http://www.bsm.org.cn/?xinx/',
 'http://m.bsm.org.cn/?xinx/',
 'https://ci.nii.ac.jp/books/search?isbn=9787547516911',
 'https://ci.nii.ac.jp/books/opensearch/search?isbn=9787532583171&format=json&count=2',
]
qs = ['Early China Cambridge Core "MOZI AND THE GHOSTS" Gibas ming 明 article',
      "T'oung Pao Jenco Chen Di investigations ancient pronunciations Mao odes brill.com",
      '中国哲学史 编辑部 目录 philosophychina.cssn.cn 2019年第2期',
      '清华大学出土文献研究与保护中心 出土文献 期刊目录 2022年第1期 目录 ctwx.tsinghua.edu.cn']
with ThreadPoolExecutor(8) as ex:
    fr = list(ex.map(F, urls))
    sr = list(ex.map(S, qs))
for u, st, t, full in fr:
    print('F', st, '|', u[:120], '\n    ', t)
for q, rs in sr:
    print('S', q)
    for r in rs: print('   ', ' | '.join(r))
# Cambridge listing structure
for u, st, t, full in fr: pass
d = fetch('https://www.cambridge.org/core/journals/early-china/listing?pageNum=8')
t = snap_text(d); i = t.find('EAC volume 40 Cover'); print('CAMB LISTING sample:\n', t[i:i+1500])
