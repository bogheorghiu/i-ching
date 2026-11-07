```python
#!/usr/bin/env python3
"""
build_keys.py - build verified answer keys for Battery 2 (final-design.md A-C, PREREG.md, INSTRUCTIONS.md).

Stages (all resumable from files in the work directory):
  a  harvest candidates from journal TOCs and publisher/catalogue lists (DeepSeek search, random offsets)
  b  record A = the harvested page (fetched, snapshotted); record B = an independent primary record reached by a
     different route (ISSN/issue browse or ISBN) from a different custodian class
  c  field extraction (DeepSeek Flash 1017 via OpenRouter, one call per snapshot); code keeps only fields that
     occur verbatim (after normalisation) in that snapshot
  d  code comparison of the two records (author/title/venue/year; volume_issue if both give it) + recoverability gate
  e  clue writing by up to three writers (Sonnet 5.5 / Opus 5.5 via OpenRouter, DeepSeek Flash via DeepSeek's own
     Anthropic-format API), sent only verified key fields + abstract/keywords; code format checks
  f  leakage check (3-char Chinese / 2-word English overlap with the title) and identifiability (clue search top 10)
  g  blind verification by Opus 5.5 in batches of 10 (writer labels stripped, shuffled); any flag drops

Models never decide that a key is right; every model output is checked by code; each candidate is accepted or
dropped in one pass. Standard library only (opencc used only if already importable).
"""
import argparse, collections, datetime, hashlib, http.client, json, math, os, random, re, socket, sys, threading, time
import unicodedata, urllib.error, urllib.request
from concurrent.futures import ThreadPoolExecutor

# ----------------------------------------------------------------------------- constants
OR_URL = "https://openrouter.ai/api/v1/chat/completions"
DS_SEARCH_URL = "https://api.deepseek.com/v1/tools/search"
DS_FETCH_URL = "https://api.deepseek.com/v1/tools/fetch"
DS_ANTH_URL = "https://api.deepseek.com/anthropic/v1/messages"
EXTRACT_MODEL = "deepseek/deepseek-v4.1-flash-1017:exacto"
SONNET = "anthropic/claude-sonnet-5.5"
OPUS = "anthropic/claude-opus-5.5"
DS_NATIVE_MODEL = "deepseek-flash"
WRITERS = {"sonnet": ("openrouter", SONNET), "opus": ("openrouter", OPUS), "deepseek": ("deepseek_native", DS_NATIVE_MODEL)}
DS_THINK_CANDIDATES = [65536, 32768, 16384, 8192, 4096, 2048, 1024]   # largest first; first accepted is kept
MAX_PAGE_CHARS = 40000
CELLS = {("article", "zh"): 0.48, ("article", "en"): 0.12, ("book", "zh"): 0.32, ("book", "en"): 0.08}
PERIODS = [(1975, 1999), (2000, 2015), (2016, 2025)]
FAME_CIT = (50, 5)       # citations >=50 famous, >=5 mid, else obscure (script's operationalisation)
FAME_HOLD = (100, 10)    # catalogue holdings >=100 famous, >=10 mid, else obscure
KEY_FLAGS = {"field_not_in_excerpt", "records_not_independent", "not_primary"}
ALLOWED_FLAGS = KEY_FLAGS | {"clue_misdescribes", "clue_leaks", "anchor_rule", "other_fitting_work", "other"}

JOURNALS_ZH = [
    dict(name="周易研究", years=(1988, 2025), issues=6, field="易学（《周易》研究）"),
    dict(name="中国哲学史", years=(1992, 2025), issues=4, field=None),
    dict(name="简帛", years=(2006, 2025), issues=2, field="简帛学"),
    dict(name="出土文献", years=(2010, 2025), issues=4, field="出土文献研究"),
]
JOURNALS_EN = [
    dict(name="Early China", years=(1975, 2025), vol0=1974, field="early China studies"),
    dict(name="T'oung Pao", years=(1980, 2025), vol0=1914, field="sinology (early Chinese texts)"),
]
TOPICS_ZH = {"周易": "易学", "易学": "易学", "卦爻辞": "易学", "帛书周易": "易学（出土易类文献）", "清华简": "简帛学",
             "上博简": "简帛学", "郭店楚简": "简帛学", "马王堆帛书": "简帛学", "出土文献": "出土文献研究", "先秦诸子": "先秦思想史"}
TOPICS_EN = {"Yijing": "Yijing studies", "Book of Changes": "Yijing studies", "Zhouyi": "Yijing studies",
             "bamboo manuscripts": "excavated manuscripts", "excavated texts": "excavated manuscripts",
             "Mawangdui": "excavated manuscripts", "Guodian": "excavated manuscripts",
             "early Chinese philosophy": "early Chinese thought"}
PUBLISHERS_ZH = ["上海古籍出版社", "中华书局", "中西书局", "文物出版社", "齐鲁书社", "北京大学出版社", "巴蜀书社", "人民出版社"]
PUBLISHERS_EN = ["Brill", "Cambridge University Press", "SUNY Press", "University of Washington Press",
                 "Columbia University Press", "Harvard University Asia Center", "Routledge"]

BANNED = ("ctext.org", "baike.", "wikipedia.org", "zhihu.com", "douban.com", "360doc", "docin.com", "doc88.com",
          "book118", "wenku.", "bilibili", "weixin.qq", "sohu.com", "sina.com", "163.com", "jd.com", "taobao",
          "dangdang", "amazon.", "kongfz", "goodreads", "wordpress", "blogspot", "medium.com", "academia.edu",
          "researchgate", "scholar.google", "baidu.com")
CLASS_RULES = [
    ("journal_own", ("zhouyi.sdu.edu.cn", "ctwx.tsinghua.edu.cn", "bsm.org.cn", "cambridge.org/core/journals/early-china",
                     "brill.com/view/journals/tpao", "brill.com/view/journals/tp/")),
    ("aggregator", ("cnki.net", "cnki.com.cn", "cqvip.com", "wanfangdata.com.cn", "nssd.cn", "napstic.cn",
                    "jstor.org", "airitilibrary.com", "muse.jhu.edu")),
    ("library", ("nlc.cn", "ci.nii.ac.jp", "cir.nii.ac.jp", "worldcat.org", "catalog.hathitrust.org", "catalog.loc.gov",
                 "opac.", "library.", "lib.", "primo.", "calis.edu.cn", "copac", "searchworks.stanford.edu",
                 "hollis.harvard.edu")),
    ("publisher", ("guji.com.cn", "zhbc.com.cn", "shsjcb.com", "zxpress.com.cn", "wenwu.com", "qlss.com.cn", "pup.cn",
                   "bashu", "brill.com", "cambridge.org/core/books", "cambridge.org", "sunypress.edu", "uwapress.uw.edu",
                   "cup.columbia.edu", "hup.harvard.edu", "routledge.com", "degruyter.com", "press.")),
]

# ----------------------------------------------------------------------------- traditional -> simplified
try:
    from opencc import OpenCC  # used only if already installed; never installed by this script
    try:
        _OCC = OpenCC("t2s")
    except Exception:
        _OCC = OpenCC("t2s.json")
except Exception:
    _OCC = None
_T2S_PAIRS = """學学 經经 傳传 書书 簡简 國国 華华 漢汉 與与 說说 論论 釋释 義义 辭辞 繫系 數数 歷历 曆历 記记 詩诗 禮礼
樂乐 莊庄 齊齐 戰战 時时 館馆 號号 衛卫 張张 陳陈 劉刘 鄭郑 趙赵 錢钱 孫孙 馮冯 蔣蒋 韓韩 楊杨 葉叶 黃黄 吳吴 顧顾 龔龚
譚谭 鄧邓 蕭萧 盧卢 蘇苏 魯鲁 賈贾 嚴严 獻献 圖图 會会 種种 為为 爲为 這这 個个 們们 來来 對对 從从 後后 發发 現现 問问 題题
關关 係系 實实 際际 當当 進进 過过 長长 開开 間间 東东 門门 見见 觀观 視视 親亲 覺觉 變变 讀读 譯译 證证 証证 識识 誤误 語语
詞词 誌志 謂谓 諸诸 講讲 議议 讖谶 譜谱 課课 調调 談谈 訓训 註注 評评 詮诠 試试 計计 訂订 討讨 許许 設设 詁诂 該该 誠诚 話话
認认 讚赞 貞贞 負负 財财 貨货 質质 賦赋 賢贤 資资 買买 賣卖 費费 貴贵 運运 達达 還还 邊边 遷迁 遺遗 選选 遠远 適适 鄉乡 鄰邻
醫医 釐厘 針针 鈔钞 銘铭 銅铜 錄录 錯错 鍾钟 鐘钟 鏡镜 鐵铁 陰阴 陽阳 陸陆 隨随 隱隐 雜杂 離离 雙双 雲云 電电 靈灵 韻韵 頁页
順顺 須须 預预 領领 頌颂 頤颐 顏颜 類类 顯显 風风 飛飞 養养 餘余 馬马 驗验 體体 鬥斗 鳥鸟 鳴鸣 麥麦 黨党 點点 齋斋 齒齿 龍龙
龜龟 億亿 價价 儀仪 優优 儲储 兒儿 內内 兩两 冊册 處处 則则 剛刚 劃划 劍剑 勞劳 勢势 區区 協协 卻却 參参 員员 喪丧 單单 園园
圓圆 團团 執执 堅坚 報报 場场 塊块 墳坟 壇坛 壓压 壽寿 夢梦 奪夺 奮奋 婦妇 寧宁 寫写 寶宝 將将 專专 尋寻 層层 屬属 歲岁 島岛
師师 帶带 幣币 幾几 廟庙 廣广 強强 彈弹 彙汇 徑径 復复 徵征 恆恒 惡恶 愛爱 態态 慶庆 憂忧 憲宪 應应 懷怀 戲戏 據据 擇择 擊击
擬拟 攝摄 敗败 敵敌 斷断 條条 極极 構构 標标 樓楼 樞枢 樣样 樹树 橋桥 機机 檢检 權权 歐欧 歸归 殘残 殺杀 氣气 決决 況况 淺浅
測测 渾浑 湯汤 溝沟 滅灭 滿满 漁渔 潛潜 澤泽 濟济 灣湾 無无 煉炼 熱热 燈灯 營营 爭争 牆墙 狀状 獨独 獲获 環环 瑣琐 產产 畫画
畢毕 異异 疊叠 盡尽 監监 盤盘 眾众 衆众 礎础 祕秘 禪禅 稱称 穀谷 積积 窮穷 竊窃 競竞 筆笔 節节 範范 築筑 簽签 籌筹 糧粮 紀纪
約约 紅红 紋纹 納纳 純纯 紙纸 級级 細细 終终 組组 結结 絕绝 統统 絲丝 綜综 綱纲 網网 緒绪 編编 緣缘 練练 縣县 總总 織织 繪绘
續续 羅罗 聖圣 聞闻 聯联 聲声 職职 聽听 肅肃 腦脑 舉举 舊旧 艱艰 藝艺 藥药 蘭兰 補补 裝装 製制 複复 襲袭 規规 覽览 觸触 訊讯
豐丰 貝贝 賞赏 趨趋 跡迹 蹟迹 輕轻 載载 輯辑 轉转 辦办 農农 迴回 遞递 鄒邹 酈郦 錦锦 閱阅 闡阐 隊队 雖虽 難难 靜静 響响 頭头
願愿 飲饮 驚惊 麗丽 龐庞 灋法 啟启 啓启 敘叙 敍叙 晉晋 晝昼 曉晓 貫贯 錫锡 鑒鉴 鑑鉴 鬱郁 隸隶 頡颉 稅税 禦御 縱纵 衝冲 亂乱
僞伪 偽伪 傷伤 備备 傑杰 倉仓 儉俭 兌兑 廬庐 蘊蕴 蓋盖 萬万 裏里 裡里 誕诞 誦诵 謝谢 譽誉 護护 讓让 賓宾 賴赖 贊赞 輪轮 輔辅
辯辩 邁迈 鄭郑 鈞钧 鎮镇 閉闭 閒闲 闕阙 陣阵 階阶 韋韦 頒颁 頗颇 頻频 飾饰 駁驳 騎骑 鮑鲍 鳳凤 麼么 齡龄 嶽岳 峯峰 巖岩 帥帅
廢废 廳厅 彥彦 徹彻 慮虑 憑凭 懸悬 拋抛 掃扫 採采 揚扬 換换 損损 擴扩 擔担 擁拥 攜携 斂敛 昇升 暢畅 臺台 歡欢 殼壳 沒没 溫温
漸渐 潔洁 濃浓 煙烟 猶犹 獄狱 瑤瑶 瓊琼 畝亩 盜盗 碼码 確确 祿禄 禍祸 穩稳 竇窦 糾纠 紛纷 絡络 綠绿 維维 緊紧 線线 繩绳 纖纤
習习 脈脉 臨临 興兴 薦荐 蟲虫 術术 訪访 詳详 誰谁 謎谜 豈岂 賀贺 賜赐 贈赠 踐践 軍军 較较 輸输 遊游 醜丑 銀银 鋼钢 閣阁 陝陕
隻只 雋隽 霧雾 頂顶 項项 額额 飯饭 馳驰 驅驱 魚鱼 鮮鲜 鴻鸿 鶴鹤 鹽盐 獸兽 譏讥 藍蓝 謀谋 誼谊 鉤钩 顛颠 雞鸡 筍笋 籃篮 罰罚"""
_T2S = {}
for _p in _T2S_PAIRS.split():
    if len(_p) == 2:
        _T2S[ord(_p[0])] = _p[1]

# ----------------------------------------------------------------------------- globals set in setup()
W = SNAP = STATE = CANDS_DIR = EXTRACT_DIR = CLUE_DIR = VERIFY_DIR = None
LEDGER = None
ARGS = None
_LOG_LOCK = threading.Lock()
_DS_PROBE_LOCK = threading.Lock()
_DUP_LOCK = threading.Lock()
_DUPS = {}


class BudgetExceeded(Exception):
    pass


class InfraError(Exception):
    """API/network failure: the call is marked missing; the item stays pending and is retried on the next run."""


def nowiso():
    return datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")


def today():
    return datetime.date.today().isoformat()


def sha(s, n=16):
    return hashlib.sha1(s.encode("utf-8")).hexdigest()[:n]


def jlog(path, obj):
    with _LOG_LOCK:
        with open(path, "a", encoding="utf-8") as f:
            f.write(json.dumps(obj, ensure_ascii=False) + "\n")


def read_jsonl(path):
    out = []
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        out.append(json.loads(line))
                    except Exception:
                        pass
    return out


def write_json(path, obj):
    tmp = f"{path}.tmp{threading.get_ident()}"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=1)
    os.replace(tmp, path)


def read_json(path, default=None):
    if os.path.exists(path):
        try:
            with open(path, encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return default
    return default


# ----------------------------------------------------------------------------- normalisation
def has_cjk(s):
    return bool(re.search(r"[\u3400-\u9fff\uf900-\ufaff]", s or ""))


def t2s(s):
    s = s or ""
    if _OCC is not None:
        try:
            return _OCC.convert(s)
        except Exception:
            pass
    return s.translate(_T2S)


def deaccent(s):
    return "".join(ch for ch in unicodedata.normalize("NFKD", s) if not unicodedata.combining(ch))


def norm(s):
    s = unicodedata.normalize("NFKC", str(s or ""))
    s = deaccent(t2s(s).lower())
    return re.sub(r"[\W_]+", "", s)


AUTH_SPLIT = re.compile(r"\s*(?:[,;，；、/／]|\band\b|&|＆)\s*")
ROLE_ZH = re.compile(r"(主编|编著|编撰|编纂|校注|译注|整理|点校|著|编|撰|译)$")
ROLE_EN = {"ed", "eds", "edited", "by", "trans", "translated", "and", "editor", "editors"}


def author_parts(a):
    return [p.strip() for p in AUTH_SPLIT.split(str(a or "")) if norm(p)]


def author_key(a):
    s = deaccent(t2s(unicodedata.normalize("NFKC", str(a or ""))).lower())
    cjk = set()
    for p in author_parts(s):
        if has_cjk(p):
            q = ROLE_ZH.sub("", re.sub(r"[^\u3400-\u9fff\uf900-\ufaff]", "", p))
            if q:
                cjk.add(q)
    latin = sorted(t for t in re.findall(r"[a-z]+", re.sub(r"[\u3400-\u9fff]", " ", s)) if t not in ROLE_EN)
    return (frozenset(cjk), tuple(latin))


def venue_key(v):
    n = norm(v)
    return n[3:] if n.startswith("the") else n


def digits_seq(s):
    return tuple(int(x) for x in re.findall(r"\d+", str(s or "")))


def sanitize(s):
    """Strip phone/email/IP-like strings (the OpenRouter guardrail would redact them anyway, e.g. ISBNs)."""
    s = str(s or "")
    s = re.sub(r"[\w.+-]+@[\w-]+\.[\w.]+", "[email]", s)
    s = re.sub(r"\b\d{1,3}(?:\.\d{1,3}){3}\b", "[ip]", s)
    s = re.sub(r"(?:\d[\s\-‐]?){9,}\d?", "[number]", s)
    return re.sub(r"\s+", " ", s).strip()


def decade_of(y):
    return (y // 10) * 10


def decade_bucket(y):
    return "pre-2000" if y < 2000 else ("2000-2015" if y <= 2015 else "2016+")


# ----------------------------------------------------------------------------- HTTP
RETRY_STATUS = {429, 500, 502, 503, 504}


def http_post(url, headers, body, timeout=300):
    """POST JSON; retries twice on connection errors (and on 429/5xx). Returns (status, json_or_None, raw_text)."""
    data = json.dumps(body, ensure_ascii=False).encode("utf-8")
    for attempt in range(3):
        req = urllib.request.Request(url, data=data, method="POST",
                                     headers={"Content-Type": "application/json", **headers})
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                status, raw = r.status, r.read().decode("utf-8", "replace")
        except urllib.error.HTTPError as e:
            try:
                raw = e.read().decode("utf-8", "replace")
            except Exception:
                raw = ""
            status = e.code
            if status in RETRY_STATUS and attempt < 2:
                time.sleep(4 * (attempt + 1))
                continue
        except (urllib.error.URLError, socket.timeout, TimeoutError, ConnectionError, http.client.HTTPException) as e:
            if attempt < 2:
                time.sleep(4 * (attempt + 1))
                continue
            raise InfraError(f"connection error on {url}: {e}")
        try:
            js = json.loads(raw)
        except Exception:
            js = None
        return status, js, raw
    raise InfraError(f"unreachable retry loop on {url}")


# ----------------------------------------------------------------------------- cost ledger
class Ledger:
    def __init__(self, path, max_usd):
        self.path, self.max, self.spent, self.lock = path, max_usd, 0.0, threading.Lock()
        for rec in read_jsonl(path):
            try:
                self.spent += float(rec.get("cost_usd") or 0)
            except Exception:
                pass

    def check(self):
        if self.max is not None and self.spent >= self.max:
            raise BudgetExceeded(f"spent ${self.spent:.4f} >= --max-usd {self.max}")

    def add(self, rec):
        with self.lock:
            self.spent += float(rec.get("cost_usd") or 0)
        jlog(self.path, rec)


def or_cost(usage):
    c = float(usage.get("cost") or 0)
    up = float((usage.get("cost_details") or {}).get("upstream_inference_cost") or 0)
    byok = usage.get("is_byok")
    if byok is True:
        return c + up, "byok:upstream_inference_cost+cost"
    if byok is False:
        return c, "usage.cost"
    return (c, "usage.cost") if c > 0 else (up, "upstream_inference_cost")


def openrouter_chat(model, messages, purpose, anthropic, max_tokens=None):
    body = {"model": model, "messages": messages, "reasoning": {"effort": "max"}, "usage": {"include": True}}
    if anthropic:
        body["provider"] = {"only": ["anthropic"]}
        body["cache_control"] = {"type": "ephemeral"}
    else:
        body["provider"] = {"zdr": True}
    if max_tokens:
        body["max_tokens"] = max_tokens
    LEDGER.check()
    t0 = time.time()
    status, js, raw = http_post(OR_URL, {"Authorization": "Bearer " + os.environ.get("OPENROUTER_API_KEY", "placeholder")},
                                body, timeout=1200)
    js = js if isinstance(js, dict) else {}
    usage = js.get("usage") or {}
    cost, src = or_cost(usage)
    ok = status == 200 and bool(js.get("choices"))
    rec = {"ts": nowiso(), "api": "openrouter", "model": model, "purpose": purpose, "generation_id": js.get("id"),
           "status": status, "prompt_tokens": usage.get("prompt_tokens"),
           "completion_tokens": usage.get("completion_tokens"),
           "reasoning_tokens": (usage.get("completion_tokens_details") or {}).get("reasoning_tokens"),
           "cached_tokens": (usage.get("prompt_tokens_details") or {}).get("cached_tokens"),
           "cost_usd": cost, "cost_source": src, "cost_known": True, "secs": round(time.time() - t0, 1)}
    if not ok:
        rec["error"] = raw[:400]
    LEDGER.add(rec)
    if ok:
        c = (js["choices"][0].get("message") or {}).get("content")
        if isinstance(c, list):
            c = "".join(p.get("text", "") for p in c if isinstance(p, dict))
        return c or ""
    err = js.get("error") or {}
    code = err.get("code", status) if isinstance(err, dict) else status
    if status == 400 or code == 400:
        return None          # request rejected for this item (e.g. context too long): item-level drop
    raise InfraError(f"OpenRouter {model} status={status} code={code}: {raw[:300]}")


def ds_native_cfg_path():
    return os.path.join(STATE, "deepseek_native.json")


def ds_native(system, user, purpose):
    """DeepSeek Flash via DeepSeek's own Anthropic-format endpoint; probes the largest accepted thinking budget once."""
    key = os.environ.get("DEEPSEEK_API_KEY", "placeholder")
    headers = {"x-api-key": key, "anthropic-version": "2023-06-01"}

    def one(budget):
        body = {"model": DS_NATIVE_MODEL, "max_tokens": budget + 8192,
                "thinking": {"type": "enabled", "budget_tokens": budget},
                "system": system, "messages": [{"role": "user", "content": user}]}
        LEDGER.check()
        t0 = time.time()
        status, js, raw = http_post(DS_ANTH_URL, headers, body, timeout=1200)
        js = js if isinstance(js, dict) else {}
        u = js.get("usage") or {}
        tin, tout = u.get("input_tokens") or 0, u.get("output_tokens") or 0
        tcache = u.get("cache_read_input_tokens") or 0
        cost, known, src = 0.0, False, "tokens only (no price returned or given)"
        if isinstance(u.get("cost"), (int, float)):
            cost, known, src = float(u["cost"]), True, "usage.cost (returned by DeepSeek)"
        elif ARGS.ds_price_in is not None and ARGS.ds_price_out is not None:
            pc = ARGS.ds_price_cache if ARGS.ds_price_cache is not None else ARGS.ds_price_in
            cost = ((tin - tcache) * ARGS.ds_price_in + tcache * pc + tout * ARGS.ds_price_out) / 1e6
            known, src = True, "computed from tokens x --ds-price-* (USD per 1M)"
        rec = {"ts": nowiso(), "api": "deepseek_native", "model": DS_NATIVE_MODEL, "purpose": purpose,
               "generation_id": js.get("id"), "status": status, "prompt_tokens": tin, "completion_tokens": tout,
               "cached_tokens": tcache, "cost_usd": cost, "cost_known": known, "cost_source": src,
               "thinking_budget_sent": budget, "max_tokens_sent": budget + 8192, "secs": round(time.time() - t0, 1)}
        ok = status == 200 and isinstance(js.get("content"), list)
        if not ok:
            rec["error"] = raw[:400]
        LEDGER.add(rec)
        text = "".join(b.get("text", "") for b in js.get("content", []) if isinstance(b, dict) and b.get("type") == "text") if ok else None
        return status, ok, text, raw

    cfg = read_json(ds_native_cfg_path(), {}) or {}
    if not cfg.get("budget"):
        with _DS_PROBE_LOCK:
            cfg = read_json(ds_native_cfg_path(), {}) or {}
            if not cfg.get("budget"):
                probes = []
                for b in DS_THINK_CANDIDATES:
                    status, ok, text, raw = one(b)
                    probes.append({"budget_tokens": b, "max_tokens": b + 8192, "status": status, "error": None if ok else raw[:200]})
                    if ok:
                        write_json(ds_native_cfg_path(), {"budget": b, "max_tokens": b + 8192, "date": today(),
                                                          "sent": {"thinking": {"type": "enabled", "budget_tokens": b}},
                                                          "probes": probes})
                        return text
                    if status != 400:
                        raise InfraError(f"DeepSeek native status={status}: {raw[:300]}")
                write_json(ds_native_cfg_path(), {"budget": None, "probes": probes, "date": today()})
                raise InfraError("DeepSeek native endpoint accepted no thinking budget")
    status, ok, text, raw = one(cfg["budget"])
    if ok:
        return text
    if status == 400:
        return None
    raise InfraError(f"DeepSeek native status={status}: {raw[:300]}")


# ----------------------------------------------------------------------------- DeepSeek tools (cached snapshots)
def results_of(js):
    if isinstance(js, dict):
        for k in ("results", "data", "items"):
            v = js.get(k)
            if isinstance(v, list):
                return v
            if isinstance(v, dict) and isinstance(v.get("results"), list):
                return v["results"]
    return []


def r_url(r):
    return str(r.get("url") or r.get("link") or "") if isinstance(r, dict) else ""


def r_text(r):
    return " ".join(str(r.get(k, "")) for k in ("title", "snippet", "summary", "content", "description")) if isinstance(r, dict) else ""


def ds_search(query, count, route):
    fn = f"s_{sha(query + '|' + str(count))}.json"
    path = os.path.join(SNAP, fn)
    snap = read_json(path)
    if snap is not None:
        jlog(os.path.join(W, "tools.jsonl"), {"ts": nowiso(), "tool": "search", "query": query, "cached": True})
        return results_of(snap.get("response")), fn
    status, js, raw = http_post(DS_SEARCH_URL, {"Authorization": "Bearer " + os.environ.get("DEEPSEEK_API_KEY", "placeholder")},
                                {"query": query, "count": count, "need_content": False}, timeout=180)
    jlog(os.path.join(W, "tools.jsonl"), {"ts": nowiso(), "tool": "search", "query": query, "cached": False, "status": status})
    if status != 200 or js is None:
        raise InfraError(f"search status={status}: {raw[:200]}")
    write_json(path, {"kind": "search", "query": query, "count": count, "route": route, "date": today(), "response": js})
    jlog(os.path.join(SNAP, "index.jsonl"), {"kind": "search", "query": query, "route": route, "date": today(), "file": fn})
    return results_of(js), fn


def fetch_text(js):
    if not isinstance(js, dict):
        return ""
    parts = []
    for d in (js, js.get("data") if isinstance(js.get("data"), dict) else {}):
        for k in ("title", "content", "text", "markdown"):
            if isinstance(d.get(k), str):
                parts.append(d[k])
    return "\n".join(parts)


def ds_fetch(url, route):
    if "ctext.org" in url.lower():
        return {"ok": False, "file": None, "text": "", "url": url}
    fn = f"f_{sha(url)}.json"
    path = os.path.join(SNAP, fn)
    snap = read_json(path)
    if snap is None:
        status, js, raw = http_post(DS_FETCH_URL, {"Authorization": "Bearer " + os.environ.get("DEEPSEEK_API_KEY", "placeholder")},
                                    {"url": url}, timeout=180)
        jlog(os.path.join(W, "tools.jsonl"), {"ts": nowiso(), "tool": "fetch", "url": url, "cached": False, "status": status})
        if status in (401, 402):
            raise InfraError(f"fetch auth/billing status={status}")
        snap = {"kind": "fetch", "url": url, "route": route, "date": today(), "status": status,
                "response": js if js is not None else raw[:20000]}
        write_json(path, snap)
        jlog(os.path.join(SNAP, "index.jsonl"), {"kind": "fetch", "url": url, "route": route, "date": today(), "file": fn, "status": status})
    else:
        jlog(os.path.join(W, "tools.jsonl"), {"ts": nowiso(), "tool": "fetch", "url": url, "cached": True})
    text = fetch_text(snap.get("response"))
    ok = snap.get("status", 200) == 200 and len(norm(text)) > 30
    return {"ok": ok, "file": fn, "text": text, "url": url, "date": snap.get("date")}


def snapshot_text(fn):
    snap = read_json(os.path.join(SNAP, fn), {}) or {}
    return fetch_text(snap.get("response"))


# ----------------------------------------------------------------------------- custodian classes
def url_hp(url):
    u = re.sub(r"^[a-z]+://", "", (url or "").lower())
    return u


def host_of(url):
    return url_hp(url).split("/")[0].split(":")[0]


def reg_domain(host):
    p = host.split(".")
    if len(p) >= 3 and p[-2] in ("edu", "com", "ac", "org", "gov", "net") and len(p[-1]) == 2:
        return ".".join(p[-3:])
    return ".".join(p[-2:])


def classify(url):
    hp = url_hp(url)
    if not hp or any(b in hp for b in BANNED):
        return None
    for cls, pats in CLASS_RULES:
        if any(p in hp for p in pats):
            return cls
    return None


# ----------------------------------------------------------------------------- JSON from model text
def parse_json_obj(text):
    if not text:
        return None
    t = re.sub(r"```(?:json)?", "", text)
    dec = json.JSONDecoder()
    for m in re.finditer(r"\{", t):
        try:
            obj, _ = dec.raw_decode(t[m.start():])
            if isinstance(obj, dict):
                return obj
        except ValueError:
            continue
    return None


