#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""build_keys.py

Verified answer-key builder for battery 2 (bibliographic recall of Chinese
scholarship on the Yijing / Zhouyi, excavated manuscripts, early Chinese texts).

Stages (each resumable from files under ./state and ./snapshots):
  harvest : DeepSeek search over journal TOCs + publisher/catalogue lists -> candidates
  build   : two independent PRIMARY records per candidate, snapshots saved,
            DeepSeek Flash extraction (OpenRouter), verbatim field check,
            comparison in code; any mismatch drops the item
  clue    : three writers (Sonnet 5.5 and Opus 5.5 via OpenRouter; DeepSeek Flash
            via DeepSeek's own Anthropic-compatible endpoint) each write a clue
            for the same verified key
  check   : code leakage check, code anchor/decade/work-type check, DeepSeek
            identifiability (key in top 10), optional different-family top-10 check
  verify  : blind batches of 10 (writer labels stripped, shuffled) to Opus 5.5;
            any flagged clue is dropped, never repaired
  report  : items.jsonl, dropped.jsonl, REPORT.md (calls.jsonl written live)

Only the Python standard library is used for HTTP.  Nothing is installed.
`opencc` is used only if it is already importable; otherwise a small built-in
traditional->simplified table is used.
"""

import argparse
import datetime
import hashlib
import json
import os
import random
import re
import sys
import time
import traceback
import urllib.error
import urllib.request

# --------------------------------------------------------------------------- #
# paths
# --------------------------------------------------------------------------- #

ROOT = os.path.dirname(os.path.abspath(__file__))
SNAP = os.path.join(ROOT, "snapshots")
STATE = os.path.join(ROOT, "state")
for _d in (SNAP, STATE):
    os.makedirs(_d, exist_ok=True)

CAND = os.path.join(STATE, "candidates.jsonl")
HQ = os.path.join(STATE, "harvest_queries.jsonl")
EXTR = os.path.join(STATE, "extractions.jsonl")
BUILT = os.path.join(STATE, "built.jsonl")
CLUES = os.path.join(STATE, "clues.jsonl")
CHECKS = os.path.join(STATE, "checks.jsonl")
VERIFY = os.path.join(STATE, "verifications.jsonl")
TOOLIDX = os.path.join(STATE, "tool_index.jsonl")
CALLS = os.path.join(ROOT, "calls.jsonl")
ITEMS = os.path.join(ROOT, "items.jsonl")
DROPPED = os.path.join(ROOT, "dropped.jsonl")
REPORT = os.path.join(ROOT, "REPORT.md")

# --------------------------------------------------------------------------- #
# endpoints / models
# --------------------------------------------------------------------------- #

OR_URL = "https://openrouter.ai/api/v1/chat/completions"
DS_SEARCH_URL = "https://api.deepseek.com/v1/tools/search"
DS_FETCH_URL = "https://api.deepseek.com/v1/tools/fetch"
DS_ANTH_URL = "https://api.deepseek.com/anthropic/v1/messages"

EXTRACT_MODEL = "deepseek/deepseek-v4.1-flash-1017:exacto"

WRITERS = {
    "sonnet": {"kind": "openrouter", "model": "anthropic/claude-sonnet-5.5"},
    "opus": {"kind": "openrouter", "model": "anthropic/claude-opus-5.5"},
    "deepseek": {"kind": "deepseek_anthropic", "model": "deepseek-flash"},
}
WRITER_ORDER = ["sonnet", "opus", "deepseek"]

VERIFIER_MODEL = "anthropic/claude-opus-5.5"
FAMILY_MODEL = "anthropic/claude-sonnet-5.5"

PRIMARY_CLASSES = {"journal_toc", "publisher", "library_catalog", "aggregator", "front_matter"}
BLOCK_HOSTS = (
    "ctext.org", "baike.baidu.com", "wikipedia.org", "zhihu.com", "douban.com",
    "sohu.com", "163.com", "sina.com.cn", "qq.com", "jianshu.com", "csdn.net",
    "bilibili.com", "youtube.com", "facebook.com", "twitter.com",
)

# --------------------------------------------------------------------------- #
# traditional -> simplified
# --------------------------------------------------------------------------- #

try:  # only if already importable; we never install anything
    from opencc import OpenCC as _OpenCC  # type: ignore
    _OPENCC = _OpenCC("t2s")
except Exception:  # noqa: BLE001
    _OPENCC = None

_T2S_PAIRS = (
    "萬万", "與与", "專专", "業业", "東东", "絲丝", "兩两", "嚴严", "喪丧", "個个",
    "豐丰", "臨临", "為为", "麗丽", "舉举", "義义", "烏乌", "樂乐", "喬乔", "習习",
    "鄉乡", "書书", "買买", "亂乱", "爭争", "於于", "虧亏", "雲云", "亞亚", "產产",
    "畝亩", "親亲", "億亿", "僅仅", "從从", "侖仑", "倉仓", "儀仪", "們们", "價价",
    "眾众", "優优", "夥伙", "會会", "傘伞", "偉伟", "傳传", "傷伤", "倫伦", "偽伪",
    "體体", "餘余", "傭佣", "僉佥", "俠侠", "侶侣", "僥侥", "偵侦", "側侧", "僑侨",
    "儉俭", "債债", "傾倾", "償偿", "儲储", "兒儿", "兌兑", "黨党", "蘭兰", "關关",
    "興兴", "養养", "獸兽", "內内", "岡冈", "冊册", "寫写", "軍军", "農农", "馮冯",
    "衝冲", "決决", "況况", "凍冻", "淨净", "涼凉", "減减", "湊凑", "凜凛", "幾几",
    "鳳凤", "憑凭", "凱凯", "擊击", "鑿凿", "芻刍", "劃划", "劉刘", "則则", "剛刚",
    "創创", "刪删", "別别", "剎刹", "劊刽", "劌刿", "劍剑", "劑剂", "辦办", "務务",
    "動动", "勵励", "勁劲", "勞劳", "勢势", "勳勋", "勻匀", "匯汇", "區区", "醫医",
    "華华", "協协", "單单", "賣卖", "盧卢", "衛卫", "卻却", "廠厂", "廳厅", "歷历",
    "厲厉", "壓压", "厭厌", "參参", "雙双", "發发", "變变", "敘叙", "葉叶", "號号",
    "嘆叹", "嘰叽", "嚇吓", "嗎吗", "啟启", "吳吴", "員员", "聽听", "嗆呛", "嗚呜",
    "詠咏", "響响", "啞哑", "喚唤", "問问", "術术", "樸朴", "機机", "殺杀", "雜杂",
    "權权", "條条", "來来", "楊杨", "極极", "構构", "槍枪", "樣样", "樁桩", "樞枢",
    "標标", "棧栈", "樓楼", "欖榄", "歐欧", "殘残", "殼壳", "毀毁", "氣气", "漢汉",
    "湯汤", "溝沟", "滅灭", "滬沪", "滾滚", "滿满", "漁渔", "滲渗", "漸渐", "漿浆",
    "潑泼", "潔洁", "灑洒", "潤润", "澗涧", "漲涨", "潛潜", "澤泽", "濁浊", "濃浓",
    "瀉泻", "瀾澜", "濤涛", "澀涩", "灣湾", "濕湿", "燈灯", "靈灵", "災灾", "爐炉",
    "點点", "煉炼", "爛烂", "爾尔", "牆墙", "獨独", "獲获", "獎奖", "環环", "現现",
    "瑪玛", "璽玺", "畫画", "暢畅", "療疗", "盡尽", "監监", "蓋盖", "盤盘", "盜盗",
    "盞盏", "睜睁", "礦矿", "碼码", "礎础", "確确", "礙碍", "禮礼", "禍祸", "離离",
    "種种", "稱称", "積积", "穩稳", "窮穷", "竊窃", "競竞", "筆笔", "節节", "範范",
    "築筑", "簡简", "籃篮", "類类", "糧粮", "約约", "級级", "紀纪", "純纯", "納纳",
    "紙纸", "紛纷", "細细", "終终", "組组", "結结", "絕绝", "統统", "經经", "綠绿",
    "維维", "網网", "綱纲", "緣缘", "編编", "練练", "縮缩", "繳缴", "繼继", "續续",
    "線线", "縣县", "總总", "縱纵", "纖纤", "罰罚", "罷罢", "羅罗", "翹翘", "聰聪",
    "聲声", "職职", "聯联", "肅肃", "腸肠", "膚肤", "膠胶", "臉脸", "舊旧", "艱艰",
    "艷艳", "藝艺", "莊庄", "蒼苍", "蓮莲", "蔣蒋", "蔥葱", "蕭萧", "薑姜", "薦荐",
    "薩萨", "藍蓝", "藥药", "蘇苏", "蘊蕴", "處处", "虛虚", "蟲虫", "蝕蚀", "補补",
    "裝装", "裡里", "褲裤", "襲袭", "見见", "規规", "視视", "覺觉", "觀观", "覽览",
    "訂订", "計计", "訊讯", "記记", "講讲", "許许", "論论", "設设", "訪访", "證证",
    "評评", "詞词", "譯译", "試试", "詩诗", "話话", "詳详", "誌志", "認认", "語语",
    "誠诚", "誤误", "說说", "誰谁", "課课", "調调", "談谈", "請请", "諾诺", "謀谋",
    "謂谓", "謝谢", "識识", "譜谱", "議议", "護护", "讀读", "讓让", "讚赞", "豬猪",
    "貝贝", "負负", "財财", "貢贡", "貧贫", "貨货", "販贩", "貪贪", "責责", "貴贵",
    "貸贷", "費费", "貼贴", "資资", "賓宾", "賜赐", "賞赏", "賠赔", "賢贤", "賤贱",
    "賦赋", "質质", "賬账", "賭赌", "賴赖", "購购", "賽赛", "贊赞", "贈赠", "趙赵",
    "趕赶", "趨趋", "躍跃", "蹤踪", "車车", "軌轨", "軒轩", "軟软", "軸轴", "較较",
    "載载", "輔辅", "輕轻", "輛辆", "輝辉", "輩辈", "輪轮", "輸输", "轉转", "轟轰",
    "辭辞", "邊边", "遼辽", "達达", "遷迁", "選选", "遺遗", "邁迈", "還还", "這这",
    "進进", "遠远", "適适", "遲迟", "鄧邓", "鄭郑", "鄰邻", "釋释", "釀酿", "針针",
    "釘钉", "釣钓", "鈴铃", "鉛铅", "銀银", "銅铜", "銘铭", "銷销", "鋒锋", "鋼钢",
    "錄录", "錢钱", "錦锦", "錫锡", "鍋锅", "鍵键", "鍾钟", "鎖锁", "鏈链", "鏡镜",
    "鐘钟", "鐵铁", "鑄铸", "鑑鉴", "長长", "門门", "閃闪", "閉闭", "開开", "閏闰",
    "閑闲", "間间", "閔闵", "閘闸", "閣阁", "閥阀", "閱阅", "闊阔", "闡阐", "陽阳",
    "陰阴", "陳陈", "陸陆", "隊队", "階阶", "隨随", "險险", "隱隐", "隸隶", "難难",
    "雛雏", "電电", "靜静", "韋韦", "韓韩", "頁页", "頂顶", "項项", "順顺", "須须",
    "頌颂", "預预", "頗颇", "領领", "頻频", "頭头", "頰颊", "頸颈", "題题", "顏颜",
    "願愿", "顧顾", "顯显", "風风", "飛飞", "飢饥", "飯饭", "飲饮", "飾饰", "館馆",
    "饑饥", "馬马", "駐驻", "駕驾", "驗验", "騎骑", "騙骗", "驅驱", "驕骄", "髮发",
    "鬥斗", "魚鱼", "魯鲁", "鮮鲜", "鯉鲤", "鳥鸟", "鳴鸣", "鴻鸿", "鵬鹏", "鶴鹤",
    "鷹鹰", "麥麦", "黃黄", "齊齐", "齒齿", "龍龙", "龜龟", "龔龚",
)
_T2S_MAP = {}
for _p in _T2S_PAIRS:
    if len(_p) == 2:
        _T2S_MAP[_p[0]] = _p[1]


def to_simp(s):
    if not s:
        return ""
    if _OPENCC is not None:
        try:
            return _OPENCC.convert(s)
        except Exception:  # noqa: BLE001
            pass
    return "".join(_T2S_MAP.get(c, c) for c in s)


# --------------------------------------------------------------------------- #
# normalisation / matching
# --------------------------------------------------------------------------- #

_ROLE_WORDS = ("主编", "编著", "编", "著", "译", "校", "整理", "点校", "撰", "等",
               "ed.", "eds.", "ed", "editor", "edited", "trans.", "translated")
_CJK = r"\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff"


def norm(s):
    """traditional->simplified, lower-case, punctuation and whitespace stripped."""
    s = to_simp(s or "")
    s = s.lower()
    s = re.sub(r"[\W_]+", "", s)
    return s


def strip_roles(s):
    s = s or ""
    for w in _ROLE_WORDS:
        s = s.replace(w, " ")
    return s


def first_year(s):
    m = re.search(r"(1[6-9]\d{2}|20\d{2})", str(s or ""))
    return int(m.group(1)) if m else None


def authors_match(a, b):
    a = strip_roles(a or "")
    b = strip_roles(b or "")
    if not norm(a) or not norm(b):
        return False
    if norm(a) == norm(b):
        return True
    split = re.compile(r"[;；,，、/|]")
    sa = {norm(x) for x in split.split(a) if norm(x)}
    sb = {norm(x) for x in split.split(b) if norm(x)}
    if sa and sb and sa == sb:
        return True
    return False


def title_match(a, b):
    na, nb = norm(a), norm(b)
    if not na or not nb:
        return False
    if na == nb:
        return True
    if len(na) >= 8 and len(nb) >= 8 and (na in nb or nb in na):
        return True
    la = re.sub(r"[^a-z]", "", to_simp(a or "").lower())
    lb = re.sub(r"[^a-z]", "", to_simp(b or "").lower())
    if la and la == lb:
        return True
    return False


_VENUE_SUFFIX = ("出版社", "有限公司", "有限责任公司", "出版公司", "杂志社", "编辑部",
                 "press", "publishing", "publishers", "publisher", "university")


def venue_match(a, b):
    na, nb = norm(a), norm(b)
    if not na or not nb:
        return False
    if na == nb:
        return True
    sa, sb = to_simp(a or "").lower(), to_simp(b or "").lower()
    for suf in _VENUE_SUFFIX:
        sa = sa.replace(suf, "")
        sb = sb.replace(suf, "")
    na2, nb2 = norm(sa), norm(sb)
    if na2 and na2 == nb2:
        return True
    if min(len(na2), len(nb2)) >= 6 and (na2 in nb2 or nb2 in na2):
        return True
    return na == nb


def cn_3grams(s):
    out = set()
    for run in re.findall(r"[%s]+" % _CJK, s or ""):
        for i in range(len(run) - 2):
            out.add(run[i:i + 3])
    return out


def en_words(s):
    return re.findall(r"[a-z0-9']+", to_simp(s or "").lower())


def en_2grams(s):
    w = en_words(s)
    return {(w[i], w[i + 1]) for i in range(len(w) - 1)}


def stable_int(s):
    return int(hashlib.sha256(str(s).encode("utf-8")).hexdigest()[:12], 16)


def stable_choice(items, key):
    return items[stable_int(key) % len(items)]


# --------------------------------------------------------------------------- #
# io helpers
# --------------------------------------------------------------------------- #

def today():
    return datetime.date.today().isoformat()


def now_iso():
    return datetime.datetime.now().isoformat(timespec="seconds")


def read_jsonl(path):
    out = []
    if not os.path.exists(path):
        return out
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                out.append(json.loads(line))
            except Exception:  # noqa: BLE001
                continue
    return out


def append_jsonl(path, obj):
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(obj, ensure_ascii=False) + "\n")


def parse_json_loose(t):
    if not t:
        return None
    t = t.strip()
    t = re.sub(r"^```(?:json)?\s*", "", t)
    t = re.sub(r"\s*```$", "", t)
    i, j = t.find("{"), t.rfind("}")
    if i < 0 or j <= i:
        return None
    frag = t[i:j + 1]
    try:
        return json.loads(frag)
    except Exception:  # noqa: BLE001
        pass
    try:
        return json.loads(frag.replace("'", '"'))
    except Exception:  # noqa: BLE001
        return None


def save_snapshot(kind, key, payload):
    h = hashlib.sha1(key.encode("utf-8")).hexdigest()[:16]
    fn = "%s_%s.json" % (kind, h)
    path = os.path.join(SNAP, fn)
    payload = dict(payload)
    payload.setdefault("date", today())
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False)
    return fn


# --------------------------------------------------------------------------- #
# http
# --------------------------------------------------------------------------- #

def http_post(url, headers, body, timeout=180, retries=2):
    data = json.dumps(body, ensure_ascii=False).encode("utf-8")
    hdrs = dict(headers)
    hdrs.setdefault("Accept", "application/json")
    last = None
    for attempt in range(retries + 1):
        try:
            req = urllib.request.Request(url, data=data, headers=hdrs, method="POST")
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                raw = resp.read().decode("utf-8", "replace")
            try:
                return json.loads(raw)
            except Exception:  # noqa: BLE001
                return {"_raw": raw}
        except urllib.error.HTTPError as e:
            try:
                body_txt = e.read().decode("utf-8", "replace")[:2000]
            except Exception:  # noqa: BLE001
                body_txt = ""
            last = {"_http_error": e.code, "_body": body_txt}
            if e.code in (429, 500, 502, 503, 504) and attempt < retries:
                time.sleep(2 + 2 * attempt)
                continue
            return last
        except (urllib.error.URLError, TimeoutError, ConnectionError, OSError) as e:
            last = {"_error": repr(e)}
            if attempt < retries:
                time.sleep(2 + 2 * attempt)
                continue
            return last
    return last or {"_error": "unknown"}


def ds_headers():
    return {
        "Authorization": "Bearer " + os.environ.get("DEEPSEEK_API_KEY", "placeholder"),
        "Content-Type": "application/json",
    }


def or_headers():
    return {
        "Authorization": "Bearer " + os.environ.get("OPENROUTER_API_KEY", "placeholder"),
        "Content-Type": "application/json",
        "HTTP-Referer": "https://localhost/battery2-keys",
        "X-Title": "battery2-keys",
    }


def ds_anth_headers():
    return {
        "x-api-key": os.environ.get("DEEPSEEK_API_KEY", "placeholder"),
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    }


# --------------------------------------------------------------------------- #
# cost ledger
# --------------------------------------------------------------------------- #

class BudgetExceeded(Exception):
    pass


class Ledger:
    def __init__(self, path):
        self.path = path
        self.total = 0.0
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                for line in f:
                    try:
                        self.total += float(json.loads(line).get("cost_usd") or 0.0)
                    except Exception:  # noqa: BLE001
                        continue

    def add(self, rec):
        c = float(rec.get("cost_usd") or 0.0)
        self.total += c
        with open(self.path, "a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")


LEDGER = None
MAX_USD = 5.0


def budget_hit():
    return LEDGER.total >= (MAX_USD - 1e-9)


def log_call(stage, tag, model, gen, usage, cost, cost_source, extra=None):
    rec = {
        "ts": now_iso(),
        "stage": stage,
        "tag": tag,
        "model": model,
        "gen": gen,
        "usage": usage or {},
        "cost_usd": float(cost or 0.0),
        "cost_source": cost_source,
    }
    if extra:
        rec.update(extra)
    LEDGER.add(rec)
    return rec


def or_cost(usage):
    """BYOK -> upstream_inference_cost; otherwise usage.cost. Never both."""
    if not isinstance(usage, dict):
        return 0.0, "none"
    cd = usage.get("cost_details") or {}
    up = cd.get("upstream_inference_cost") if isinstance(cd, dict) else None
    c = usage.get("cost")
    if isinstance(up, (int, float)) and up > 0:
        return float(up), "upstream"
    if isinstance(c, (int, float)) and c > 0:
        return float(c), "usage.cost"
    return 0.0, "zero"


def ds_cost(usage):
    if not isinstance(usage, dict):
        return 0.0, "none"
    for k in ("cost", "total_cost", "upstream_inference_cost"):
        v = usage.get(k)
        if isinstance(v, (int, float)) and v > 0:
            return float(v), "api." + k
    cd = usage.get("cost_details")
    if isinstance(cd, dict):
        for k, v in cd.items():
            if isinstance(v, (int, float)) and v > 0:
                return float(v), "api.cost_details." + k
    pin = os.environ.get("DEEPSEEK_FLASH_INPUT_USD_PER_MTOK")
    pout = os.environ.get("DEEPSEEK_FLASH_OUTPUT_USD_PER_MTOK")
    if pin and pout:
        it = usage.get("input_tokens") or usage.get("prompt_tokens") or 0
        ot = usage.get("output_tokens") or usage.get("completion_tokens") or 0
        return (float(it) * float(pin) + float(ot) * float(pout)) / 1e6, "env_prices"
    return 0.0, "tokens_only"


# --------------------------------------------------------------------------- #
# model wrappers
# --------------------------------------------------------------------------- #

def _msg_text(m):
    c = m.get("content")
    if isinstance(c, str):
        return c
    if isinstance(c, list):
        return "".join(p.get("text", "") for p in c if isinstance(p, dict))
    return ""


def or_chat(model, provider, prompt, stage, tag, effort="max", max_tokens=3000):
    if budget_hit():
        raise BudgetExceeded()
    body = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": max_tokens,
        "provider": provider,
        "reasoning": {"effort": effort},
        "usage": {"include": True},
        "cache_control": {"type": "ephemeral"},
    }
    r = http_post(OR_URL, or_headers(), body)
    if not isinstance(r, dict) or "_error" in r or "_http_error" in r or "choices" not in r:
        log_call(stage, tag + ":error", model, None, {}, 0.0, "error",
                 {"error": json.dumps(r, ensure_ascii=False)[:600]})
        return None, None
    txt = _msg_text((r.get("choices") or [{}])[0].get("message") or {})
    usage = r.get("usage") or {}
    cost, src = or_cost(usage)
    log_call(stage, tag, model, r.get("id"), usage, cost, src)
    return txt, r.get("id")


def ds_anthropic(prompt, stage, tag, max_tokens=None, budget=None):
    if budget_hit():
        raise BudgetExceeded()
    if budget is not None and max_tokens is not None:
        ladder = [(budget, max_tokens)]
    else:
        ladder = [(32000, 40000), (16000, 24000), (8000, 12000), (0, 2000)]
    last_err = None
    for bt, mt in ladder:
        body = {
            "model": "deepseek-flash",
            "max_tokens": mt,
            "messages": [{"role": "user", "content": prompt}],
            "cache_control": {"type": "ephemeral"},
        }
        if bt > 0:
            body["thinking"] = {"type": "enabled", "budget_tokens": bt}
        r = http_post(DS_ANTH_URL, ds_anth_headers(), body)
        if isinstance(r, dict) and ("_http_error" in r or "_error" in r):
            last_err = r
            if r.get("_http_error") in (400, 404, 422):
                continue
            log_call(stage, tag + ":error", "deepseek-flash", None, {}, 0.0, "error",
                     {"error": json.dumps(r, ensure_ascii=False)[:600],
                      "thinking_budget": bt, "max_tokens": mt})
            return None, None
        parts = r.get("content") or []
        txt = "".join(p.get("text", "") for p in parts
                      if isinstance(p, dict) and p.get("type") == "text")
        usage = r.get("usage") or {}
        cost, src = ds_cost(usage)
        log_call(stage, tag, "deepseek-flash", r.get("id"), usage, cost, src,
                 {"thinking_budget": bt, "max_tokens": mt})
        return txt, r.get("id")
    log_call(stage, tag + ":error", "deepseek-flash", None, {}, 0.0, "error",
             {"error": json.dumps(last_err, ensure_ascii=False)[:600]})
    return None, None


# --------------------------------------------------------------------------- #
# DeepSeek tools
# --------------------------------------------------------------------------- #

def ds_search(query, count=10, offset=None, tag="search"):
    body = {"query": query, "count": count, "need_content": False}
    if offset:
        body["offset"] = int(offset)
    r = http_post(DS_SEARCH_URL, ds_headers(), body)
    used_offset = offset
    if isinstance(r, dict) and r.get("_http_error") == 400 and offset:
        body.pop("offset", None)
        r = http_post(DS_SEARCH_URL, ds_headers(), body)
        used_offset = None
    results = []
    if isinstance(r, dict):
        results = r.get("results") or r.get("data") or []
        if isinstance(results, dict):
            results = results.get("results") or results.get("items") or []
    results = [x for x in results if isinstance(x, dict)]
    sfile = save_snapshot("s", query + "|" + str(count) + "|" + str(used_offset),
                          {"kind": "search", "query": query, "count": count,
                           "offset": used_offset, "response": r})
    append_jsonl(TOOLIDX, {"kind": "search", "query": query, "file": sfile,
                           "date": today(), "offset": used_offset,
                           "n": len(results), "tag": tag})
    return results, sfile


def ds_fetch(url, tag="fetch"):
    r = http_post(DS_FETCH_URL, ds_headers(), {"url": url})
    text = None
    if isinstance(r, dict):
        c = r.get("content")
        if isinstance(c, str):
            text = c
        if text is None:
            d = r.get("data")
            if isinstance(d, dict):
                text = d.get("content") or d.get("text")
        if text is None and isinstance(r.get("text"), str):
            text = r["text"]
    if not isinstance(text, str):
        text = None
    sfile = save_snapshot("f", url, {"kind": "fetch", "url": url, "response": r})
    append_jsonl(TOOLIDX, {"kind": "fetch", "url": url, "file": sfile,
                           "date": today(), "ok": bool(text), "tag": tag})
    return text, sfile


# --------------------------------------------------------------------------- #
# custodian classification
# --------------------------------------------------------------------------- #

def host_of(url):
    m = re.match(r"https?://([^/]+)", url or "")
    return (m.group(1) if m else "").lower()


def custodian_class(url):
    u = (url or "").lower()
    h = host_of(u)
    if any(d in h for d in ("cnki.net", "wanfangdata", "cqvip.com", "vip.com", "cqvip")):
        return "aggregator"
    if any(d in h for d in ("nlc.cn", "opac", "catalog", "cir.nii.ac.jp", "cinii",
                            "worldcat", "loc.gov", "ndl.go.jp", "lib.")):
        return "library_catalog"
    if any(d in h for d in ("cambridge.org", "brill.com", "shsjcb.com", "press.",
                            "publish", "books.", "oup.com", "tandfonline", "springer")):
        return "publisher"
    if any(d in h for d in ("sdu.edu.cn", "tsinghua.edu.cn", "journal", "cnjournals",
                            "xueshu", "periodical")):
        return "journal_toc"
    if any(d in h for d in ("front", "matter", "image")):
        return "front_matter"
    return "other"


def independent(a, b):
    if a["custodian_class"] not in PRIMARY_CLASSES:
        return False
    if b["custodian_class"] not in PRIMARY_CLASSES:
        return False
    if a["custodian_class"] == b["custodian_class"]:
        return False
    # two aggregators never count as a pair
    if a["custodian_class"] == "aggregator" and b["custodian_class"] == "aggregator":
        return False
    if a.get("route") == b.get("route") and str(a.get("route", "")).startswith("title"):
        return False
    return True


# --------------------------------------------------------------------------- #
# extraction
# --------------------------------------------------------------------------- #

FIELDS = ["author", "title", "venue", "year", "volume_issue"]
REQ = ["author", "title", "venue", "year"]
EXTRACT_CHARS = 20000

EXTRACT_PROMPT = """You read ONE saved snapshot of a PRIMARY bibliographic record: a journal table of contents or article page, a publisher catalogue page, a library catalogue record, or a CNKI/VIP/Wanfang item page showing full fields.

Return ONLY a JSON object with exactly these keys:
{"author": "...", "title": "...", "venue": "...", "year": "YYYY", "volume_issue": "...", "abstract_or_keywords": "...", "language": "zh" or "en", "work_type": "article"|"book"|"chapter"|"edited_volume"|"unknown"}

Rules:
- Copy characters EXACTLY as printed in the snapshot. Do not convert traditional to simplified, do not translate, do not fix typos, do not add punctuation.
- author: names as printed, multiple authors separated by "; ". Editors as "ed. NAME".
- venue: for an article the journal name exactly as printed; for a book the publisher name.
- year: four digits, the publication year of THIS record (not a citation year, not a dynasty year).
- volume_issue: e.g. "2019年第3期" or "vol. 12 no. 2"; "" if none.
- abstract_or_keywords: the abstract or keywords text as printed, copied verbatim, max 1200 characters; "" if absent.
- If a field is absent from the snapshot, use "".
- Never guess. Never use outside knowledge.
- If the snapshot is a list of many records, extract the one whose title best matches the TITLE HINT.

TITLE HINT (may be empty; ignore if empty): {hint}

SNAPSHOT:
<<<
{snapshot}
>>>
"""


def all_required(verified):
    return [f for f in REQ if not verified.get(f)]


def get_extraction(snapshot_file, text, hint, cache):
    if snapshot_file in cache:
        return cache[snapshot_file]
    prompt = EXTRACT_PROMPT.replace("{hint}", hint or "").replace(
        "{snapshot}", (text or "")[:EXTRACT_CHARS])
    txt, _gen = or_chat(EXTRACT_MODEL, {"zdr": True}, prompt,
                        stage="build", tag="extract:" + snapshot_file,
                        effort="max", max_tokens=1500)
    obj = parse_json_loose(txt) or {}
    raw = {k: (obj.get(k) if isinstance(obj.get(k), str) else "") for k in FIELDS}
    ntext = norm(text)
    verified = {}
    for k in FIELDS:
        v = (raw.get(k) or "").strip()
        if not v:
            verified[k] = ""
            continue
        nv = norm(v)
        if nv and nv in ntext:
            verified[k] = v
        elif k == "volume_issue":
            verified[k] = ""
        else:
            verified[k] = ""
    abstract = (obj.get("abstract_or_keywords") or "").strip()
    if abstract and len(abstract) > 40:
        head = norm(abstract[:60])
        if head and head not in ntext:
            abstract = ""
    rec = {
        "snapshot_file": snapshot_file,
        "raw": raw,
        "verified": verified,
        "abstract": abstract[:1500],
        "language": (obj.get("language") or "").strip().lower()[:2] or "",
        "work_type": (obj.get("work_type") or "unknown").strip().lower(),
        "date": today(),
    }
    append_jsonl(EXTR, rec)
    cache[snapshot_file] = rec
    return rec


# --------------------------------------------------------------------------- #
# stage: harvest
# --------------------------------------------------------------------------- #

JOURNALS = ["周易研究", "中国哲学史", "简帛", "出土文献", "Early China", "T'oung Pao"]
PUBLISHERS = ["上海古籍出版社", "中华书局", "文物出版社", "中西书局",
              "社会科学文献出版社", "Cambridge University Press", "Brill"]
TOPICS = ["易学", "周易", "清华简", "简帛", "出土文献", "早期中国", "early China",
          "manuscript", "Yijing"]


def harvest_queries(n, seed):
    rng = random.Random(seed)
    qs = []
    for j in JOURNALS:
        for _ in range(6):
            y = rng.randint(1995, 2024)
            i = rng.randint(1, 6)
            qs.append("%s %d年第%d期 目录 篇名 作者" % (j, y, i))
            qs.append("%s %d年 总第%d期 目次" % (j, y, i))
    for p in PUBLISHERS:
        for _ in range(4):
            t = rng.choice(TOPICS)
            qs.append("%s %s 著者 出版日期 目录" % (p, t))
    rng.shuffle(qs)
    return qs[:n]


def blocked_host(url):
    h = host_of(url)
    return any(b in h for b in BLOCK_HOSTS)


def stage_harvest(args):
    done_q = {r.get("query") for r in read_jsonl(HQ)}
    existing = {r.get("url") for r in read_jsonl(CAND)}
    qs = harvest_queries(args.harvest_queries, args.seed)
    for q in qs:
        if budget_hit():
            raise BudgetExceeded()
        if q in done_q:
            continue
        if len(existing) >= args.target * 4:
            break
        rng = random.Random(stable_int(q) ^ args.seed)
        offset = rng.randint(2, 20)
        try:
            results, _sf = ds_search(q, 10, offset=offset, tag="harvest")
        except Exception:  # noqa: BLE001
            traceback.print_exc()
            results = []
        for rank, r in enumerate(results[:10], start=1):
            url = (r.get("url") or "").strip()
            if not url or url in existing:
                continue
            if blocked_host(url):
                append_jsonl(DROPPED, {"cid": "", "url": url, "rule": "blocked_host",
                                       "detail": host_of(url), "date": today()})
                continue
            cid = hashlib.sha1(url.encode("utf-8")).hexdigest()[:12]
            cand = {
                "cid": cid,
                "url": url,
                "title_hint": (r.get("title") or "").strip(),
                "snippet": (r.get("snippet") or r.get("description") or "")[:400],
                "query": q,
                "rank": rank,
                "offset": offset,
                "custodian_class": custodian_class(url),
                "source": "harvest",
                "date": today(),
            }
            append_jsonl(CAND, cand)
            existing.add(url)
        append_jsonl(HQ, {"query": q, "offset": offset, "date": today(),
                          "n": len(results)})
        print("[harvest] %s -> %d results (candidates: %d)" % (q[:50], len(results), len(existing)),
              file=sys.stderr)


# --------------------------------------------------------------------------- #
# stage: build (two records, extract, compare)
# --------------------------------------------------------------------------- #

def build_secondary_query(ex, attempt):
    v = ex["verified"]
    venue = v.get("venue") or ""
    year = first_year(v.get("year") or "")
    vi = v.get("volume_issue") or ""
    if not venue:
        return None
    parts = ['"%s"' % venue]
    if year:
        parts.append(str(year))
    if vi:
        parts.append(vi)
    if attempt == 0:
        parts.append("目录")
    elif attempt == 1:
        parts.append("篇名 作者 页码")
    else:
        parts.append("文献 题录")
    return " ".join(parts)


def find_secondary(ex, class_a, hint, seed):
    """Search a non-title route and return a fetched, title-confirming record."""
    for attempt in range(3):
        q = build_secondary_query(ex, attempt)
        if not q:
            return None
        rng = random.Random(stable_int(q) ^ seed)
        try:
            results, _sf = ds_search(q, 10, offset=rng.randint(2, 12), tag="secondary")
        except Exception:  # noqa: BLE001
            results = []
        shortlist = []
        for r in results[:10]:
            url = (r.get("url") or "").strip()
            if not url:
                continue
            cls = custodian_class(url)
            if cls not in PRIMARY_CLASSES or cls == "aggregator" and class_a == "aggregator":
                continue
            if cls == class_a:
                continue
            shortlist.append({"url": url, "custodian_class": cls,
                              "route": "issue_browse_query"})
        for cand in shortlist[:4]:
            if budget_hit():
                raise BudgetExceeded()
            text, sfile = ds_fetch(cand["url"], tag="secondary")
            if not text or len(text) < 200:
                continue
            if norm(ex["verified"]["title"]) not in norm(text):
                continue
            cand["snapshot_file"] = sfile
            cand["date"] = today()
            cand["text"] = text
            return cand
    return None


def compare_records(a, b):
    fa, fb = a["verified"], b["verified"]
    mism = []
    if not authors_match(fa["author"], fb["author"]):
        mism.append("author")
    if not title_match(fa["title"], fb["title"]):
        mism.append("title")
    if not venue_match(fa["venue"], fb["venue"]):
        mism.append("venue")
    ya, yb = first_year(fa["year"]), first_year(fb["year"])
    if not (ya and yb and ya == yb):
        mism.append("year")
    return mism


def stage_build(args):
    cache = {r["snapshot_file"]: r for r in read_jsonl(EXTR) if r.get("snapshot_file")}
    seen = {r["cid"] for r in read_jsonl(BUILT)}
    ok_count = sum(1 for r in read_jsonl(BUILT) if r.get("status") == "ok")
    goal = max(args.target, 10) * 2
    cands = read_jsonl(CAND)
    cands.sort(key=lambda c: c.get("cid", ""))
    for c in cands:
        if budget_hit():
            raise BudgetExceeded()
        if c["cid"] in seen:
            continue
        if ok_count >= goal:
            break
        seen.add(c["cid"])
        cls = c.get("custodian_class") or custodian_class(c["url"])
        if cls not in PRIMARY_CLASSES:
            append_jsonl(BUILT, {"cid": c["cid"], "status": "drop",
                                 "rule": "unclassifiable_custodian",
                                 "detail": cls, "url": c["url"], "date": today()})
            continue
        # ---- record A
        text_a, sfile_a = ds_fetch(c["url"], tag="primary_A")
        if not text_a or len(text_a) < 200:
            append_jsonl(BUILT, {"cid": c["cid"], "status": "drop",
                                 "rule": "unfetchable_source", "url": c["url"],
                                 "detail": "A", "date": today()})
            continue
        ex_a = get_extraction(sfile_a, text_a, c.get("title_hint") or "", cache)
        miss_a = all_required(ex_a["verified"])
        if miss_a:
            append_jsonl(BUILT, {"cid": c["cid"], "status": "drop",
                                 "rule": "field_not_verbatim:" + ",".join(miss_a),
                                 "url": c["url"], "detail": "A", "date": today()})
            continue
        rec_a = {"url": c["url"], "custodian_class": cls,
                 "route": "title_query_from_harvest",
                 "snapshot_file": sfile_a, "date": today()}
        # ---- record B
        b = find_secondary(ex_a, cls, c.get("title_hint") or "", args.seed)
        if not b:
            append_jsonl(BUILT, {"cid": c["cid"], "status": "drop",
                                 "rule": "no_second_independent_record",
                                 "url": c["url"], "detail": "B", "date": today()})
            continue
        if not independent(rec_a, b):
            append_jsonl(BUILT, {"cid": c["cid"], "status": "drop",
                                 "rule": "not_independent", "url": c["url"],
                                 "detail": b["custodian_class"], "date": today()})
            continue
        ex_b = get_extraction(b["snapshot_file"], b["text"], ex_a["verified"]["title"], cache)
        miss_b = all_required(ex_b["verified"])
        if miss_b:
            append_jsonl(BUILT, {"cid": c["cid"], "status": "drop",
                                 "rule": "field_not_verbatim_B:" + ",".join(miss_b),
                                 "url": b["url"], "detail": "B", "date": today()})
            continue
        mism = compare_records(ex_a, ex_b)
        if mism:
            append_jsonl(BUILT, {"cid": c["cid"], "status": "drop",
                                 "rule": "field_mismatch:" + ",".join(mism),
                                 "url": c["url"], "detail": mism, "date": today()})
            continue
        key = {
            "author": ex_a["verified"]["author"],
            "title": ex_a["verified"]["title"],
            "venue": ex_a["verified"]["venue"],
            "year": str(first_year(ex_a["verified"]["year"]) or ex_a["verified"]["year"]),
            "volume_issue": ex_a["verified"].get("volume_issue")
                             or ex_b["verified"].get("volume_issue") or "",
        }
        abstract = ex_a.get("abstract") or ex_b.get("abstract") or ""
        lang = ex_a.get("language") or ex_b.get("language") or \
               ("en" if re.search(r"[A-Za-z]", key["title"]) else "zh")
        item = {
            "cid": c["cid"],
            "status": "ok",
            "key": key,
            "abstract": abstract,
            "language": "en" if lang.startswith("en") else "zh",
            "work_type": ex_a.get("work_type") or "unknown",
            "records": [
                {"url": rec_a["url"], "custodian_class": rec_a["custodian_class"],
                 "route": rec_a["route"], "snapshot_file": rec_a["snapshot_file"],
                 "date": rec_a["date"]},
                {"url": b["url"], "custodian_class": b["custodian_class"],
                 "route": b["route"], "snapshot_file": b["snapshot_file"],
                 "date": b["date"]},
            ],
            "evidence": [(text_a or "")[:800], (b.get("text") or "")[:800]],
            "date": today(),
        }
        append_jsonl(BUILT, item)
        ok_count += 1
        print("[build] ok %s | %s" % (c["cid"], key["title"][:40]), file=sys.stderr)


# --------------------------------------------------------------------------- #
# stage: clue
# --------------------------------------------------------------------------- #

FIELD_OF = [
    (("易学", "周易", "易經", "易经", "yijing", "zhouyi"), "易学与经学"),
    (("简", "帛", "出土", "清华简", "manuscript"), "出土文献与简帛"),
    (("哲学", "思想", "儒", "道", "philosoph"), "中国哲学"),
    (("史", "history", "汉", "秦"), "早期中国史"),
]


def guess_field(key):
    blob = (key.get("title", "") + " " + key.get("venue", "")).lower()
    for needles, label in FIELD_OF:
        if any(n.lower() in blob for n in needles):
            return label
    return "早期中国研究"


def decade_of(year):
    try:
        y = int(year)
    except Exception:  # noqa: BLE001
        return None
    return (y // 10) * 10


def first_author(a):
    parts = [p.strip() for p in re.split(r"[;；,，、]", a or "") if p.strip()]
    return parts[0] if parts else (a or "").strip()


def anchor_for(cid, key):
    kind = "author" if stable_int(cid) % 2 == 0 else "venue"
    val = first_author(key["author"]) if kind == "author" else key["venue"]
    return kind, val


CLUE_PROMPT = """You write ONE short research-recall question (a "clue") about a real scholarly work, for an evaluation of bibliographic recall on early Chinese texts.

Write in {lang}. Return ONLY the clue text, one or two sentences, no preamble, no quotation marks around the whole thing.

The clue MUST contain:
1. the work type ({work_type_word});
2. the field or subject area ({field});
3. a PARAPHRASE of the topic taken from the abstract/keywords below - never copy a run of characters from the title;
4. EXACTLY ONE anchor, and only one: {anchor_kind} = {anchor_value};
5. a decade, written like {decade_example}.

The clue MUST NOT contain: the title, any three-character run from the title, the exact year, the volume/issue number, the author's other works, or the name of the city of publication.
Do not mention the work by name. Do not give the answer. Do not ask a question whose answer is the title.

WORK TYPE: {work_type}
FIELD: {field}
ANCHOR ({anchor_kind}): {anchor_value}
DECADE: {decade}
TOPIC (abstract/keywords copied from the primary record):
{kb}

Return only the clue text.
"""


def write_clue(writer, item, anchor_kind, anchor_value, decade):
    key = item["key"]
    lang = item.get("language", "zh")
    if lang == "en":
        decade_example = "the %ds" % decade
        work_type_word = "article" if item.get("work_type") in ("article", "") else "book"
    else:
        decade_example = "%d年代" % decade
        work_type_word = "论文" if item.get("work_type") in ("article", "") else "专著/著作"
    prompt = CLUE_PROMPT.format(
        lang="English" if lang == "en" else "Chinese",
        work_type_word=work_type_word,
        field=guess_field(key),
        anchor_kind="author" if anchor_kind == "author" else "journal or publisher",
        anchor_value=anchor_value,
        decade_example=decade_example,
        decade="%d年代" % decade if lang != "en" else "the %ds" % decade,
        work_type=item.get("work_type") or "unknown",
        kb=(item.get("abstract") or "")[:1500] or "(no abstract; use the title's topic only as a subject area, and do not copy the title)",
    )
    spec = WRITERS[writer]
    if spec["kind"] == "openrouter":
        txt, gen = or_chat(spec["model"], {"only": ["anthropic"]}, prompt,
                           stage="clue", tag="clue:" + writer,
                           effort="max", max_tokens=1200)
    else:
        txt, gen = ds_anthropic(prompt, "clue", "clue:" + writer)
    if not txt:
        return None
    txt = txt.strip().strip('"').strip("“”").strip()
    if not txt:
        return None
    return {"cid": item["cid"], "writer": writer, "clue": txt,
            "anchor_kind": anchor_kind, "anchor_value": anchor_value,
            "decade": decade, "lang": lang, "model": spec["model"],
            "gen": gen, "date": today()}


def stage_clue(args):
    writers = [w for w in args.writers.split(",") if w]
    for w in writers:
        if w not in WRITERS:
            raise SystemExit("unknown writer: %s" % w)
    done = {(r["cid"], r["writer"]) for r in read_jsonl(CLUES)}
    built = [b for b in read_jsonl(BUILT) if b.get("status") == "ok"]
    built.sort(key=lambda b: b["cid"])
    for item in built:
        dec = decade_of(item["key"]["year"])
        if dec is None:
            append_jsonl(DROPPED, {"cid": item["cid"], "url": "",
                                   "rule": "no_year_for_decade", "date": today()})
            continue
        ak, av = anchor_for(item["cid"], item["key"])
        for w in writers:
            if (item["cid"], w) in done:
                continue
            if budget_hit():
                raise BudgetExceeded()
            rec = write_clue(w, item, ak, av, dec)
            if rec:
                append_jsonl(CLUES, rec)
                done.add((item["cid"], w))
                print("[clue] %s %s ok" % (item["cid"], w), file=sys.stderr)
            else:
                append_jsonl(DROPPED, {"cid": item["cid"], "url": "",
                                       "rule": "clue_writer_error:%s" % w,
                                       "date": today()})
                done.add((item["cid"], w))


# --------------------------------------------------------------------------- #
# stage: check (leakage, anchor, decade, identifiability, family)
# --------------------------------------------------------------------------- #

TYPE_WORDS = ("论文", "文章", "专著", "著作", "研究", "书", "article", "book",
              "monograph", "study", "paper", "volume", "chapter")

FAMILY_PROMPT = """A clue is meant to identify exactly ONE real scholarly work.
Below is the clue and the top-10 search results it returned for its own text.
The key is at index {key_idx}. You can never approve the item; you can only widen or drop it.

Decide:
- "drop": true if the clue is ambiguous, misdescribes the work, or fits several works equally well;
- "other_acceptable_keys": at most 2 other result indices that an expert would also accept as fitting the clue.

Reply ONLY JSON: {{"drop": false, "other_acceptable_keys": [], "reason": ""}}

CLUE: {clue}
RESULTS:
{results}
"""


def leakage_cn(clue, title):
    tc = cn_3grams(title)
    if not tc:
        return None
    cl = cn_3grams(clue)
    shared = tc & cl
    return sorted(shared)[0] if shared else None


def leakage_en(clue, title):
    tt = en_2grams(title)
    if not tt:
        return None
    cc = en_2grams(clue)
    shared = tt & cc
    return " ".join(sorted(shared)[0]) if shared else None


def decade_present(clue, decade):
    s = clue
    pats = []
    pats.append(re.compile(r"(\d{4})\s*(?:年代|s\b|'s)"))
    pats.append(re.compile(r"(\d{2})\s*世纪\s*(\d{1,2})\s*年代"))
    for p in pats:
        for m in p.finditer(s):
            if m.lastindex == 1:
                try:
                    v = int(m.group(1))
                except Exception:  # noqa: BLE001
                    continue
                if v in (decade, decade // 100 * 100):
                    return True
                if len(m.group(1)) == 2:
                    if (1900 + v) // 10 * 10 == decade:
                        return True
            else:
                try:
                    c = int(m.group(1))
                    y = int(m.group(2))
                except Exception:  # noqa: BLE001
                    continue
                if (c - 1) * 100 + y == decade:
                    return True
    return False


def match_rank(results, item):
    title = item["key"]["title"]
    urls = {r.get("url", "").split("#")[0] for r in item.get("records", [])}
    nt = norm(title)
    for i, r in enumerate(results[:10], start=1):
        url = (r.get("url") or "").split("#")[0]
        rt = r.get("title") or ""
        rs = r.get("snippet") or r.get("description") or ""
        if url and url in urls:
            return i
        if title_match(title, rt):
            return i
        if nt and nt in norm(rt + " " + rs):
            return i
    return None


def stage_check(args):
    writers = [w for w in args.writers.split(",") if w]
    built = {b["cid"]: b for b in read_jsonl(BUILT) if b.get("status") == "ok"}
    done = {(r["cid"], r["writer"]) for r in read_jsonl(CHECKS)}
    clues = [c for c in read_jsonl(CLUES) if c.get("writer") in writers and c.get("cid") in built]
    clues.sort(key=lambda c: (c["cid"], c["writer"]))
    for c in clues:
        key = (c["cid"], c["writer"])
        if key in done:
            continue
        if budget_hit():
            raise BudgetExceeded()
        item = built[c["cid"]]
        title = item["key"]["title"]
        rec = {"cid": c["cid"], "writer": c["writer"], "date": today(),
               "status": "ok", "rule": "", "detail": "",
               "recoverability": None, "extra_acceptable_keys": []}
        cn = leakage_cn(c["clue"], title)
        if cn:
            rec.update(status="drop", rule="clue_leakage_cn", detail=cn)
            append_jsonl(CHECKS, rec)
            done.add(key)
            continue
        en = leakage_en(c["clue"], title)
        if en:
            rec.update(status="drop", rule="clue_leakage_en", detail=en)
            append_jsonl(CHECKS, rec)
            done.add(key)
            continue
        if norm(c["anchor_value"]) not in norm(c["clue"]):
            rec.update(status="drop", rule="clue_missing_anchor",
                       detail=c["anchor_kind"])
            append_jsonl(CHECKS, rec)
            done.add(key)
            continue
        if not decade_present(c["clue"], c["decade"]):
            rec.update(status="drop", rule="clue_decade_mismatch",
                       detail=str(c["decade"]))
            append_jsonl(CHECKS, rec)
            done.add(key)
            continue
        if not any(w in c["clue"].lower() for w in TYPE_WORDS):
            rec.update(status="drop", rule="clue_missing_work_type")
            append_jsonl(CHECKS, rec)
            done.add(key)
            continue
        if len(c["clue"]) < 15 or len(c["clue"]) > 600:
            rec.update(status="drop", rule="clue_length", detail=str(len(c["clue"])))
            append_jsonl(CHECKS, rec)
            done.add(key)
            continue
        # ---- identifiability: the key must appear in the top 10
        rng = random.Random(stable_int(c["clue"]) ^ args.seed)
        try:
            results, _sf = ds_search(c["clue"], 10,
                                     offset=rng.randint(2, 10), tag="ident")
        except Exception:  # noqa: BLE001
            results = []
        rank = match_rank(results, item)
        if not rank:
            rec.update(status="drop", rule="identifiability_failed",
                       detail="not in top 10")
            rec["top10"] = [{"url": r.get("url"), "title": r.get("title")}
                            for r in results[:10]]
            append_jsonl(CHECKS, rec)
            done.add(key)
            continue
        rec["recoverability"] = {"query": c["clue"], "rank": rank}
        # ---- different-family top-10 comparison (may only widen or drop)
        if args.family_check:
            idx = rank - 1
            top = "\n".join(
                "%d. %s | %s" % (i, (r.get("title") or "")[:120],
                                 (r.get("snippet") or r.get("description") or "")[:200])
                for i, r in enumerate(results[:10]))
            prompt = FAMILY_PROMPT.format(key_idx=idx, clue=c["clue"], results=top)
            txt, _gen = or_chat(FAMILY_MODEL, {"only": ["anthropic"]}, prompt,
                                stage="check", tag="family", effort="low",
                                max_tokens=500)
            obj = parse_json_loose(txt) or {}
            if obj.get("drop") is True:
                rec.update(status="drop", rule="family_check_dropped",
                           detail=str(obj.get("reason", ""))[:200])
                append_jsonl(CHECKS, rec)
                done.add(key)
                continue
            extra = obj.get("other_acceptable_keys") or []
            extras = []
            for e in extra:
                try:
                    i = int(e)
                except Exception:  # noqa: BLE001
                    continue
                if 0 <= i < len(results):
                    extras.append({"url": results[i].get("url"),
                                   "title": results[i].get("title")})
            rec["extra_acceptable_keys"] = extras
        append_jsonl(CHECKS, rec)
        done.add(key)
        print("[check] %s %s -> %s" % (c["cid"], c["writer"], rec["status"]),
              file=sys.stderr)


# --------------------------------------------------------------------------- #
# stage: verify (blind Opus batches of 10)
# --------------------------------------------------------------------------- #

VERIFY_PROMPT = """You audit bibliographic answer keys for an evaluation. Each item below has a claimed key (author / title / venue / year / volume-issue), the two primary-record URLs it was built from, short excerpts from those snapshots, and a recall clue written from the key.

Flag an item if ANY of:
- the key fields are not supported by the excerpts;
- the key is internally inconsistent (e.g. a year impossible for the venue);
- the clue misdescribes the work (wrong work type, wrong field, a decade that contradicts the year, more than one anchor);
- the clue leaks the title, or the work is recoverable from the clue without knowing it.

You never repair anything. You only flag.

Return ONLY a JSON object:
{"results":[{"i":<index>,"flag":true|false,"reason":"<short>"}, ...]}
One entry per item, in the order given. No other text.

ITEMS:
{items}
"""


def stage_verify(args):
    writers = [w for w in args.writers.split(",") if w]
    built = {b["cid"]: b for b in read_jsonl(BUILT) if b.get("status") == "ok"}
    checks = {(r["cid"], r["writer"]): r for r in read_jsonl(CHECKS)}
    done = {(r["cid"], r["writer"]) for r in read_jsonl(VERIFY)
            if r.get("flag") in (True, False)}
    pending = []
    for (cid, w), ch in checks.items():
        if w not in writers or cid not in built:
            continue
        if ch.get("status") != "ok":
            continue
        if (cid, w) in done:
            continue
        pending.append((cid, w))
    pending.sort()
    for start in range(0, len(pending), 10):
        if budget_hit():
            raise BudgetExceeded()
        chunk = pending[start:start + 10]
        rng = random.Random(stable_int("batch%d" % start) ^ args.seed)
        rng.shuffle(chunk)  # blind: writer labels stripped, order shuffled
        lines = []
        for i, (cid, w) in enumerate(chunk):
            it = built[cid]
            key = it["key"]
            ev = it.get("evidence") or ["", ""]
            lines.append(
                "ITEM %d\n"
                "author: %s\ntitle: %s\nvenue: %s\nyear: %s\nvolume_issue: %s\n"
                "record_urls: %s | %s\nevidence_excerpt_1: %s\nevidence_excerpt_2: %s\n"
                "clue: %s\n" % (
                    i, key.get("author"), key.get("title"), key.get("venue"),
                    key.get("year"), key.get("volume_issue"),
                    it["records"][0].get("url"), it["records"][1].get("url"),
                    (ev[0] if len(ev) > 0 else "")[:700],
                    (ev[1] if len(ev) > 1 else "")[:700],
                    checks[(cid, w)].get("recoverability", {}).get("query", "")))
        prompt = VERIFY_PROMPT.format(items="\n".join(lines))
        txt, _gen = or_chat(VERIFIER_MODEL, {"only": ["anthropic"]}, prompt,
                            stage="verify", tag="verify", effort="max",
                            max_tokens=2000)
        obj = parse_json_loose(txt) or {}
        res = obj.get("results") if isinstance(obj.get("results"), list) else None
        if not res:
            append_jsonl(VERIFY, {"batch": start, "error": "unparsable",
                                  "raw": (txt or "")[:800], "date": today()})
            continue
        by_i = {}
        for r in res:
            if isinstance(r, dict):
                try:
                    by_i[int(r.get("i"))] = r
                except Exception:  # noqa: BLE001
                    continue
        for i, (cid, w) in enumerate(chunk):
            r = by_i.get(i)
            if r is None:
                continue
            append_jsonl(VERIFY, {
                "cid": cid, "writer": w, "batch": start,
                "flag": bool(r.get("flag")),
                "reason": str(r.get("reason", ""))[:300],
                "date": today(),
            })
        print("[verify] batch %d -> %d items" % (start, len(chunk)), file=sys.stderr)


# --------------------------------------------------------------------------- #
# assembly + report
# --------------------------------------------------------------------------- #

def assemble(args):
    writers = [w for w in args.writers.split(",") if w]
    built = {b["cid"]: b for b in read_jsonl(BUILT) if b.get("status") == "ok"}
    clues = {(c["cid"], c["writer"]): c for c in read_jsonl(CLUES)}
    checks = {(r["cid"], r["writer"]): r for r in read_jsonl(CHECKS)}
    verif = {}
    for r in read_jsonl(VERIFY):
        if r.get("flag") in (True, False):
            verif[(r["cid"], r["writer"])] = r
    items, drops = [], []
    for cid, it in sorted(built.items()):
        surviving = []
        for w in writers:
            c = clues.get((cid, w))
            ch = checks.get((cid, w))
            if not c:
                drops.append({"cid": cid, "writer": w, "rule": "no_clue", "date": today()})
                continue
            if not ch or ch.get("status") != "ok":
                drops.append({"cid": cid, "writer": w,
                              "rule": (ch or {}).get("rule", "no_check"),
                              "detail": (ch or {}).get("detail", ""), "date": today()})
                continue
            v = verif.get((cid, w))
            if not v:
                drops.append({"cid": cid, "writer": w, "rule": "unverified",
                              "date": today()})
                continue
            if v.get("flag"):
                drops.append({"cid": cid, "writer": w, "rule": "opus_flagged",
                              "detail": v.get("reason", ""), "date": today()})
                continue
            surviving.append({
                "writer": w,
                "clue": c["clue"],
                "recoverability": ch.get("recoverability"),
                "extra_acceptable_keys": ch.get("extra_acceptable_keys", []),
                "anchor": {"kind": c["anchor_kind"], "value": c["anchor_value"]},
            })
        if not surviving:
            drops.append({"cid": cid, "writer": "*",
                          "rule": "all_writer_clues_rejected", "date": today()})
            continue
        year = first_year(it["key"]["year"])
        item = {
            "id": cid,
            "stratum": {
                "fame": "unknown",
                "type": ("article" if it.get("work_type") == "article"
                         else "book" if it.get("work_type") in ("book", "edited_volume")
                         else "unknown"),
                "language": it.get("language", "zh"),
                "decade": "%ds" % (year // 10 * 10) if year else "unknown",
            },
            "key": it["key"],
            "records": it["records"],
            "clue": surviving[0]["clue"],
            "recoverability": surviving[0]["recoverability"],
            "extra_acceptable_keys": surviving[0]["extra_acceptable_keys"],
            "clues": {s["writer"]: {"clue": s["clue"],
                                    "recoverability": s["recoverability"],
                                    "extra_acceptable_keys": s["extra_acceptable_keys"],
                                    "anchor": s["anchor"]} for s in surviving},
            "verified_batch": True,
            "date": today(),
        }
        items.append(item)
    items.sort(key=lambda x: x["id"])
    if args.target and len(items) > args.target:
        for extra in items[args.target:]:
            drops.append({"cid": extra["id"], "writer": "*",
                          "rule": "beyond_target", "date": today()})
        items = items[:args.target]
    return items, drops


def stratum_counts(items):
    out = {}
    for dim in ("fame", "type", "language", "decade"):
        c = {}
        for it in items:
            v = it["stratum"].get(dim, "unknown")
            c[v] = c.get(v, 0) + 1
        out[dim] = c
    return out


def rule_counts(drops):
    c = {}
    for d in drops:
        base = (d.get("rule") or "?").split(":")[0]
        c[base] = c.get(base, 0) + 1
    return dict(sorted(c.items(), key=lambda kv: -kv[1]))


def stage_report(args):
    global LEDGER
    if LEDGER is None:
        LEDGER = Ledger(CALLS)
    items, drops = assemble(args)
    # persist
    with open(ITEMS, "w", encoding="utf-8") as f:
        for it in items:
            f.write(json.dumps(it, ensure_ascii=False) + "\n")
    all_drops = list(drops)
    for d in read_jsonl(BUILT):
        if d.get("status") == "drop":
            all_drops.append({"cid": d["cid"], "writer": "",
                              "rule": d.get("rule", "?"),
                              "detail": str(d.get("detail", ""))[:200],
                              "url": d.get("url", ""), "date": d.get("date", today())})
    with open(DROPPED, "w", encoding="utf-8") as f:
        for d in all_drops:
            f.write(json.dumps(d, ensure_ascii=False) + "\n")

    calls = read_jsonl(CALLS)
    toolcalls = read_jsonl(TOOLIDX)
    n_search = sum(1 for t in toolcalls if t.get("kind") == "search")
    n_fetch = sum(1 for t in toolcalls if t.get("kind") == "fetch")
    total_cost = sum(float(c.get("cost_usd") or 0.0) for c in calls)
    by_model = {}
    for c in calls:
        m = c.get("model") or "?"
        d = by_model.setdefault(m, {"calls": 0, "cost": 0.0, "tokens_in": 0,
                                    "tokens_out": 0})
        d["calls"] += 1
        d["cost"] += float(c.get("cost_usd") or 0.0)
        u = c.get("usage") or {}
        d["tokens_in"] += int(u.get("prompt_tokens") or u.get("input_tokens") or 0)
        d["tokens_out"] += int(u.get("completion_tokens") or u.get("output_tokens") or 0)

    writers = [w for w in args.writers.split(",") if w]
    clues = read_jsonl(CLUES)
    checks = {(r["cid"], r["writer"]): r for r in read_jsonl(CHECKS)}
    verif = {(r["cid"], r["writer"]): r for r in read_jsonl(VERIFY)
             if r.get("flag") in (True, False)}
    wrows = []
    for w in writers:
        produced = [c for c in clues if c.get("writer") == w]
        leak_ok = 0
        ident_ok = 0
        acc = 0
        flagged = 0
        for c in produced:
            ch = checks.get((c["cid"], w))
            if not ch:
                continue
            if ch.get("status") == "ok":
                leak_ok += 1
                if ch.get("recoverability"):
                    ident_ok += 1
                v = verif.get((c["cid"], w))
                if v and not v.get("flag"):
                    acc += 1
            elif not str(ch.get("rule", "")).startswith("identifiability"):
                pass
            if ch.get("rule", "").startswith("clue_leakage"):
                pass
            v = verif.get((c["cid"], w))
            if v and v.get("flag"):
                flagged += 1
        # leakage pass = status ok OR later failed on identifiability/family
        leak_pass = sum(1 for c in produced
                        if (checks.get((c["cid"], w)) or {}).get("rule", "")
                        not in ("clue_leakage_cn", "clue_leakage_en",
                                "clue_missing_anchor", "clue_decade_mismatch",
                                "clue_missing_work_type", "clue_length"))
        cost = sum(float(c.get("cost_usd") or 0.0) for c in calls
                   if str(c.get("tag", "")).startswith("clue:" + w))
        wrows.append({"writer": w, "produced": len(produced),
                      "leak_pass": leak_pass, "ident_pass": ident_ok,
                      "flagged": flagged, "accepted": acc, "cost": cost,
                      "cost_per": (cost / acc) if acc else None})

    # disagreements between writers on the same item
    by_item = {}
    for c in clues:
        by_item.setdefault(c["cid"], {})[c["writer"]] = c
    dis = []
    for cid, ws in by_item.items():
        if len(ws) < 2:
            continue
        statuses = {}
        for w, c in ws.items():
            ch = checks.get((cid, w)) or {}
            v = verif.get((cid, w)) or {}
            if ch.get("status") != "ok":
                statuses[w] = "check:" + str(ch.get("rule"))
            elif v.get("flag"):
                statuses[w] = "opus_flag"
            else:
                statuses[w] = "ok"
        vals = set(statuses.values())
        if len(vals) > 1:
            dis.append({"cid": cid, "statuses": statuses,
                        "clues": {w: c["clue"][:300] for w, c in ws.items()}})

    built_ok = sum(1 for b in read_jsonl(BUILT) if b.get("status") == "ok")
    ncand = len(read_jsonl(CAND))
    lines = []
    lines.append("# Answer-key build report\n")
    lines.append("Generated %s. Work directory `%s`.\n" % (now_iso(), ROOT))
    lines.append("Flags: target=%s max_usd=%s stage=%s writers=%s seed=%s family_check=%s\n"
                 % (args.target, args.max_usd, args.stage, args.writers,
                    args.seed, args.family_check))
    lines.append("\n## Funnel\n\n")
    lines.append("| step | n |\n|---|---|\n")
    lines.append("| candidates harvested | %d |\n" % ncand)
    lines.append("| candidates with two comparable independent records | %d |\n" % built_ok)
    lines.append("| items with >=1 accepted clue | %d |\n" % len(items))
    lines.append("| dropped entries recorded | %d |\n" % len(all_drops))
    lines.append("\n## Counts by stratum (accepted items)\n\n")
    sc = stratum_counts(items)
    for dim in ("fame", "type", "language", "decade"):
        lines.append("**%s**\n\n" % dim)
        for k, v in sorted(sc[dim].items(), key=lambda kv: -kv[1]):
            lines.append("- %s: %d\n" % (k, v))
        lines.append("\n")
    lines.append("\n## Drop rules\n\n")
    lines.append("| rule | n |\n|---|---|\n")
    for k, v in rule_counts(all_drops).items():
        lines.append("| %s | %d |\n" % (k, v))
    lines.append("\n## Per-writer comparison\n\n")
    lines.append("| writer | clues produced | passed leakage | passed identifiability "
                 "| flagged by Opus | accepted | cost USD | cost / accepted clue |\n")
    lines.append("|---|---|---|---|---|---|---|---|\n")
    for r in wrows:
        cpa = ("%.4f" % r["cost_per"]) if r["cost_per"] is not None else "n/a"
        lines.append("| %s | %d | %d | %d | %d | %d | %.4f | %s |\n" % (
            r["writer"], r["produced"], r["leak_pass"], r["ident_pass"],
            r["flagged"], r["accepted"], r["cost"], cpa))
    lines.append("\n## Disagreements between writers on the same item (examples)\n\n")
    if not dis:
        lines.append("_None recorded._\n")
    else:
        for d in dis[:8]:
            lines.append("**%s**\n\n" % d["cid"])
            lines.append("- statuses: `%s`\n" % json.dumps(d["statuses"], ensure_ascii=False))
            for w, c in d["clues"].items():
                lines.append("- %s: %s\n" % (w, c.replace("\n", " ")))
            lines.append("\n")
    lines.append("\n## Cost\n\n")
    lines.append("Total model spend so far: **$%.4f** (cap $%.2f).\n\n"
                 % (total_cost, args.max_usd))
    lines.append("DeepSeek tool calls (not charged against the model budget): "
                 "%d search, %d fetch.\n\n" % (n_search, n_fetch))
    lines.append("| model | calls | input tokens | output tokens | cost USD |\n")
    lines.append("|---|---|---|---|---|\n")
    for m, d in sorted(by_model.items(), key=lambda kv: -kv[1]["cost"]):
        lines.append("| %s | %d | %d | %d | %.4f |\n"
                     % (m, d["calls"], d["tokens_in"], d["tokens_out"], d["cost"]))
    ds_calls = [c for c in calls if c.get("model") == "deepseek-flash"]
    tokens_only = [c for c in ds_calls if c.get("cost_source") == "tokens_only"]
    lines.append("\nDeepSeek own-API calls: %d. Of these, %d had no published price "
                 "returned; their tokens are logged in `calls.jsonl` and their cost "
                 "is counted as 0. Set `DEEPSEEK_FLASH_INPUT_USD_PER_MTOK` / "
                 "`DEEPSEEK_FLASH_OUTPUT_USD_PER_MTOK` and re-run the report to price "
                 "them.\n" % (len(ds_calls), len(tokens_only)))
    lines.append("\n## What this run could not do\n\n")
    lines.append("- **Fame stratification**: CNKI citation counts and catalogue "
                 "holdings are not exposed by the available search/fetch tools, so "
                 "`stratum.fame` is recorded as `unknown` for every item. The other "
                 "three dimensions (type, language, decade) are recorded; the item "
                 "set is not balanced on the design's 20/40/40 fame split.\n")
    lines.append("- **Random offsets**: the search tool exposes no offset parameter. "
                 "A random offset is still sent and recorded; if the endpoint rejects "
                 "it (HTTP 400) the call is retried without it. Randomisation of the "
                 "sample therefore rests mainly on randomised query construction.\n")
    lines.append("- **Same-title-query independence**: retrieval B is issued on a "
                 "venue+year+issue route, never on the title. A record whose custodian "
                 "class cannot be determined is dropped, not guessed.\n")
    lines.append("- Anything the run could not do is stated here; a null result is a "
                 "result.\n")
    with open(REPORT, "w", encoding="utf-8") as f:
        f.write("".join(lines))
    print("[report] %d items, %d drops, $%.4f" % (len(items), len(all_drops),
                                                  total_cost), file=sys.stderr)


# --------------------------------------------------------------------------- #
# main
# --------------------------------------------------------------------------- #

def parse_args(argv=None):
    p = argparse.ArgumentParser(description="build verified answer keys")
    p.add_argument("--target", type=int, default=300,
                   help="items to keep in items.jsonl")
    p.add_argument("--max-usd", type=float, default=5.0,
                   help="stop cleanly when this spend is reached")
    p.add_argument("--stage", default="all",
                   choices=["all", "harvest", "build", "clue", "check",
                            "verify", "report"])
    p.add_argument("--writers", default=",".join(WRITER_ORDER),
                   help="comma-separated subset of: " + ",".join(WRITER_ORDER))
    p.add_argument("--seed", type=int, default=20261104)
    p.add_argument("--harvest-queries", type=int, default=60)
    p.add_argument("--family-check", dest="family_check", action="store_true",
                   default=True, help="run the different-family top-10 comparison")
    p.add_argument("--no-family-check", dest="family_check", action="store_false")
    return p.parse_args(argv)


def main(argv=None):
    global LEDGER, MAX_USD
    args = parse_args(argv)
    MAX_USD = float(args.max_usd)
    LEDGER = Ledger(CALLS)
    print("[start] spent so far $%.4f, cap $%.2f" % (LEDGER.total, MAX_USD),
          file=sys.stderr)
    order = ["harvest", "build", "clue", "check", "verify"]
    stages = order if args.stage == "all" else [args.stage]
    try:
        for st in stages:
            fn = {"harvest": stage_harvest, "build": stage_build,
                  "clue": stage_clue, "check": stage_check,
                  "verify": stage_verify}[st]
            print("[stage] %s" % st, file=sys.stderr)
            fn(args)
    except BudgetExceeded:
        print("[budget] cap $%.2f reached at $%.4f; stopping cleanly"
              % (MAX_USD, LEDGER.total), file=sys.stderr)
    except KeyboardInterrupt:
        print("[interrupt] stopping; progress is saved", file=sys.stderr)
    finally:
        if args.stage in ("all", "report"):
            try:
                stage_report(args)
            except BudgetExceeded:
                stage_report(args)


if __name__ == "__main__":
    main()