# ----------------------------------------------------------------------------- stage a: harvest
def cand_path():
    return os.path.join(W, "candidates.jsonl")


def make_query(cell, rng):
    typ, lang = cell
    for _ in range(20):
        period = rng.choice(PERIODS)
        if typ == "article" and lang == "zh":
            j = rng.choice(JOURNALS_ZH)
            lo, hi = max(period[0], j["years"][0]), min(period[1], j["years"][1])
            if lo > hi:
                continue
            y, i = rng.randint(lo, hi), rng.randint(1, j["issues"])
            topic = rng.choice(list(TOPICS_ZH))
            q = rng.choice([f"《{j['name']}》{y}年第{i}期 目录", f"{j['name']} {y}年第{i}期 {topic}", f"{j['name']} {y} {topic} 论文"])
            return q, {"journal": j["name"], "year_target": y, "topic": topic, "field": j["field"] or TOPICS_ZH[topic]}
        if typ == "article" and lang == "en":
            j = rng.choice(JOURNALS_EN)
            lo, hi = max(period[0], j["years"][0]), min(period[1], j["years"][1])
            if lo > hi:
                continue
            y = rng.randint(lo, hi)
            topic = rng.choice(list(TOPICS_EN))
            q = rng.choice([f"{j['name']} {y} {topic} article", f"\"{j['name']}\" volume {y - j['vol0']} {y}"])
            return q, {"journal": j["name"], "year_target": y, "topic": topic, "field": j["field"]}
        y = rng.randint(max(period[0], 1980), period[1])
        if lang == "zh":
            pub, topic = rng.choice(PUBLISHERS_ZH), rng.choice(list(TOPICS_ZH))
            q = rng.choice([f"{pub} {topic} {y}年 出版 ISBN", f"{topic} {pub} 图书 {y}", f"国家图书馆 {topic} {pub} {y}",
                            f"CiNii Books {topic} {pub}"])
            return q, {"publisher": pub, "year_target": y, "topic": topic, "field": TOPICS_ZH[topic]}
        pub, topic = rng.choice(PUBLISHERS_EN), rng.choice(list(TOPICS_EN))
        q = rng.choice([f"{pub} {topic} book {y} ISBN", f"{topic} {pub} {y} catalogue", f"CiNii Books {topic} {pub}"])
        return q, {"publisher": pub, "year_target": y, "topic": topic, "field": TOPICS_EN[topic]}
    raise RuntimeError("no query possible")


def stage_a(args):
    cands = read_jsonl(cand_path())
    seen = {c["url"] for c in cands}
    have = collections.Counter(tuple(c["cell"]) for c in cands)
    nq = collections.Counter(tuple(q["cell"]) for q in read_jsonl(os.path.join(W, "harvest_queries.jsonl")))
    for cell, share in CELLS.items():
        quota = math.ceil(args.target * share * args.harvest_factor)
        maxq = math.ceil(quota / 3) + 5
        allowed = {"journal_own", "aggregator"} if cell[0] == "article" else {"publisher", "library"}
        while have[cell] < quota and nq[cell] < maxq:
            rng = random.Random(f"{args.seed}:{cell}:{nq[cell]}")
            q, meta = make_query(cell, rng)
            offset = rng.choice([10, 20])
            res, sfile = ds_search(q, offset + 10, route="harvest")
            if len(res) > offset:
                window, eff = res[offset:offset + 10], offset
            elif len(res) > 10:
                window, eff = res[10:], 10
            else:
                window, eff = res, 0
            added = 0
            for k, r in enumerate(window):
                u = r_url(r).split("#")[0]
                hint = str(r.get("title", "")) if isinstance(r, dict) else ""
                cls = classify(u)
                if not u or u in seen or cls not in allowed:
                    continue
                if (cell[1] == "zh") != has_cjk(hint):
                    continue
                c = {"cid": "c" + sha(u, 10), "url": u, "hint_title": hint, "query": q, "search_snapshot": sfile,
                     "cell": list(cell), "meta": meta, "rank": eff + k + 1, "offset": eff, "date": today()}
                jlog(cand_path(), c)
                seen.add(u)
                have[cell] += 1
                added += 1
            jlog(os.path.join(W, "harvest_queries.jsonl"), {"cell": list(cell), "query": q, "count": offset + 10,
                                                           "offset_requested": offset, "offset_used": eff,
                                                           "returned": len(res), "added": added, "date": today()})
            nq[cell] += 1
    print(f"[a] candidates: {dict(have)}")


# ----------------------------------------------------------------------------- per-candidate state
def state_path(cid):
    return os.path.join(CANDS_DIR, cid + ".json")


_CANDS = {}


def load_cands():
    global _CANDS
    _CANDS = {c["cid"]: c for c in read_jsonl(cand_path())}
    return _CANDS


def load_state(cid):
    st = read_json(state_path(cid))
    if st is None:
        st = {"cid": cid, "cand": _CANDS[cid]}
    return st


def save_state(st):
    write_json(state_path(st["cid"]), st)


def all_states():
    out = []
    for fn in sorted(os.listdir(CANDS_DIR)):
        if fn.endswith(".json"):
            s = read_json(os.path.join(CANDS_DIR, fn))
            if s:
                out.append(s)
    return out


def drop(st, rule, stage, detail=""):
    st["drop"] = {"rule": rule, "stage": stage, "detail": str(detail)[:500], "date": today()}


# ----------------------------------------------------------------------------- stage c helper: extraction + verbatim check
EXTRACT_SYSTEM = """You extract bibliographic records from the text of a saved web page.
Copy every value exactly as written on the page: same characters (traditional or simplified as on the page), same spelling. Never translate, complete, correct or infer a value. If a value is not on the page, use null.
Return only JSON:
{"page_kind": "single_record" | "list" | "other",
 "entries": [{"author": str|null, "title": str|null, "venue": str|null, "year": str|null, "volume_issue": str|null,
              "work_type": "article"|"book"|"chapter"|"other", "abstract": str|null, "keywords": [str], "citations": str|null, "holdings": str|null}]}
"venue" is the journal name for an article and the publisher for a book. "volume_issue" is the volume/issue as printed (e.g. 2012年第4期, Vol. 37). "abstract" is the page's own abstract or content summary (内容简介/摘要), copied verbatim. "citations" is a citation count only if the page states one (e.g. 被引); "holdings" a library holdings count only if stated. At most 30 entries."""


def verify_entry(e, raw):
    """Keep only fields that occur verbatim (after normalisation) in the snapshot; return (verified, dropped_fields)."""
    nt, rawn = norm(raw), unicodedata.normalize("NFKC", raw)
    out, dropped = {}, []
    a = e.get("author")
    if isinstance(a, list):
        a = "；".join(str(x) for x in a)
    if a:
        parts = author_parts(a)
        if parts and all(norm(p) in nt for p in parts):
            out["author"] = str(a).strip()
        else:
            dropped.append("author")
    for f in ("title", "venue", "volume_issue"):
        v = e.get(f)
        if v is None or not str(v).strip():
            continue
        v = str(v).strip()
        if norm(v) and norm(v) in nt:
            out[f] = v
        else:
            dropped.append(f)
    y = e.get("year")
    if y is not None:
        m = re.search(r"(1[89]\d\d|20\d\d)", unicodedata.normalize("NFKC", str(y)))
        if m and m.group(1) in rawn:
            out["year"] = int(m.group(1))
        else:
            dropped.append("year")
    ab = e.get("abstract")
    if isinstance(ab, str) and ab.strip():
        sents = [s for s in re.split(r"(?<=[。！？.!?；;])\s*", ab) if len(norm(s)) >= 4]
        good = [s for s in sents if norm(s) in nt]
        if good:
            out["abstract"] = " ".join(good)
        if len(good) < len(sents):
            dropped.append(f"abstract_sentences:{len(sents) - len(good)}")
    kws = e.get("keywords") or []
    if isinstance(kws, str):
        kws = re.split(r"[;；,，、]", kws)
    good = [str(k).strip() for k in kws if norm(k) and norm(k) in nt]
    if good:
        out["keywords"] = good
    for f in ("citations", "holdings"):
        v = e.get(f)
        if v is not None:
            d = str(v).replace(",", "").strip()
            if re.fullmatch(r"\d+", d) and d in rawn:
                out[f] = int(d)
            else:
                dropped.append(f)
    out["work_type_llm"] = e.get("work_type")
    return out, dropped


def extract(snapfile, url, mode, target=None):
    key = f"{snapfile}__{mode}__{sha(json.dumps(target, ensure_ascii=False) if target else '')}"
    path = os.path.join(EXTRACT_DIR, key + ".json")
    cached = read_json(path)
    if cached is not None:
        return cached
    raw = snapshot_text(snapfile)
    user = f"URL: {url}\n\nPAGE TEXT (may be truncated):\n{raw[:MAX_PAGE_CHARS]}"
    if mode == "B" and target:
        user += ("\n\nReturn ONLY the entry (if any) for the work whose title is close to: " + target["title"] +
                 (" (author: " + target["author"] + ")" if target.get("author") else "") +
                 "\nUse exactly this page's own wording, which may differ from the hint. If no such entry is on the page, return \"entries\": [].")
    txt = openrouter_chat(EXTRACT_MODEL, [{"role": "system", "content": EXTRACT_SYSTEM}, {"role": "user", "content": user}],
                          purpose=f"extract:{mode}", anthropic=False)
    parsed = parse_json_obj(txt) if txt is not None else None
    entries = []
    if parsed and isinstance(parsed.get("entries"), list):
        for e in parsed["entries"][:30]:
            if isinstance(e, dict):
                v, d = verify_entry(e, raw)
                entries.append({"verified": v, "dropped_fields": d})
    res = {"snapshot_file": snapfile, "mode": mode, "target": target, "date": today(), "raw_output": txt,
           "parse_ok": parsed is not None, "call_rejected": txt is None, "entries": entries}
    write_json(path, res)
    return res


REQ = ("author", "title", "venue", "year")


def complete(v):
    return all(k in v for k in REQ)


# ----------------------------------------------------------------------------- stage b
ISBN_RE = re.compile(r"(?:ISBN[\s:：]*)?((?:97[89][\s\-‐]?)?\d[\d\s\-‐]{7,13}[\dXx])")
ISSN_RE = re.compile(r"ISSN[\s:：]*(\d{4}[\-‐]\d{3}[\dXx])")


def isbn_ok(d):
    if len(d) == 13 and d.isdigit():
        return sum(int(c) * (1 if i % 2 == 0 else 3) for i, c in enumerate(d)) % 10 == 0
    if len(d) == 10 and d[:9].isdigit():
        s = sum((10 - i) * (10 if c in "Xx" else int(c)) for i, c in enumerate(d))
        return s % 11 == 0
    return False


def find_isbns(text):
    out = []
    for m in re.finditer(r"ISBN", text):
        seg = text[m.start(): m.start() + 40]
        mm = ISBN_RE.search(seg)
        if mm:
            d = re.sub(r"[\s\-‐]", "", mm.group(1))
            if isbn_ok(d) and d not in out:
                out.append(d)
    return out


def b_queries(entry, a_text, cand):
    typ, lang = cand["cell"]
    if typ == "book":
        return [(f"ISBN {d}", "isbn") for d in find_isbns(a_text)[:2]]
    qs = []
    v, y = entry["venue"], entry["year"]
    nums = digits_seq(entry.get("volume_issue"))
    nums = [n for n in nums if n != y]
    issn = ISSN_RE.search(a_text)
    if lang == "zh":
        if nums:
            qs.append((f"{v} {y}年第{nums[-1]}期 目录", "issue_browse"))
        else:
            qs.append((f"{v} {y}年 目录", "issue_browse"))
        if issn:
            qs.append((f"ISSN {issn.group(1)} {y}" + (f" 第{nums[-1]}期" if nums else ""), "issn_issue_browse"))
    else:
        if nums:
            qs.append((f"{v} volume {nums[0]} {y} table of contents", "issue_browse"))
        else:
            qs.append((f"{v} {y} table of contents", "issue_browse"))
        if issn:
            qs.append((f"ISSN {issn.group(1)} {y}", "issn_issue_browse"))
    return qs


def loose_title_in(title, text):
    n = norm(title)
    p = n[:min(len(n), 10)]
    return bool(p) and p in norm(text)


def stage_b(st, args):
    if st.get("drop") or st.get("recB"):
        return
    c = st["cand"]
    cls = classify(c["url"])
    if not cls:
        return drop(st, "not_primary_source", "b", c["url"])
    if "entryA" not in st:
        A = ds_fetch(c["url"], route=f"harvest search: {c['query']}")
        if not A["ok"]:
            return drop(st, "unfetchable_source", "b", "record A")
        ex = extract(A["file"], c["url"], "A")
        if ex["call_rejected"] or not ex["parse_ok"]:
            return drop(st, "extraction_failed", "c", "record A")
        full = [e["verified"] for e in ex["entries"] if complete(e["verified"])]
        if not full:
            return drop(st, "field_unverified", "c", "record A: no entry with verbatim author+title+venue+year")
        nh = norm(c.get("hint_title"))
        pref = [v for v in full if len(nh) >= 4 and (norm(v["title"]) in nh or nh in norm(v["title"]))]
        pick = pref[0] if pref else random.Random(c["cid"]).choice(full)
        st["recA"] = {"url": c["url"], "custodian_class": cls, "route": f"harvest search: {c['query']}",
                      "snapshot_file": A["file"], "date": A["date"] or today()}
        st["entryA"] = pick
        st["extract_files"] = {"A": A["file"]}
        save_state(st)
    entry = st["entryA"]
    a_text = snapshot_text(st["recA"]["snapshot_file"])
    qs = b_queries(entry, a_text, c)
    if not qs:
        return drop(st, "no_second_record", "b", "no ISBN / ISSN-issue route available")
    tried = 0
    for q, route in qs:
        res, _ = ds_search(q, 10, route=f"{route}: {q}")
        for r in res:
            u = r_url(r).split("#")[0]
            cl = classify(u)
            if not u or not cl or cl == cls or reg_domain(host_of(u)) == reg_domain(host_of(c["url"])):
                continue   # different custodian class required; two aggregators never pair (same class)
            if tried >= 3:
                break
            tried += 1
            B = ds_fetch(u, route=f"{route}: {q}")
            if B["ok"] and loose_title_in(entry["title"], B["text"]):
                st["recB"] = {"url": u, "custodian_class": cl, "route": f"{route}: {q}", "snapshot_file": B["file"],
                              "date": B["date"] or today()}
                return
    drop(st, "no_second_record", "b", f"no independent primary record found ({tried} fetched)")


# ----------------------------------------------------------------------------- stage c
def stage_c(st, args):
    if st.get("drop") or not st.get("recB") or st.get("entryB"):
        return
    rb, ea = st["recB"], st["entryA"]
    ex = extract(rb["snapshot_file"], rb["url"], "B", target={"title": ea["title"], "author": ea.get("author")})
    if ex["call_rejected"] or not ex["parse_ok"]:
        return drop(st, "extraction_failed", "c", "record B")
    full = [e["verified"] for e in ex["entries"] if complete(e["verified"])]
    if not full:
        return drop(st, "field_unverified", "c", "record B: no entry with verbatim author+title+venue+year")
    same = [v for v in full if norm(v["title"]) == norm(ea["title"])]
    st["entryB"] = same[0] if same else full[0]


# ----------------------------------------------------------------------------- stage d
def stage_d(st, args):
    if st.get("drop") or not st.get("entryB") or st.get("key"):
        return
    a, b = st["entryA"], st["entryB"]
    if norm(a["title"]) != norm(b["title"]):
        return drop(st, "field_mismatch:title", "d", f"{a['title']} | {b['title']}")
    if author_key(a["author"]) != author_key(b["author"]):
        return drop(st, "field_mismatch:author", "d", f"{a['author']} | {b['author']}")
    if venue_key(a["venue"]) != venue_key(b["venue"]):
        return drop(st, "field_mismatch:venue", "d", f"{a['venue']} | {b['venue']}")
    if a["year"] != b["year"]:
        return drop(st, "field_mismatch:year", "d", f"{a['year']} | {b['year']}")
    vi = None
    if a.get("volume_issue") and b.get("volume_issue"):
        if digits_seq(a["volume_issue"]) != digits_seq(b["volume_issue"]):
            return drop(st, "field_mismatch:volume_issue", "d", f"{a['volume_issue']} | {b['volume_issue']}")
        vi = a["volume_issue"]
    else:
        vi = a.get("volume_issue") or b.get("volume_issue")   # only one record states it; verified verbatim there
    sig = norm(a["title"]) + "|" + norm(a["author"])
    with _DUP_LOCK:
        if sig in _DUPS and _DUPS[sig] != st["cid"]:
            return drop(st, "duplicate", "d", f"same key as {_DUPS[sig]}")
        _DUPS[sig] = st["cid"]
    typ, _ = st["cand"]["cell"]
    lang = "zh" if has_cjk(a["title"]) else "en"
    fame, fsrc = "unknown", None
    cit = a.get("citations", b.get("citations"))
    hold = a.get("holdings", b.get("holdings"))
    if cit is not None:
        fame = "famous" if cit >= FAME_CIT[0] else ("mid" if cit >= FAME_CIT[1] else "obscure")
        fsrc = f"citations={cit}"
    elif hold is not None:
        fame = "famous" if hold >= FAME_HOLD[0] else ("mid" if hold >= FAME_HOLD[1] else "obscure")
        fsrc = f"holdings={hold}"
    st["key"] = {"author": a["author"], "title": a["title"], "venue": a["venue"], "year": a["year"], "volume_issue": vi}
    st["key_forms"] = {"A": {k: a.get(k) for k in REQ + ("volume_issue",)}, "B": {k: b.get(k) for k in REQ + ("volume_issue",)}}
    st["stratum"] = {"fame": fame, "fame_source": fsrc, "type": typ, "language": lang,
                     "decade": decade_bucket(a["year"]), "post_cutoff": a["year"] >= args.cutoff_year}
    st["records"] = [st["recA"], st["recB"]]
    ab = " ".join(x for x in (a.get("abstract"), b.get("abstract")) if x)
    kws = list(dict.fromkeys((a.get("keywords") or []) + (b.get("keywords") or [])))
    st["topic_source"] = {"abstract": ab[:3000], "keywords": kws[:15]}
    # recoverability gate (design A6): the search tool must find the key from its own fields
    q = f"{a['title']} {author_parts(a['author'])[0] if author_parts(a['author']) else ''}".strip()
    res, _ = ds_search(q, 10, route="recoverability")
    rank = hit_rank(res, a["title"], [st["recA"]["url"], st["recB"]["url"]])
    st["recover"] = {"query": q, "rank": rank}
    if rank is None:
        return drop(st, "recoverability_failed", "d", q)
    if not ab and not kws:
        return drop(st, "no_abstract_keywords", "d", "no verified abstract/keywords to paraphrase a topic from")


def hit_rank(results, title, urls):
    nt = norm(title)
    clean = [x.split("#")[0].rstrip("/") for x in urls if x]
    for i, r in enumerate(results[:10], 1):
        u = r_url(r).split("#")[0].rstrip("/")
        if u and u in clean:
            return i
        if nt and nt in norm(r_text(r)):
            return i
        rt = re.sub(r"(\.\.\.|…)+\s*$", "", str(r.get("title", "")) if isinstance(r, dict) else "")
        nr = norm(rt)
        if len(nr) >= 6 and len(nr) >= min(12, len(nt)) and nt.startswith(nr):
            return i
    return None


# ----------------------------------------------------------------------------- stage e: writers
WRITER_SYSTEM = """You write ONE search clue for a bibliographic recall test on Chinese scholarship (Yijing/Zhouyi, excavated manuscripts, early Chinese texts). You receive verified key fields of one work and its abstract/keywords.
Rules:
1. Write in the language given ("Chinese" -> Chinese, "English" -> English).
2. The clue states: the work type, the field, the topic paraphrased in your own words from the abstract/keywords, the ONE anchor given (author or venue, written exactly as given), and the decade given, written exactly as given.
3. Do not give the title, the exact year, volume, issue, pages, or the other anchor (anchor=author: do not name the journal/publisher; anchor=venue: do not name the author).
4. Do not reuse any 3 consecutive Chinese characters from the title, nor any 2 consecutive English words from the title.
5. Describe only what the abstract/keywords support; add no claims.
6. One sentence; at most 80 Chinese characters or 45 English words.
Return only JSON: {"clue": "..."}"""


def writer_payload(st):
    k, s = st["key"], st["stratum"]
    zh = s["language"] == "zh"
    anchor = "author" if int(sha(st["cid"]), 16) % 2 == 0 else "venue"
    dec = decade_of(k["year"])
    return {
        "language": "Chinese" if zh else "English",
        "work_type": ("期刊论文" if s["type"] == "article" else "专著/图书") if zh else ("journal article" if s["type"] == "article" else "book"),
        "field": st["cand"]["meta"].get("field"),
        "title": k["title"], "author": k["author"], "venue": k["venue"],
        "anchor": {"type": anchor, "value": k[anchor] if anchor == "venue" else k["author"]},
        "decade": f"{dec}年代" if zh else f"the {dec}s",
        "abstract": sanitize(st["topic_source"]["abstract"])[:1500],
        "keywords": [sanitize(x) for x in st["topic_source"]["keywords"]],
    }


def call_writer(w, user, purpose):
    kind, model = WRITERS[w]
    if kind == "openrouter":
        return openrouter_chat(model, [{"role": "system", "content": WRITER_SYSTEM}, {"role": "user", "content": user}],
                               purpose, anthropic=True, max_tokens=32000)
    return ds_native(WRITER_SYSTEM, user, purpose)


def clue_format_check(clue, st, payload):
    k = st["key"]
    zh = st["stratum"]["language"] == "zh"
    nc = norm(clue)
    if not nc:
        return "empty"
    if zh and (len(clue) > 120 or not has_cjk(clue)):
        return "length_or_language"
    if not zh and (len(clue.split()) > 60 or len(re.findall(r"[\u3400-\u9fff]", clue)) > len(clue) / 3):
        return "length_or_language"
    aparts = [p for p in (ROLE_ZH.sub("", x) for x in author_parts(k["author"])) if len(norm(p)) >= 2]
    if payload["anchor"]["type"] == "author":
        if not aparts or not all(norm(p) in nc for p in aparts):
            return "anchor_missing"
        if venue_key(k["venue"]) and venue_key(k["venue"]) in nc:
            return "second_anchor_venue"
    else:
        if venue_key(k["venue"]) not in nc:
            return "anchor_missing"
        if any(norm(p) in nc for p in aparts):
            return "second_anchor_author"
    dec = str(decade_of(k["year"]))
    token = dec + ("年代" if zh else "s")
    if token not in nc:
        return "decade_missing"
    if str(k["year"]) in nc.replace(token, ""):
        return "exact_year_given"
    return None


def stage_e(st, args):
    if st.get("drop") or not st.get("key"):
        return
    st.setdefault("clues", {})
    payload = writer_payload(st)
    user = json.dumps(payload, ensure_ascii=False, indent=1)
    for w in args.writers:
        if w in st["clues"]:
            continue
        txt = call_writer(w, user, purpose=f"write:{w}")
        write_json(os.path.join(CLUE_DIR, f"{st['cid']}_{w}.json"), {"writer": w, "date": today(), "payload": payload, "raw_output": txt})
        rec = {"writer": w, "anchor": payload["anchor"]["type"]}
        if txt is None:
            rec.update(status="call_rejected", reason="call_rejected")
        else:
            obj = parse_json_obj(txt)
            clue = obj.get("clue") if isinstance(obj, dict) else None
            if not isinstance(clue, str):
                rec.update(status="unparseable", reason="cl