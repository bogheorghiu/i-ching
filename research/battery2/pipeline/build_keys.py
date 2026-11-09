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


NAME_DROP = {"author", "authors", "editor", "editors", "ed", "eds", "edited", "by", "translator", "translators",
             "trans", "tr", "compiler", "comp", "contributor", "illustrator", "writer", "joint", "introduction",
             "foreword", "preface", "jr", "sr", "dr", "prof", "professor"}
NAME_PARTICLES = {"van", "von", "der", "den", "de", "du", "di", "da", "del", "della", "dos", "das", "la", "le",
                  "ter", "ten", "bin", "al"}
LIFE_DATES = re.compile(
    r"\b(?:b|d|fl|ca|c|born|died|active|approximately)\.?\s*\d{3,4}\??"
    r"|\d{3,4}\??\s*[-–—]\s*(?:\d{3,4}\??)?"
    r"|\b\d{1,2}(?:st|nd|rd|th)\s+cent(?:ury|\.)?"
    r"|\d+", re.I)

def _name_tokens(seg):
    seg = LIFE_DATES.sub(" ", seg)
    return [t for t in re.findall(r"[a-z]+", seg) if t not in NAME_DROP and t not in ROLE_EN]

def _latin_people(a):
    """Alternative parses of a Latin-script author string into persons (surname_set_or_None, tokens).
    'Surname, Given, dates, role' gives a known surname; a 2-segment comma chunk is also tried as two persons."""
    s = deaccent(unicodedata.normalize("NFKC", str(a or "")).lower())
    chunks = [ch for ch in re.split(r"[;；|/&+]|\band\b|\bwith\b", s) if _name_tokens(ch)]
    options = []
    for ch in chunks:
        segs = [t for t in (_name_tokens(x) for x in re.split(r"[,，]", ch)) if t]
        opts = [[(None, tuple(t)) for t in segs]]
        if len(segs) == 2:
            opts.insert(0, [(frozenset(segs[0]), tuple(segs[0] + segs[1]))])
        options.append(opts)
    if not options:
        return []
    return [[p for grp in combo for p in grp] for combo in itertools.islice(itertools.product(*options), 32)]

def _person_match(p, q):
    """Surname plus at least one given name shared, order-insensitive."""
    shared = set(p[1]) & set(q[1])
    if len(shared) < 2:
        return False
    for x, y in ((p, q), (q, p)):
        if x[0] is None:
            continue
        core = {t for t in x[0] if t not in NAME_PARTICLES} or set(x[0])
        if not core <= shared or not (shared - x[0]):
            return False
        if y[0] is None and not core & {y[1][0], y[1][-1]}:    # surname must sit at an end of the other name
            return False
    if p[0] is None and q[0] is None and not ({p[1][0], p[1][-1]} & {q[1][0], q[1][-1]} & shared):
        return False
    return True

def authors_match(a, b):
    """Author equality for cross-record checks. Exact author_key equality always matches. Strings containing CJK
    keep the exact rule only (no loosening). Latin-script names: catalogue forms ('Eyferth, Jan Jacob Karl,
    1962-') match 'Jacob Eyferth' when surname + >=1 given name agree, every person on each side matched."""
    sa = "; ".join(map(str, a)) if isinstance(a, list) else str(a or "")
    sb = "; ".join(map(str, b)) if isinstance(b, list) else str(b or "")
    if author_key(sa) == author_key(sb):
        return True
    if has_cjk(sa) or has_cjk(sb):
        return False
    for pa in _latin_people(sa):
        for pb in _latin_people(sb):
            if pa and pb and all(any(_person_match(p, q) for q in pb) for p in pa) \
                    and all(any(_person_match(q, p) for p in pa) for q in pb):
                return True
    return False



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


def openrouter_chat(model, messages, purpose, anthropic, max_tokens=None, reasoning_tokens=None):
    # With effort "max", Opus spent the whole 32k max_tokens on reasoning and returned empty content in run 1
    # (2026-11-09, two verify batches); a reasoning budget below max_tokens leaves room for the answer.
    reasoning = {"max_tokens": reasoning_tokens} if reasoning_tokens else {"effort": "max"}
    body = {"model": model, "messages": messages, "reasoning": reasoning, "usage": {"include": True}}
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


def hit_text(r):
    """Text of ONE search hit as saved: its own title/snippet/summary/content/description, no URL and no crawl date
    (so a year or digits inside a URL can never verify a field)."""
    if not isinstance(r, dict):
        return ""
    out = []
    for k in ("title", "snippet", "summary", "content", "description"):
        v = r.get(k)
        if isinstance(v, str) and v.strip() and v.strip() not in out:
            out.append(v.strip())
    return "\n".join(out)


def verify_source(snapfile):
    """The only text a record may be extracted from and verified against. For a saved search hit this is the hit's
    own title/snippet/summary/content/description (hit_text) - never the query, route, URL, crawl date or site name
    we stored alongside it, so nothing we typed can verify a field. Other snapshots: their page text."""
    d = read_json(os.path.join(SNAP, snapfile)) if str(snapfile).endswith(".json") else None
    if isinstance(d, dict) and d.get("kind") == "search_hit":
        return hit_text(d.get("response"))
    return snapshot_text(snapfile)




def ds_search(query, count, route):
    # DeepSeek search rejects queries over 128 characters (HTTP 400): cut at the last space before the limit.
    if len(query) > 128:
        query = query[:128].rsplit(" ", 1)[0] if " " in query[:128] else query[:128]
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


def save_hit_snapshot(hit, parent_file, idx, query, route):
    """Snapshot of one search hit: the hit's own JSON from the saved search response, with a pointer to that response."""
    fn = f"h_{sha(str(parent_file) + '|' + str(idx))}.json"
    path = os.path.join(SNAP, fn)
    if read_json(path) is None:
        write_json(path, {"kind": "search_hit", "parent_snapshot": parent_file, "hit_index": idx, "query": query,
                          "route": route, "url": r_url(hit), "date": today(), "response": hit})
        jlog(os.path.join(SNAP, "index.jsonl"), {"kind": "search_hit", "parent": parent_file, "hit_index": idx,
                                                 "query": query, "route": route, "date": today(), "file": fn})
    return fn



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
    if snap is not None and snap.get("status") != 200 and host_of(url) in MOONSHOT_FALLBACK_HOSTS \
            and not snap.get("fallback_tried"):
        snap = None                               # retry a cached DeepSeek failure through Moonshot once
    if snap is None:
        status, js, raw = http_post(DS_FETCH_URL, {"Authorization": "Bearer " + os.environ.get("DEEPSEEK_API_KEY", "placeholder")},
                                    {"url": url}, timeout=180)
        jlog(os.path.join(W, "tools.jsonl"), {"ts": nowiso(), "tool": "fetch", "url": url, "cached": False, "status": status})
        if status in (401, 402):
            raise InfraError(f"fetch auth/billing status={status}")
        snap = {"kind": "fetch", "url": url, "route": route, "date": today(), "status": status,
                "response": js if js is not None else raw[:20000]}
        if status != 200 and host_of(url) in MOONSHOT_FALLBACK_HOSTS:
            # DeepSeek's fetch cannot open these hosts; Moonshot's can (observed 2026-11-09, PATCH-5.md).
            m_status, m_js, m_raw = http_post(MOONSHOT_FETCH_URL, {"Authorization": "Bearer " + os.environ.get(
                "MOONSHOT_API_KEY", "placeholder")}, {"url": url}, timeout=180)
            jlog(os.path.join(W, "tools.jsonl"), {"ts": nowiso(), "tool": "fetch", "via": "moonshot", "url": url,
                                                  "cached": False, "status": m_status})
            if m_status in (401, 402, 429):
                raise InfraError(f"moonshot fetch auth/billing/rate status={m_status}")
            snap = {"kind": "fetch", "url": url, "route": route + " (via moonshot after deepseek " + str(status) + ")",
                    "date": today(), "status": m_status, "fetcher": "moonshot", "fallback_tried": True,
                    "response": m_js if m_js is not None else m_raw[:20000]}
        write_json(path, snap)
        jlog(os.path.join(SNAP, "index.jsonl"), {"kind": "fetch", "url": url, "route": route, "date": today(), "file": fn, "status": status})
    else:
        jlog(os.path.join(W, "tools.jsonl"), {"ts": nowiso(), "tool": "fetch", "url": url, "cached": True})
    text = fetch_text(snap.get("response"))
    ok = snap.get("status", 200) == 200 and len(norm(text)) > 30
    return {"ok": ok, "file": fn, "text": text, "url": url, "date": snap.get("date")}


def snapshot_text(fn):
    snap = read_json(os.path.join(SNAP, fn), {}) or {}
    if snap.get("kind") == "search_hit":
        return hit_text(snap.get("response"))
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


# Journal-introduction / journal-home pages are listings, not records (owner rule 4).
JOURNAL_PAGE_TITLE = re.compile(
    r"期刊介绍|期刊简介|期刊概况|本刊简介|本刊介绍|刊物简介|杂志简介|关于本刊|期刊首页|投稿须知|投稿指南|征稿启事|编委会|"
    r"about\s+(?:the|this)\s+journal|journal\s+(?:home(?:page)?|information|overview)|aims\s+(?:and|&)\s+scope|"
    r"editorial\s+board", re.I)
JOURNAL_PAGE_PATH = re.compile(
    r"/(?:qkjs|qkjj|qkgk|bkjj|bkjs|gybk|kwjj|tgxz|tgzn|zgqs|bwh)(?:[./?_#-]|$)"
    r"|/(?:about(?:[-_]?(?:us|the[-_]?journal|journal))?|aims[-_]?(?:and|&)[-_]?scope|editorial[-_]?board|"
    r"journal[-_]?(?:info|information|intro|introduction|home))(?:[./?#]|$)", re.I)
SITE_HOME_PATH = re.compile(r"/?(?:(?:index|default|home)\.(?:s?html?|aspx?|php|jsp))?/?", re.I)
JOURNAL_BODY_MARKS = [re.compile(x, re.I) for x in (
    r"主办单位|主办[:：]", r"主管单位|主管[:：]", r"创刊于|创刊时间|创刊年",
    r"国际标准连续出版物号|ISSN\s*[:：]?\s*\d{4}\s*-?\s*\d{3}[\dX]",
    r"国内统一连续出版物号|CN\s*[:：]?\s*\d{2}\s*-\s*\d{4}", r"刊期|出版周期", r"邮发代号",
    r"aims\s+(?:and|&)\s+scope", r"editorial\s+board", r"about\s+(?:the|this)\s+journal",
    r"submission\s+guidelines|instructions\s+for\s+authors|submit\s+(?:an|your)\s+(?:article|manuscript)",
    r"call\s+for\s+papers")]
ARTICLE_BODY_MARK = re.compile(r"摘要|关键词|关键字|abstract|keywords|doi\s*[:：]?\s*10\.", re.I)



def classify(url):
    hp = url_hp(url)
    if not hp or any(b in hp for b in BANNED):
        return None
    for cls, pats in CLASS_RULES:
        if any(p in hp for p in pats):
            return cls
    return None


LISTING_PATH = re.compile(
    r"(?:[?&](?:q|query|kw|keyword|keywords|key|searchword|wd|word|lookfor|search|term|txt)=|/search|/s\?|/browse|"
    r"hotword|/toc\b|tableofcontents|/issues?(?:/|$|\?)|/all-issues|/listissue|/navi|kns8?/(?:brief|defaultresult)|"
    r"func=(?:find|short|scan)|/column|/catalog\?|/results)", re.I)
ITEM_URL = [
    ("cnki.net", r"(kcms2?/(article/abstract|detail)|detail\.aspx|/kcms/detail/)"),
    ("cnki.com.cn", r"/article/"),
    ("cqvip.com", r"(/qk/[\w-]+/\d+/[\w-]+\.html|/doc/journal/\d+|/article/detail)"),
    ("wanfangdata.com.cn", r"(/details/detail\.do\?_type=(perio|degree|conference)|/(periodical|thesis|conference)/[a-z0-9%=+_-]{10,})"),
    ("nssd.cn", r"(article_detail|/articles/)"),
    ("airitilibrary.com", r"(aldetailedmesh|/article/detail)"),
    ("jstor.org", r"/stable/"),
    ("muse.jhu.edu", r"/(article|book)/\d+"),
    ("ci.nii.ac.jp", r"/(ncid|naid|crid)/"),
    ("cir.nii.ac.jp", r"/crid/"),
    ("opac.nlc.cn", r"func=(full|direct)"),
    ("worldcat.org", r"/(title|oclc)/"),
    ("searchworks.stanford.edu", r"/view/"),
    ("hollis.harvard.edu", r"fulldisplay"),
    ("catalog.hathitrust.org", r"/record/"),
    ("cambridge.org", r"/core/(journals/[^/]+/article/|books/[^/?]+)"),
    ("brill.com", r"(/view/journals/\w+/\d+/[\w.-]+/article|/view/title/|/display/title/|/edcollbook/title/)"),
]


def is_listing_url(url):
    """True if the URL is a listing (search result, TOC/issue index, hotword/wiki page, column, journal
    introduction/home page, site root) rather than one work's own item page. Hosts with a known item-URL form
    must match it; other hosts are judged by listing patterns only."""
    hp = url_hp(url)
    host = host_of(url)
    path = hp[len(hp.split("/")[0]):]
    if host.startswith("wiki.") or ".wiki." in host or "wiki.cnki" in hp:
        return True
    if LISTING_PATH.search(path) or JOURNAL_PAGE_PATH.search(path):
        return True
    if SITE_HOME_PATH.fullmatch(path):            # a site/journal root is never one work's record
        return True
    for dom, pat in ITEM_URL:
        if host == dom or host.endswith("." + dom):
            return not re.search(pat, path)
    return False


LIST_TITLE_MARK = re.compile(r"(目录|目次|总目|索引|检索|搜索|热词|导航|栏目|期刊简介|过刊|往期|期刊浏览|search|\bresults?\b|"
                             r"table of contents|\bcontents\b|all issues|\bissue \d+|\bvolume \d+\b|\bvol\. ?\d+\s*(?:,|no))", re.I)
LIST_BODY_MARK = re.compile(r"(检索结果|搜索结果|共找到|找到约|条记录|条结果|共\s*\d+\s*条|相关搜索|本期目录|往期目录|期刊目录|"
                            r"search results|results for|showing \d+|\d+\s*[-–]\s*\d+\s+of\s+\d+)", re.I)


def is_listing_text(text, title=""):
    """Content test on a search hit: listing or journal-page markers in its title, listing markers in its text,
    a journal-introduction profile (>=3 journal markers and no article markers), more than one year/issue, or
    several different 《》 titles mean the hit describes a listing, not one work."""
    if title:
        tn = unicodedata.normalize("NFKC", str(title))
        if LIST_TITLE_MARK.search(tn) or JOURNAL_PAGE_TITLE.search(tn):
            return True
    t = unicodedata.normalize("NFKC", str(text or ""))
    if LIST_BODY_MARK.search(t):
        return True
    if sum(1 for rx in JOURNAL_BODY_MARKS if rx.search(t)) >= 3 and not ARTICLE_BODY_MARK.search(t):
        return True
    issues = {(m.group(1), m.group(2)) for m in re.finditer(r"((?:19|20)\d\d)\s*年\s*第?\s*0?(\d{1,2})\s*期", t)}
    if len(issues) > 1:
        return True
    quoted = {norm(x) for x in re.findall(r"《([^《》]{2,60})》", t) if norm(x)}
    return len(quoted) >= 3




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




def load_host_stats(extra_paths, min_attempts=3):
    """Hosts with >= min_attempts uncached DeepSeek fetches and none with status 200, counted over this
    workdir's tools.jsonl plus any --host-stats files (each file read once, by real path)."""
    paths, seen_real = [], set()
    for p in [os.path.join(W, "tools.jsonl")] + list(extra_paths or []):
        rp = os.path.realpath(p)
        if rp in seen_real or not os.path.exists(p):
            continue
        seen_real.add(rp)
        paths.append(p)
    att, ok = collections.Counter(), collections.Counter()
    for p in paths:
        for t in read_jsonl(p):
            if not isinstance(t, dict) or t.get("tool") != "fetch" or t.get("cached") or "status" not in t:
                continue
            h = host_of(t.get("url", ""))
            if not h:
                continue
            att[h] += 1
            if t.get("status") == 200:
                ok[h] += 1
    blocked = {h: {"fetch_attempts": att[h], "fetch_200": 0} for h in att if att[h] >= min_attempts and ok[h] == 0}
    return blocked, paths




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


def seed_queries(r, cell, meta):
    """Up to two item queries seeded from a listing hit's text (the listing itself is never a record)."""
    txt = hit_text(r)
    venue = meta.get("journal") or meta.get("publisher") or ""
    if cell[1] == "zh":
        segs = re.findall(r"《([^《》]{6,40})》", txt)
        segs += [s for s in re.split(r"[\s|｜;；/／•·]+|\.\.\.|…", txt)
                 if 8 <= len(s) <= 40 and has_cjk(s) and not re.search(r"目录|目次|期刊|检索|搜索|第\d+期|\d{4}年", s)]
    else:
        segs = [s.strip() for s in re.split(r"\s[|·•–—-]\s|;|\.\s|…", txt) if 4 <= len(s.split()) <= 18]
    out, seen = [], {venue_key(venue)}
    for s in segs:
        n = norm(s)
        if not n or n in seen:
            continue
        seen.add(n)
        out.append(f"{s} {venue}".strip())
        if len(out) >= 2:
            break
    return out


def harvest_hit(r, idx, sfile, q, cell, meta, rank, offset, allowed, seen, seed_from=None, blocked=None):
    """Register one search hit as a candidate if it is an item record; returns 'added', 'listing', 'skipped' or None."""
    if not isinstance(r, dict):
        return None
    u = r_url(r).split("#")[0]
    hint = str(r.get("title", ""))
    if not u or classify(u) not in allowed:
        return None
    if (cell[1] == "zh") != has_cjk(hint):
        return None
    if is_listing_url(u) or is_listing_text(hit_text(r), hint):
        return "listing"
    if u in seen:
        return None
    h = host_of(u)
    if blocked and h in blocked:            # host steering: not a candidate, logged for the sampling-frame report
        jlog(os.path.join(W, "harvest_skips.jsonl"),
             {"ts": nowiso(), "reason": "host_unfetchable", "host": h, "url": u, "hint_title": hint,
              "cell": list(cell), "query": q, "search_snapshot": sfile, "hit_index": idx, "seed_from": seed_from,
              "fetch_attempts": blocked[h]["fetch_attempts"], "fetch_200": blocked[h]["fetch_200"], "date": today()})
        return "skipped"
    c = {"cid": "c" + sha(u, 10), "url": u, "hint_title": hint, "query": q, "search_snapshot": sfile, "hit_index": idx,
         "cell": list(cell), "meta": meta, "rank": rank, "offset": offset, "seed_from": seed_from, "date": today()}
    jlog(cand_path(), c)
    seen.add(u)
    return "added"



# ----------------------------------------------------------------------------- seeded intake (PREREG deviations 2-3)
# Candidates come from a seed JSONL (one paper per line, with candidate source URLs) instead of search. Record A is an
# item page fetched and extracted as usual; record B is a complete issue table of contents on a research institute's
# portal, parsed in code: the entry line must match record A's title exactly (after norm), so nothing is repaired.
TOC_HOSTS = ("iwr.cass.cn", "iwr.cssn.cn")
MOONSHOT_FETCH_URL = "https://api.moonshot.ai/v1/tools/fetch"
MOONSHOT_FALLBACK_HOSTS = ("iwr.cssn.cn",)
CNKI_HOSTS = ("www.cnki.com.cn", "cnki.com.cn")
TOC_HEAD = re.compile(r"《([^》]{2,30})》\s*(\d{4})\s*年")


def toc_entry(url, title):
    """Record B from an institute TOC: (entry, record, None) or (None, None, reason)."""
    F = ds_fetch(url, "seed: institute toc")
    if not F["ok"]:
        return None, None, "unfetchable_source"
    head = TOC_HEAD.search(F["text"][:600])
    if not head:
        return None, None, "toc_header_absent"
    text = F["text"].replace("\\|", "|").replace("**", "")     # Moonshot returns markdown
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    hits = []
    for i, ln in enumerate(lines):
        if "/" not in ln:
            continue
        # Formats seen on these portals: "title//authors（page）" (2016), "title/authors" (2018),
        # "title/author|author" (2019). Authors are the text after the last separator.
        t, _, rest = ln.partition("//") if "//" in ln else ln.rpartition("/")
        if i and re.match(r"^[-—–]{2,}", t):          # subtitle wrapped onto its own line
            t = lines[i - 1] + t
        if norm(t) == norm(title):
            hits.append((t.strip(), rest, ln))
    if len(hits) != 1:
        return None, None, "toc_entry_absent" if not hits else "toc_entry_ambiguous"
    t, rest, raw = hits[0]
    m = re.match(r"^\s*(.+?)\s*(?:[（(]\s*[\d+,，\s]+[)）])?\s*$", rest)
    names = [x for x in re.split(r"[\s、|，,；;]+", m.group(1)) if x] if m else []
    if not names or any(len(x) > 12 for x in names):
        return None, None, "toc_author_unparsed"
    authors = "；".join(names)                   # separator only; the names are copied as written
    entry = {"title": t, "author": authors, "venue": head.group(1), "year": int(head.group(2))}
    rec = {"url": url, "snapshot_file": F["file"], "snapshot_kind": "fetch", "route": "seed: institute toc",
           "date": today(), "toc_line": raw, "toc_header": head.group(0)}
    return entry, rec, None


CNKI_ID = re.compile(r"CJFDTotal-[A-Z]+(\d{4})(\d{2})\d+")
CNKI_SELF = re.compile(r"^([^\[\]\n|]+?)\[J\];([^;\n]+);(\d{4})年(\d{1,2})期", re.M)


def cnki_entry(url):
    """Record A from a cnki.com.cn article page, parsed in code. The fetched text carries the title (H1) and abstract;
    author, venue and issue appear only in CNKI's own catalogue line for the article ("authors;title[J];venue;
    YYYY年NN期"), listed under 相似文献. That line is accepted only if its title equals the H1 title (after norm)."""
    F = ds_fetch(url, "seed: cnki article page")
    if not F["ok"]:
        return None, None, "unfetchable_source"
    h1 = re.search(r"^#\s+(.+)$", F["text"], re.M)
    if not h1:
        return None, None, "field_unverified"
    title = h1.group(1).strip()
    uid = CNKI_ID.search(url)
    sim = F["text"].find("相似文献")
    if not uid or sim < 0:
        return None, None, "field_unverified"
    m = CNKI_SELF.search(F["text"][sim:].replace("|", "\n"))       # only the first catalogue line counts
    parts = [x.strip() for x in m.group(1).split(";") if x.strip()] if m else []
    if len(parts) < 2 or norm(parts[-1]) != norm(title) \
            or (int(m.group(3)), int(m.group(4))) != (int(uid.group(1)), int(uid.group(2))):
        return None, None, "field_unverified"
    authors = parts[:-1]
    ab = re.search(r"【摘要】[:：]\s*(.+)", F["text"])
    entry = {"title": title, "author": "；".join(authors), "venue": m.group(2).strip(), "year": int(m.group(3)),
             "volume_issue": f"{m.group(3)}年{m.group(4)}期"}
    if ab:
        entry["abstract"] = ab.group(1).strip()
    rec = {"url": url, "snapshot_file": F["file"], "snapshot_kind": "fetch", "route": "seed: cnki article page",
           "date": today(), "catalogue_line": m.group(0)}
    return entry, rec, None


def stage_s(args):
    cands = read_jsonl(cand_path())
    seen = {c["url"] for c in cands}
    fields = {j["name"]: j["field"] for j in JOURNALS_ZH}
    added = 0
    for row in read_jsonl(args.seed_file):
        srcs = [x["url"] for x in row.get("sources", []) if (x.get("fields_seen") or {}).get("title")]
        a = [u for u in srcs if host_of(u) in CNKI_HOSTS and CNKI_ID.search(u)]   # deviation 3 covers CNKI only
        b = [u for u in srcs if host_of(u) in TOC_HOSTS]
        why = None if a and b else ("no_record_a_url" if not a else "no_institute_toc_url")
        if why or a[0] in seen:
            jlog(os.path.join(W, "seed_skips.jsonl"), {"title": row.get("title"), "reason": why or "duplicate_url",
                                                         "seed_file": args.seed_file, "date": today()})
            continue
        c = {"cid": "s" + sha(a[0], 10), "url": a[0], "hint_title": row.get("title", ""),
             "query": "seed: " + os.path.basename(args.seed_file), "search_snapshot": None, "hit_index": None,
             "cell": ["article", "zh"], "meta": {"field": fields.get(row.get("journal"))}, "rank": None,
             "offset": None, "seed_from": args.seed_file, "seed_b_url": b[0], "date": today()}
        jlog(cand_path(), c)
        seen.add(a[0])
        added += 1
    print(f"[s] seeded candidates added: {added}")


def stage_a(args):
    cands = read_jsonl(cand_path())
    seen = {c["url"] for c in cands}
    have = collections.Counter(tuple(c["cell"]) for c in cands)
    nq = collections.Counter(tuple(q["cell"]) for q in read_jsonl(os.path.join(W, "harvest_queries.jsonl")))
    seed_log = os.path.join(W, "listing_seeds.jsonl")
    seeded = {s.get("seed_query") for s in read_jsonl(seed_log)}
    blocked, stat_paths = load_host_stats(getattr(args, "host_stats", None))
    print(f"[a] host steering: {len(blocked)} unfetchable hosts from {len(stat_paths)} tools log(s)"
          + (": " + ", ".join(sorted(blocked)[:12]) if blocked else ""))
    n_skipped = 0
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
            added, skipped, listings = 0, 0, []
            for k, r in enumerate(window):
                out = harvest_hit(r, eff + k, sfile, q, cell, meta, eff + k + 1, eff, allowed, seen, blocked=blocked)
                if out == "added":
                    added += 1
                    have[cell] += 1
                elif out == "skipped":
                    skipped += 1
                elif out == "listing":
                    listings.append(r)
            for r in listings[:3]:              # a listing only seeds item queries; it is never a record
                for sq in seed_queries(r, cell, meta):
                    if sq in seeded or have[cell] >= quota:
                        continue
                    seeded.add(sq)
                    res2, sf2 = ds_search(sq, 10, route=f"listing_seed: {r_url(r)}")
                    n2, s2 = 0, 0
                    for j, r2 in enumerate(res2):
                        out2 = harvest_hit(r2, j, sf2, sq, cell, meta, j + 1, 0, allowed, seen,
                                           seed_from=r_url(r), blocked=blocked)
                        if out2 == "added":
                            n2 += 1
                        elif out2 == "skipped":
                            s2 += 1
                    have[cell] += n2
                    added += n2
                    skipped += s2
                    jlog(seed_log, {"cell": list(cell), "listing_url": r_url(r), "harvest_query": q, "seed_query": sq,
                                    "search_snapshot": sf2, "added": n2, "skipped_host": s2, "date": today()})
            n_skipped += skipped
            jlog(os.path.join(W, "harvest_queries.jsonl"), {"cell": list(cell), "query": q, "count": offset + 10,
                                                           "offset_requested": offset, "offset_used": eff,
                                                           "returned": len(res), "listings_seen": len(listings),
                                                           "added": added, "skipped_host": skipped, "date": today()})
            nq[cell] += 1
    print(f"[a] candidates: {dict(have)}; hits skipped on unfetchable hosts this run: {n_skipped}")


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


def record_excerpts(st):
    """Sanitised record blocks (A, B) with excerpts around the key fields; shared by pre-screen and verification."""
    k, forms = st["key"], st.get("key_forms", {})
    recs = []
    for tag, r in zip(("A", "B"), st["records"]):
        f = forms.get(tag) or k
        txt = snapshot_text(r["snapshot_file"])
        recs.append({"url": r["url"], "custodian_class": r["custodian_class"], "route": sanitize(r["route"])[:200],
                     "snapshot_kind": r.get("snapshot_kind", "fetch"),
                     "excerpt": excerpt(txt, [f.get("title"), f.get("venue"), f.get("author"), f.get("volume_issue")])})
    return recs



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


def author_gap(d):
    """From an item_entry diag: the single verified hit entry if it has title, venue and year but no author
    (owner rule 3). Returns (entry_or_None, note)."""
    ents = d.get("verified")
    if not isinstance(ents, list):
        return None, "no_verified_dicts_in_diag"
    if len(ents) != 1:
        return None, "not_single_entry"
    v = ents[0]
    if v.get("author"):
        return None, "author_present"
    if not (v.get("title") and v.get("venue") and v.get("year")):
        return None, "title_venue_year_incomplete"
    if venue_key(v["title"]) == venue_key(v["venue"]):
        return None, "title_is_venue"
    return dict(v), "author_gap"

def merge_author(gap, d, F):
    """Take the author from the hit's own fetched page (fields verified on that page) into the hit entry.
    Same work required: the hit title is on the page; the page entry's title matches; year and venue do not conflict.
    Returns (merged_entry_or_None, result)."""
    if not loose_title_in(gap["title"], F["text"]):
        return None, "hit_title_absent_on_page"
    auths = {}
    for v in d.get("verified") or []:
        if not v.get("author") or not v.get("title"):
            continue
        if not (loose_title_in(gap["title"], v["title"]) or loose_title_in(v["title"], gap["title"])):
            continue
        if v.get("year") and v["year"] != gap["year"]:
            return None, "year_conflict"
        if v.get("venue"):
            a, b = venue_key(v["venue"]), venue_key(gap["venue"])
            if a != b and a not in b and b not in a:
                return None, "venue_conflict"
        auths[author_key(v["author"])] = v["author"]
    if not auths:
        return None, "author_not_on_page"
    if len(auths) > 1:
        return None, "ambiguous_author"
    return dict(gap, author=next(iter(auths.values()))), "ok"



def extract(snapfile, url, mode, target=None):
    # v2: verification source changed (verify_source), so old cached extractions are not reused
    key = f"{snapfile}__{mode}__v2__{sha(json.dumps(target, ensure_ascii=False) if target else '')}"
    path = os.path.join(EXTRACT_DIR, key + ".json")
    cached = read_json(path)
    if cached is not None:
        return cached
    raw = verify_source(snapfile)
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


def item_entry(snapfile, url, mode, target=None, diag=None):
    """Extract + verbatim-verify one snapshot and accept it only as an ITEM record. Returns (entry, None) or
    (None, reason). A page the extractor calls a list, or with complete verified entries for more than one distinct
    title, is a listing and is rejected (never repaired, never narrowed to one entry). If diag is a dict it is filled
    with what was seen (for the drop log only; it never affects the decision)."""
    ex = extract(snapfile, url, mode, target)
    parsed = parse_json_obj(ex.get("raw_output")) or {}
    if diag is not None:
        diag.update({"snapshot": snapfile, "page_kind": parsed.get("page_kind"), "n_entries": len(ex["entries"]),
                     "verified_fields": [sorted(k for k in e["verified"] if k != "work_type_llm") for e in ex["entries"][:5]],
                     "dropped_fields": [e["dropped_fields"] for e in ex["entries"][:5]]})
    if ex["call_rejected"] or not ex["parse_ok"]:
        return None, "extraction_failed"
    full = [e["verified"] for e in ex["entries"] if complete(e["verified"])]
    if parsed.get("page_kind") == "list" or len({norm(v["title"]) for v in full}) > 1:
        return None, "listing_page"
    if not full:
        return None, "field_unverified"
    return full[0], None


def cand_hit(c):
    """The candidate's own hit inside its saved search response: (index, hit) or (None, None)."""
    snap = read_json(os.path.join(SNAP, c.get("search_snapshot") or "-"), {}) or {}
    res = results_of(snap.get("response"))
    i = c.get("hit_index")
    if isinstance(i, int) and 0 <= i < len(res) and r_url(res[i]).split("#")[0] == c["url"]:
        return i, res[i]
    for j, r in enumerate(res):
        if r_url(r).split("#")[0] == c["url"]:
            return j, r
    return None, None


def record_from_hit(hit, idx, sfile, query, route, url, mode, target=None, diag=None):
    """Record from a search hit: the hit's JSON is the snapshot; the page is fetched (once) only if the hit lacks a
    field. If the hit verifies title/venue/year but lacks the author, the author may come from that fetched page
    (record keeps both snapshots; field_sources names the page for 'author').
    Returns (entry, record_dict, None) or (None, None, reason). diag (optional dict) receives a 'steps' log."""
    diag = {} if diag is None else diag
    steps = diag.setdefault("steps", [])
    why = "field_unverified"
    hfn, gap = None, None
    if hit is not None:
        ht = hit_text(hit)
        if is_listing_text(ht, str(hit.get("title", ""))):
            steps.append({"step": "hit", "result": "listing_text", "hit_title": str(hit.get("title", ""))[:80]})
            return None, None, "listing_page"
        if len(norm(ht)) >= 8:
            hfn = save_hit_snapshot(hit, sfile, idx, query, route)
            d = {"step": "hit", "hit_title": str(hit.get("title", ""))[:80]}
            e, why = item_entry(hfn, url, mode, target, d)
            d["result"] = why or "ok"
            if why == "field_unverified":
                gap, d["author_gap"] = author_gap(d)
            steps.append(d)
            if e is not None:
                return e, {"url": url, "snapshot_file": hfn, "snapshot_kind": "search_hit", "search_snapshot": sfile,
                           "hit_index": idx, "query": query, "route": route, "date": today()}, None
            if why == "listing_page":
                return None, None, why
        else:
            steps.append({"step": "hit", "result": "hit_text_too_short", "chars": len(norm(ht))})
    else:
        steps.append({"step": "hit", "result": "hit_not_in_search_snapshot"})
    F = ds_fetch(url, route)                      # single fetch: missing-field fallback and author check
    if not F["ok"]:
        steps.append({"step": "fetch", "result": "fetch_failed"})
        return None, None, ("unfetchable_source" if hit is None else why)
    if target and not loose_title_in(target["title"], F["text"]):
        steps.append({"step": "fetch", "result": "target_title_absent", "snapshot": F["file"]})
        return None, None, why
    d = {"step": "fetch"}
    e, why2 = item_entry(F["file"], url, mode, target, d)
    d["result"] = why2 or "ok"
    steps.append(d)
    if e is not None:
        return e, {"url": url, "snapshot_file": F["file"], "snapshot_kind": "fetch", "search_snapshot": sfile,
                   "hit_index": idx, "query": query, "route": route, "date": F["date"] or today()}, None
    if why2 != "listing_page" and gap is not None:
        m, res = merge_author(gap, d, F)
        steps.append({"step": "author_from_page", "result": res, "snapshot": F["file"]})
        if m is not None:
            return m, {"url": url, "snapshot_file": hfn, "snapshot_kind": "search_hit+page_author",
                       "author_snapshot_file": F["file"], "field_sources": {"author": F["file"]},
                       "search_snapshot": sfile, "hit_index": idx, "query": query, "route": route,
                       "date": F["date"] or today()}, None
    return None, None, (why2 if why2 == "listing_page" else why)


def _isbn10_ok(d):
    if not re.fullmatch(r"\d{9}[\dX]", d):
        return False
    return sum((10 - i) * (10 if c == "X" else int(c)) for i, c in enumerate(d)) % 11 == 0

def _isbn13_ok(d):
    if not re.fullmatch(r"97[89]\d{10}", d):
        return False
    return sum(int(c) * (1 if i % 2 == 0 else 3) for i, c in enumerate(d)) % 10 == 0

def isbn_variants(text):
    """Checksum-valid ISBNs written in the record text (ISBN-10 or -13, hyphenated or not, e.g. 'ISBN/价格： |
    7-301-10179-1'), each with its other form (10<->13). Only numbers the record itself prints are used."""
    t = unicodedata.normalize("NFKC", text or "")
    raw = [m.group(1) for m in re.finditer(r"ISBN[^\dXx]{0,15}([\dXx][\dXx\- ]{8,17})", t, re.I)]
    try:
        raw += list(find_isbns(t))
    except Exception:
        pass
    out = []
    def add(d):
        if d not in out:
            out.append(d)
    for r in raw:
        d = re.sub(r"[\- ]", "", str(r)).upper()
        for cand in (d[:13], d[:10]):
            if len(cand) == 13 and _isbn13_ok(cand):
                add(cand)
                if cand.startswith("978"):
                    core = cand[3:12]
                    c10 = (11 - sum((10 - i) * int(c) for i, c in enumerate(core)) % 11) % 11
                    add(core + ("X" if c10 == 10 else str(c10)))
                break
            if len(cand) == 10 and _isbn10_ok(cand):
                add(cand)
                core = "978" + cand[:9]
                c13 = (10 - sum(int(c) * (1 if i % 2 == 0 else 3) for i, c in enumerate(core)) % 10) % 10
                add(core + str(c13))
                break
    return out






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
    """Queries for an independent ITEM record (not issue browses, which return listings). Books: the record's own
    ISBNs in both forms, then a publisher-directed query (reaches publisher catalogues, a different custodian class
    from a library record A), then title/author/venue and catalogue queries."""
    typ, lang = cand["cell"]
    t, v, y = entry["title"], entry.get("venue") or "", entry.get("year") or ""
    parts = [ROLE_ZH.sub("", p) for p in author_parts(entry.get("author"))]
    a0 = parts[0].strip() if parts else ""
    qs = []
    if typ == "book":
        qs += [(f"ISBN {d}", "isbn") for d in isbn_variants(a_text)[:4]]
        if v:
            qs.append((f"{v} {t} {a0}".strip(), "publisher_title"))
    if lang == "zh":
        qs += [(f"{t} {a0}".strip(), "title_author"), (f"{t} {v} {y}".strip(), "title_venue"),
               (f"CiNii {t}", "catalogue_title")]
    else:
        qs += [(f"\"{t}\" {a0}".strip(), "title_author"), (f"{t} {v} {y}".strip(), "title_venue"),
               (f"CiNii {t}", "catalogue_title"), (f"WorldCat {t} {a0}".strip(), "catalogue_title")]
    out, seen = [], set()
    for q, r in qs:
        if norm(q) and norm(q) not in seen:
            seen.add(norm(q))
            out.append((q, r))
    return out


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
        if is_listing_url(c["url"]):
            return drop(st, "listing_page", "b", "record A URL is a listing: " + c["url"])
        diag = {}
        if c.get("seed_b_url") and host_of(c["url"]) in CNKI_HOSTS:
            entry, rec, why = cnki_entry(c["url"])
        else:
            idx, hit = cand_hit(c)
            route = f"harvest search: {c['query']}"
            entry, rec, why = record_from_hit(hit, idx, c["search_snapshot"], c["query"], route, c["url"], "A", diag=diag)
        if entry is None:
            return drop(st, why, "b" if why in ("unfetchable_source", "listing_page") else "c",
                        "record A: " + json.dumps(diag, ensure_ascii=False)[:1500])
        st["recA"] = dict(rec, custodian_class=cls)
        st["entryA"] = entry
        st["extract_files"] = {"A": rec["snapshot_file"]}
        save_state(st)
    entry = st["entryA"]
    if c.get("seed_b_url"):
        e, rec, why = toc_entry(c["seed_b_url"], entry["title"])
        if e is None:
            return drop(st, why, "b", "record B (institute toc): " + c["seed_b_url"])
        st["recB"] = dict(rec, custodian_class="institute_toc", pairing="aggregator_plus_institute_toc",
                          prereg_deviation="PREREG deviations 2-3: institute issue TOC as record B",
                          institutions=[reg_domain(host_of(c["url"])), reg_domain(host_of(c["seed_b_url"]))])
        st["entryB"] = e
        return
    a_cls = st["recA"]["custodian_class"]
    a_dom = reg_domain(host_of(c["url"]))
    a_text = verify_source(st["recA"]["snapshot_file"])      # record A's own text only (not our query/URL)
    qs = b_queries(entry, a_text, c)
    if not qs:
        return drop(st, "no_second_record", "b", "no route to a second record")
    target = {"title": entry["title"], "author": entry.get("author")}
    used_q = {norm(c["query"])}                 # record B must be reached by a different query
    tried, searches, n_hits = 0, 0, 0
    skips, fails, classes_seen = {}, {}, {}
    def skip(k):
        skips[k] = skips.get(k, 0) + 1
    for q, route in qs:
        if norm(q) in used_q or tried >= 4:
            continue
        used_q.add(norm(q))
        rt = f"{route}: {q}"
        res, sfile = ds_search(q, 10, route=rt)
        searches += 1
        if not res:
            skip("search_empty")
            continue
        for i, r in enumerate(res):
            if tried >= 4:
                break
            n_hits += 1
            u = r_url(r).split("#")[0]
            cl = classify(u) if u else None
            if not u:
                skip("no_url"); continue
            if not cl:
                skip("unclassified"); continue          # includes booksellers (BANNED): never records
            classes_seen[cl] = classes_seen.get(cl, 0) + 1
            # Different custodian class required (CNKI/VIP/Wanfang = one aggregator class, never pair), EXCEPT
            # owner deviation: library catalogues of different institutions (registered domains) pair.
            if cl == a_cls and cl != "library":
                skip("same_class"); continue
            if reg_domain(host_of(u)) == a_dom:
                skip("same_domain"); continue
            if is_listing_url(u) or is_listing_text(hit_text(r), str(r.get("title", ""))):
                skip("listing"); continue
            if not loose_title_in(entry["title"], hit_text(r)):
                skip("title_absent"); continue
            tried += 1
            e, rec, why = record_from_hit(r, i, sfile, q, rt, u, "B", target)
            if e is not None:
                lib_pair = cl == a_cls
                st["recB"] = dict(rec, custodian_class=cl,
                                  pairing="cross_institution_library" if lib_pair else "cross_class",
                                  prereg_deviation="owner: library catalogues of different institutions"
                                  if lib_pair else None,
                                  institutions=[a_dom, reg_domain(host_of(u))])
                return
            fails[why] = fails.get(why, 0) + 1
    drop(st, "no_second_record", "b",
         f"no independent item record found ({tried} tried; {searches} searches, {n_hits} hits; "
         f"A class={a_cls}; skipped={json.dumps(skips, ensure_ascii=False)}; "
         f"classes_seen={json.dumps(classes_seen, ensure_ascii=False)}; failed={json.dumps(fails, ensure_ascii=False)})")


# ----------------------------------------------------------------------------- stage c
def stage_c(st, args):
    if st.get("drop") or not st.get("recB") or st.get("entryB"):
        return
    rb, ea = st["recB"], st["entryA"]
    e, why = item_entry(rb["snapshot_file"], rb["url"], "B", target={"title": ea["title"], "author": ea.get("author")})
    if e is None:
        return drop(st, why, "c", "record B")
    st["entryB"] = e


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
                rec.update(status="unparseable", reason="clue_unparseable")
            else:
                clue = re.sub(r"\s+", " ", clue).strip()
                rec["clue"] = clue
                bad = clue_format_check(clue, st, payload)
                if bad:
                    rec.update(status="format_failed", reason="clue_format:" + bad)
                else:
                    rec.update(status="written", reason=None)
        st["clues"][w] = rec
        save_state(st)


# ----------------------------------------------------------------------------- stage f: leakage + identifiability
FINAL = {"call_rejected", "unparseable", "format_failed", "leak_failed", "ident_failed", "accepted", "flagged"}
PRE_G_FAIL = {"call_rejected", "unparseable", "format_failed", "leak_failed", "ident_failed"}
_CJK3 = re.compile(r"^[\u3400-\u9fff\uf900-\ufaff]{3}$")


def _words(s):
    return re.findall(r"[a-z0-9']+", deaccent(t2s(unicodedata.normalize("NFKC", str(s or ""))).lower()))


def leak_reason(clue, title):
    """Design C2: any shared 3-char Chinese substring or any shared 2-word English phrase with the title."""
    nt, nc = norm(title), norm(clue)
    for i in range(len(nt) - 2):
        g = nt[i:i + 3]
        if _CJK3.match(g) and g in nc:
            return f"zh3gram:{g}"
    wt, wc = _words(title), _words(clue)
    gt = {(wt[i], wt[i + 1]) for i in range(len(wt) - 1)}
    gc = {(wc[i], wc[i + 1]) for i in range(len(wc) - 1)}
    common = sorted(gt & gc)
    if common:
        return "en2gram:" + " ".join(common[0])
    return None


def stage_f(st, args):
    if st.get("drop") or not st.get("key") or not st.get("clues"):
        return
    for w, rec in st["clues"].items():
        if rec.get("status") != "written":
            continue
        lr = leak_reason(rec["clue"], st["key"]["title"])
        if lr:
            rec.update(status="leak_failed", reason="leakage:" + lr)
            save_state(st)
            continue
        res, sf = ds_search(rec["clue"], 10, route=f"identifiability:{w}")
        rank = hit_rank(res, st["key"]["title"], [r["url"] for r in st["records"]])
        rec["identifiability"] = {"query": rec["clue"], "rank": rank, "search_snapshot": sf}
        if rank:
            rec.update(status="passed_f", reason=None)
        else:
            rec.update(status="ident_failed", reason="identifiability_failed")
        save_state(st)
    decide_item(st, args)


def decide_item(st, args):
    """Item-level decision from clue statuses. Key flags drop the item; otherwise >=1 accepted clue accepts it."""
    if st.get("drop") or not st.get("key"):
        return
    clues = st.get("clues", {}) or {}
    kf = [w for w, c in clues.items() if c.get("key_flagged")]
    if kf:
        st.pop("accepted", None)
        flags = sorted({f for w in kf for f in clues[w].get("verify", {}).get("flags", []) if f in KEY_FLAGS})
        return drop(st, "verification_flag:key", "g", ",".join(flags))
    if any(c.get("status") == "accepted" for c in clues.values()):
        st["accepted"] = True
        return
    pending = [w for w in args.writers if w not in clues or clues[w].get("status") not in FINAL]
    pending += [w for w, c in clues.items() if c.get("status") == "passed_f"]
    if pending:
        return
    if not clues:
        return
    if all(c.get("status") in PRE_G_FAIL for c in clues.values()):
        reasons = sorted({str(c.get("reason")) for c in clues.values()})
        return drop(st, "clue_check_failed", "f", "; ".join(reasons))
    return drop(st, "verification_flag:clue", "g", "all clues flagged by verifier")


# ----------------------------------------------------------------------------- stage g: blind Opus verification
VERIFY_SYSTEM = """You audit candidate answer keys and clues for a bibliographic recall test (Chinese scholarship on the Yijing/Zhouyi, excavated manuscripts, early Chinese texts). You never approve or repair anything: you only raise flags. Code drops every flagged unit.
Each unit gives: key fields, two record URLs with their custodian class, a short excerpt from each saved record, and a search clue. (Numbers of 9+ digits were masked as [number].)
Flags (use only these names):
- field_not_in_excerpt: a key field (author, title, venue, year, volume_issue) is contradicted by, or clearly absent from, the excerpts.
- records_not_independent: the two URLs look like the same custodian, a mirror/copy of each other, or two aggregators (CNKI/VIP/Wanfang).
- not_primary: a URL is not a primary record (search snippet, citing paper, reference list, encyclopedia, blog, shop, forum).
- clue_misdescribes: the clue states something about the work (type, field, topic, decade, anchor value) not supported by the key/excerpts.
- clue_leaks: the clue gives the title or part of it, the exact year, volume, issue or pages.
- anchor_rule: the clue names neither or both of the author and the venue.
- other_fitting_work: you know another work that fits the clue about as well as the key.
- other: any other serious problem (explain in note).
Return only JSON: {"verdicts": [{"id": "<unit id>", "flags": [], "note": "<short>"}]} with exactly one verdict per unit id; an empty flags list means you found no problem."""


def excerpt(text, needles, width=300, cap=1200):
    pieces, covered = [], []
    for nd in needles:
        nd = str(nd or "").strip()
        if not nd:
            continue
        pos = text.find(nd)
        if pos < 0 and len(nd) > 8:
            pos = text.find(nd[:8])
        if pos < 0 or any(a <= pos <= b for a, b in covered):
            continue
        a, b = max(0, pos - width), min(len(text), pos + len(nd) + width)
        covered.append((a, b))
        pieces.append(text[a:b])
    if not pieces:
        pieces = [text[:600]]
    return sanitize(" … ".join(pieces))[:cap]


def unit_block(st, w, uid):
    k = st["key"]
    return {"id": uid, "key": {x: k.get(x) for x in ("author", "title", "venue", "year", "volume_issue")},
            "work_type": st["stratum"]["type"], "records": record_excerpts(st), "clue": st["clues"][w]["clue"]}


def prescreen_system():
    return (
        "You screen candidate bibliographic items before a more expensive check. You see one work: its key fields "
        "(author, title, venue, year, volume_issue), excerpts from the catalogue or journal records it was taken from, "
        "the target cell (type and language) and the field the harvest query was aimed at. Answer two questions.\n\n"
        "(a) on_topic: Is this work about the target field: Yijing/Zhouyi studies, excavated or transmitted early "
        "Chinese texts, early China, or Chinese philosophy of that period? A work on another region, on modern or "
        "contemporary society, or on an unrelated subject is not on topic.\n"
        "(b) type_match: Does the work's type match the cell?\n"
        "  - article = one article in a journal issue, or one article or chapter in an edited volume.\n"
        "  - book = a monograph, or a single edition of a text.\n"
        "  - An edited serial volume as a whole (one numbered volume of a series of collected papers, e.g. a "
        "volume titled like 《…研究》第六輯) is NOT an article. A journal issue as a whole is neither an article nor a book.\n\n"
        "Answer each question with \"yes\", \"no\" or \"unsure\", plus a one-line reason. Answer \"no\" only when "
        "the key and excerpts make it clear; if the evidence is thin, answer \"unsure\". Do not judge whether the "
        "record is accurate or whether the key is correct.\n\n"
        "Output only this JSON object:\n"
        "{\"on_topic\": \"yes|no|unsure\", \"on_topic_reason\": \"...\", "
        "\"type_match\": \"yes|no|unsure\", \"type_reason\": \"...\"}")


def prescreen_call(st, cand):
    """One cheap call per item (cid), cached on disk with its raw output. Runs in a worker thread: no state writes."""
    path = os.path.join(W, "prescreen", f"{st['cid']}.json")
    saved = read_json(path)
    if saved is not None and "raw_output" in saved:
        return saved
    k = st["key"]
    cell = list(cand.get("cell") or st.get("cell") or [st["stratum"]["type"], st["stratum"].get("language")])
    meta = cand.get("meta") or st.get("meta") or {}
    req = {"key": {x: k.get(x) for x in ("author", "title", "venue", "year", "volume_issue")},
           "records": record_excerpts(st),
           "cell": {"type": cell[0], "language": cell[1] if len(cell) > 1 else None},
           "harvest_field": meta.get("field")}
    user = json.dumps(req, ensure_ascii=False, indent=1)
    txt = openrouter_chat(EXTRACT_MODEL, [{"role": "system", "content": prescreen_system()},
                                          {"role": "user", "content": user}],
                          purpose="prescreen", anthropic=False)
    saved = {"cid": st["cid"], "date": today(), "model": EXTRACT_MODEL, "request": req, "raw_output": txt,
             "request_rejected": txt is None}
    write_json(path, saved)
    return saved


def apply_prescreen(st, saved):
    """Drop-only. An explicit 'no' drops; 'yes', 'unsure', missing or unparseable output never drops."""
    def yn(v):
        if isinstance(v, bool):
            return "yes" if v else "no"
        if isinstance(v, str):
            s = v.strip().strip(".").lower()
            if s in ("yes", "no", "unsure"):
                return s
        return None
    obj = parse_json_obj(saved.get("raw_output"))
    obj = obj if isinstance(obj, dict) else {}
    a, b = yn(obj.get("on_topic")), yn(obj.get("type_match"))
    ra, rb = str(obj.get("on_topic_reason", ""))[:240], str(obj.get("type_reason", ""))[:240]
    st["prescreen"] = {"file": f"prescreen/{st['cid']}.json", "parsed": bool(obj), "on_topic": a,
                       "on_topic_reason": ra, "type_match": b, "type_reason": rb, "date": today()}
    if a == "no":
        rule, detail = "prescreen:off_topic", ra + (f" | type_match=no: {rb}" if b == "no" else "")
    elif b == "no":
        rule, detail = "prescreen:type_mismatch", rb
    else:
        return None
    st.pop("accepted", None)
    drop(st, rule, "g_pre", detail)
    return rule


def stage_prescreen(args, states):
    """Cheap pre-screen of every item that has a unit about to go to Opus. One call per cid covers all its units
    (the inputs do not include the clue). Can only drop."""
    from concurrent.futures import ThreadPoolExecutor
    cmap = {c["cid"]: c for c in read_jsonl(cand_path())}
    todo = [st for st in states if not st.get("drop") and st.get("key")
            and any(r.get("status") == "passed_f" for r in (st.get("clues") or {}).values())]
    os.makedirs(os.path.join(W, "prescreen"), exist_ok=True)
    print(f"[g0] pre-screen: {len(todo)} items")
    dropped = collections.Counter()
    with ThreadPoolExecutor(max_workers=max(1, args.workers)) as ex:
        futs = [(st, ex.submit(prescreen_call, st, cmap.get(st["cid"], {}))) for st in todo]
        for st, fut in futs:
            saved = fut.result()          # InfraError / BudgetExceeded propagate; finished calls are already cached
            rule = apply_prescreen(st, saved)
            save_state(st)
            if rule:
                dropped[rule] += 1
    print(f"[g0] pre-screen drops: {dict(dropped) or 'none'}")






def verify_system():
    old = ("- not_primary: a URL is not a primary record (search snippet, citing paper, reference list, encyclopedia, "
           "blog, shop, forum).")
    new = ("- not_primary: a URL is not one work's own item record (article page or catalogue record): e.g. a listing, "
           "table of contents, search-result page, citing paper, reference list, encyclopedia, blog, shop, forum. "
           "snapshot_kind=search_hit means the excerpt is the search engine's result entry for that URL; it counts as "
           "the item record if the URL is the item's own page and the entry describes only that work.")
    new += ("\n- Exception (owner's PREREG deviations 2-3): a record with custodian_class=institute_toc is a complete issue "
            "table of contents on a research institute's portal; it counts as an item record, and you judge only whether "
            "its entry line for this work supports the key. A record routed 'seed: cnki article page' is the article's "
            "own CNKI page; the first line under 相似文献 is CNKI's own catalogue record of that article.")
    return VERIFY_SYSTEM.replace(old, new) if old in VERIFY_SYSTEM else VERIFY_SYSTEM + "\n" + new



def stage_g(args, states):
    stage_prescreen(args, states)                            # drop-only; dropped items are skipped below
    units = []
    for st in states:
        if st.get("drop") or not st.get("key"):
            continue
        for w, rec in (st.get("clues") or {}).items():
            if rec.get("status") == "passed_f":
                units.append((f"u{sha(st['cid'] + '|' + w + '|' + str(args.seed), 10)}", st, w))
    units.sort(key=lambda x: x[0])
    random.Random(f"{args.seed}:verify").shuffle(units)     # mixes writers; labels are never sent
    print(f"[g] units to verify: {len(units)}")
    system = verify_system()
    for i in range(0, len(units), 10):
        batch = units[i:i + 10]
        bid = "batch_" + sha("|".join(u[0] for u in batch), 12)
        bpath = os.path.join(VERIFY_DIR, bid + ".json")
        saved = read_json(bpath)
        if saved is None or not saved.get("raw_output"):         # an empty answer is retried, not judged
            blocks = [unit_block(st, w, uid) for uid, st, w in batch]
            user = json.dumps({"units": blocks}, ensure_ascii=False, indent=1)
            txt = openrouter_chat(OPUS, [{"role": "system", "content": system}, {"role": "user", "content": user}],
                                  purpose="verify", anthropic=True, max_tokens=32000,
                                  reasoning_tokens=16000)
            saved = {"batch": bid, "date": today(), "unit_ids": [u[0] for u in batch], "request_units": blocks,
                     "raw_output": txt, "writer_map_private": {uid: w for uid, _, w in batch}}
            write_json(bpath, saved)
        if not saved.get("raw_output"):
            print(f"[g] {bid}: verifier returned no answer; units left pending for the next run")
            continue
        obj = parse_json_obj(saved.get("raw_output"))
        vmap = {}
        if isinstance(obj, dict) and isinstance(obj.get("verdicts"), list):
            for v in obj["verdicts"]:
                if isinstance(v, dict) and isinstance(v.get("id"), str):
                    vmap[v["id"]] = v
        for uid, st, w in batch:
            rec = st["clues"][w]
            v = vmap.get(uid)
            if v is None:
                flags = ["no_verdict"]
            elif not isinstance(v.get("flags"), list):
                flags = ["malformed_verdict"]
            else:
                flags = sorted({(f if f in ALLOWED_FLAGS else "other") for f in v["flags"] if isinstance(f, str)})
            rec["verify"] = {"batch": bid, "uid": uid, "flags": flags, "note": str((v or {}).get("note", ""))[:400]}
            if flags:
                rec.update(status="flagged", reason="verification_flag:" + ",".join(flags))
            else:
                rec.update(status="accepted", reason=None)
            if set(flags) & KEY_FLAGS:
                rec["key_flagged"] = True
            decide_item(st, args)
            save_state(st)


# ----------------------------------------------------------------------------- candidate pipeline (b-f)
FN = {"b": stage_b, "c": stage_c, "d": stage_d, "e": stage_e, "f": stage_f}


def process(cid, args, stages):
    st = load_state(cid)
    if st.get("drop"):
        return st
    try:
        for s in stages:
            FN[s](st, args)
            save_state(st)
            if st.get("drop"):
                break
    except InfraError as e:
        jlog(os.path.join(W, "errors.jsonl"), {"ts": nowiso(), "cid": cid, "error": str(e)[:500]})
    finally:
        save_state(st)
    return st


def is_good(st):
    if st.get("drop"):
        return False
    return bool(st.get("accepted")) or any(c.get("status") in ("passed_f", "accepted")
                                           for c in (st.get("clues") or {}).values())


def run_candidates(args, stages):
    cids = sorted(_CANDS)
    random.Random(f"{args.seed}:order").shuffle(cids)
    states = {s["cid"]: s for s in all_states()}
    goal = math.ceil(args.target * args.overshoot)
    gate = len(stages) > 1
    budget_hit = None
    chunk = max(1, args.workers * 2)
    with ThreadPoolExecutor(max(1, args.workers)) as ex:
        for i in range(0, len(cids), chunk):
            if gate and sum(is_good(s) for s in states.values()) >= goal:
                print(f"[b-f] reached {goal} candidates with a passing clue; stopping intake")
                break
            futs = {ex.submit(process, cid, args, stages): cid for cid in cids[i:i + chunk]}
            for f, cid in futs.items():
                try:
                    states[cid] = f.result()
                except BudgetExceeded as e:
                    budget_hit = e
            done = sum(1 for s in states.values() if s.get("drop") or s.get("accepted") or is_good(s))
            print(f"[b-f] {min(i + chunk, len(cids))}/{len(cids)} processed; settled {done}; "
                  f"good {sum(is_good(s) for s in states.values())}; spent ${LEDGER.spent:.4f}")
            if budget_hit:
                raise budget_hit


# ----------------------------------------------------------------------------- outputs
def primary_clue(st, writers):
    acc = [w for w, c in (st.get("clues") or {}).items() if c.get("status") == "accepted"]
    order = list(writers) + [w for w in WRITERS if w not in writers]
    for w in order:
        if w in acc:
            return w
    return None


def item_record(st, writers):
    pw = primary_clue(st, writers)
    clues = st.get("clues") or {}
    return {"id": "B2-" + st["cid"], "stratum": st["stratum"], "key": st["key"],
            "key_forms": st.get("key_forms"), "records": st["records"],
            "clue": clues[pw]["clue"] if pw else None, "clue_writer": pw,
            "clues_by_writer": {w: {"clue": c.get("clue"), "status": c.get("status"), "anchor": c.get("anchor"),
                                    "identifiability": c.get("identifiability")} for w, c in clues.items()},
            "extra_acceptable_keys": [], "recoverability": st.get("recover"),
            "topic_source": st.get("topic_source"), "harvest": {"query": st["cand"]["query"],
                                                                "search_snapshot": st["cand"]["search_snapshot"],
                                                                "rank": st["cand"]["rank"], "offset": st["cand"]["offset"]}}


def write_jsonl(path, rows):
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    os.replace(tmp, path)


def finalize(args, note=""):
    load_cands()
    states = all_states()
    accepted = sorted([s for s in states if s.get("accepted") and not s.get("drop")], key=lambda s: s["cid"])
    by_cell = collections.defaultdict(list)
    for s in accepted:
        by_cell[(s["stratum"]["type"], s["stratum"]["language"])].append(s)
    chosen, rest = [], []
    for cell, share in CELLS.items():
        q = round(args.target * share)
        chosen += by_cell[cell][:q]
        rest += by_cell[cell][q:]
    for cell, lst in by_cell.items():
        if cell not in CELLS:
            rest += lst
    rest.sort(key=lambda s: s["cid"])
    while len(chosen) < args.target and rest:
        chosen.append(rest.pop(0))
    write_jsonl(os.path.join(W, "items.jsonl"), [item_record(s, args.writers) for s in chosen])
    write_jsonl(os.path.join(W, "reserve.jsonl"), [item_record(s, args.writers) for s in rest])
    dropped = [{"cid": s["cid"], "url": s["cand"]["url"], "cell": s["cand"]["cell"], **s["drop"],
                "key": s.get("key"), "clues": {w: {k: c.get(k) for k in ("status", "reason", "clue")}
                                               for w, c in (s.get("clues") or {}).items()}}
               for s in states if s.get("drop")]
    write_jsonl(os.path.join(W, "dropped.jsonl"), dropped)
    write_report(args, states, chosen, rest, dropped, note)
    print(f"[out] items {len(chosen)} (target {args.target}), reserve {len(rest)}, dropped {len(dropped)}; "
          f"spent ${LEDGER.spent:.4f}")


def write_report(args, states, chosen, rest, dropped, note):
    L = []
    L.append("# Battery 2 key building: REPORT\n")
    L.append(f"Generated {nowiso()} by build_keys.py (seed `{args.seed}`, target {args.target}, writers "
             f"{','.join(args.writers)}, --max-usd {args.max_usd}).\n")
    if note:
        L.append(f"**Run note:** {note}\n")
    cands = read_jsonl(cand_path())
    L.append("## Funnel\n")
    fun = collections.OrderedDict([
        ("harvested candidates", len(cands)),
        ("processed (state saved)", len(states)),
        ("record A fetched + fields verified", sum(1 for s in states if s.get("entryA"))),
        ("independent record B found", sum(1 for s in states if s.get("recB"))),
        ("key verified by code comparison", sum(1 for s in states if s.get("key"))),
        ("recoverable (search finds key)", sum(1 for s in states if (s.get("recover") or {}).get("rank"))),
        ("≥1 clue passed leakage + identifiability", sum(1 for s in states if any(
            c.get("status") in ("passed_f", "accepted", "flagged") for c in (s.get("clues") or {}).values()))),
        ("accepted after Opus verification", sum(1 for s in states if s.get("accepted") and not s.get("drop"))),
        ("written to items.jsonl", len(chosen)), ("surplus in reserve.jsonl", len(rest)),
        ("pending (no decision yet)", sum(1 for s in states if not s.get("drop") and not s.get("accepted")))])
    for k, v in fun.items():
        L.append(f"- {k}: {v}")
    proc = len(states)
    L.append(f"\nYield: {len(chosen) + len(rest)} accepted / {proc} processed candidates"
             f" = {((len(chosen) + len(rest)) / proc * 100 if proc else 0):.1f}%.\n")
    # --- sampling frame (host steering)
    L.append("## Sampling frame\n")
    srcs = ["tools.jsonl (this workdir)"] + [f"`{p}`" for p in (getattr(args, "host_stats", None) or [])]
    L.append("Host steering in harvest: a search hit that would otherwise be registered is skipped when its host has "
             "≥3 uncached DeepSeek fetch attempts and none returned status 200, counted over "
             + ", ".join(srcs) + " at harvest time. Skips are logged in harvest_skips.jsonl and are not counted as "
             "candidates.\n")
    skips = read_jsonl(os.path.join(W, "harvest_skips.jsonl"))
    if not skips:
        L.append("No hits were skipped.\n")
    else:
        hs = {}
        for s in skips:
            h = hs.setdefault(s.get("host"), {"hits": 0, "urls": set(), "cells": collections.Counter(), "att": 0})
            h["hits"] += 1
            h["urls"].add(s.get("url"))
            h["cells"]["/".join(s.get("cell") or [])] += 1
            h["att"] = max(h["att"], int(s.get("fetch_attempts") or 0))
        L.append("| host | skipped hits | distinct URLs | by cell | uncached fetch attempts (none 200) |")
        L.append("|---|---|---|---|---|")
        for host, h in sorted(hs.items(), key=lambda x: (-x[1]["hits"], str(x[0]))):
            cells = ", ".join(f"{c} {n}" for c, n in sorted(h["cells"].items()))
            L.append(f"| {host} | {h['hits']} | {len(h['urls'])} | {cells} | {h['att']} |")
        n_urls = len({s.get("url") for s in skips})
        L.append(f"\nItems on these {len(hs)} hosts cannot enter the set: {len(skips)} hits ({n_urls} distinct URLs) "
                 "were skipped. The item set therefore samples works whose records sit on hosts the DeepSeek fetch "
                 "tool can read, not every work the searches return.")
        early = [c for c in cands if host_of(c.get("url", "")) in hs]
        if early:
            acc_ids = {s["cid"] for s in chosen + rest}
            L.append(f"Exception: {len(early)} candidates on these hosts were registered before steering applied and "
                     f"were processed normally ({sum(1 for c in early if c['cid'] in acc_ids)} accepted).")
        L.append("")
    L.append("## Items by stratum (items.jsonl)\n")
    for dim in ("fame", "type", "language", "decade"):
        c = collections.Counter(s["stratum"][dim] for s in chosen)
        L.append(f"- {dim}: " + (", ".join(f"{k} {v}" for k, v in sorted(c.items())) or "none"))
    L.append(f"- post-cutoff (year ≥ {args.cutoff_year}): {sum(1 for s in chosen if s['stratum'].get('post_cutoff'))}")
    tgt = ", ".join(f"{t}/{l} {round(args.target * sh)}" for (t, l), sh in CELLS.items())
    L.append(f"- type×language targets: {tgt}")
    L.append("\nFame is set only from a citation count or holdings count stated on a primary record "
             f"(citations ≥{FAME_CIT[0]} famous, ≥{FAME_CIT[1]} mid; holdings ≥{FAME_HOLD[0]}/≥{FAME_HOLD[1]}); "
             "otherwise `unknown`. Fame and decade strata are reported, not enforced by quota.\n")
    L.append("## Drops by rule (item level)\n")
    dc = collections.Counter(d["rule"] for d in dropped)
    for k, v in dc.most_common():
        L.append(f"- {k}: {v}")
    L.append("\nDrops by rule and type×language:\n")
    dcc = collections.Counter((d["rule"], "/".join(d["cell"])) for d in dropped)
    for (r, c), v in sorted(dcc.items()):
        L.append(f"- {r} | {c}: {v}")
    L.append("\n`prescreen:*` drops come from a cheap EXTRACT_MODEL screen run before Opus; it can only drop "
             "(an explicit 'no'), never accept. Raw outputs: prescreen/<cid>.json.")
    # --- per-writer table
    calls = read_jsonl(os.path.join(W, "calls.jsonl"))
    L.append("\n## Writer comparison (same verified candidates)\n")
    L.append("| writer | clues produced | passed leakage | passed identifiability | flagged by Opus | accepted | writer cost | cost / accepted clue |")
    L.append("|---|---|---|---|---|---|---|---|")
    for w in WRITERS:
        recs = [(s, s["clues"][w]) for s in states if w in (s.get("clues") or {})]
        prod = [c for _, c in recs if c.get("clue")]
        pl = [c for c in prod if c.get("status") in ("passed_f", "ident_failed", "accepted", "flagged")]
        pi = [c for c in prod if c.get("status") in ("passed_f", "accepted", "flagged")]
        fl = [c for c in prod if c.get("status") == "flagged"]
        ac = [c for c in prod if c.get("status") == "accepted"]
        wc = [c for c in calls if c.get("purpose") == f"write:{w}"]
        known = all(c.get("cost_known", True) for c in wc)
        cost = sum(float(c.get("cost_usd") or 0) for c in wc)
        toks = (sum(c.get("prompt_tokens") or 0 for c in wc), sum(c.get("completion_tokens") or 0 for c in wc))
        cstr = f"${cost:.4f}" if known else f"tokens only: in {toks[0]}, out {toks[1]}"
        per = (f"${cost / len(ac):.4f}" if ac else "n/a") if known else "n/a (no price)"
        L.append(f"| {w} | {len(prod)} | {len(pl)} | {len(pi)} | {len(fl)} | {len(ac)} | {cstr} | {per} |")
    cfg = read_json(ds_native_cfg_path(), {}) or {}
    if cfg:
        L.append(f"\nDeepSeek native request: model `{DS_NATIVE_MODEL}`, thinking budget sent "
                 f"{cfg.get('budget')} (max_tokens {cfg.get('max_tokens')}); probe log: "
                 + "; ".join(f"{p['budget_tokens']}→{p['status']}" for p in cfg.get("probes", [])))
    if any(c.get("api") == "deepseek_native" and not c.get("cost_known") for c in calls):
        L.append("\nDeepSeek's own API returned no cost and no --ds-price-* prices were given: those calls are "
                 "logged with tokens only and counted as $0 against --max-usd.")
    L.append("\n### Examples of writer disagreement on the same item\n")
    ex = 0
    for s in states:
        cl = s.get("clues") or {}
        if len(cl) < 2 or not s.get("key"):
            continue
        if len({c.get("status") for c in cl.values()}) < 2:
            continue
        L.append(f"- **{s['key']['title']}** ({s['key']['year']})")
        for w, c in cl.items():
            L.append(f"  - {w}: {c.get('status')} {('(' + str(c.get('reason')) + ')') if c.get('reason') else ''} — "
                     f"{(c.get('clue') or '')[:160]}")
        ex += 1
        if ex >= 6:
            break
    if not ex:
        L.append("(none yet)")
    # --- cost
    L.append("\n## Cost\n")
    bym = collections.defaultdict(lambda: [0, 0.0, 0, 0, 0])
    for c in calls:
        m = bym[(c.get("api"), c.get("model"))]
        m[0] += 1
        m[1] += float(c.get("cost_usd") or 0)
        m[2] += c.get("prompt_tokens") or 0
        m[3] += c.get("completion_tokens") or 0
        m[4] += 0 if c.get("cost_known", True) else 1
    L.append("| api | model | calls | cost USD | prompt tok | completion tok | calls without cost |")
    L.append("|---|---|---|---|---|---|---|")
    for (api, model), m in sorted(bym.items(), key=lambda x: str(x[0])):
        L.append(f"| {api} | {model} | {m[0]} | {m[1]:.4f} | {m[2]} | {m[3]} | {m[4]} |")
    # --- cost by stage
    def stage_of(c):
        p = str(c.get("purpose") or "")
        if p.startswith("write:"):
            return "writing"
        if p == "verify":
            return "verification"
        if p == "prescreen":
            return "pre-screen"
        return "extraction"
    sc = collections.OrderedDict((k, {"n": 0, "usd": 0.0, "unk": 0, "purp": set()})
                                 for k in ("extraction", "pre-screen", "writing", "verification"))
    for c in calls:
        s = sc[stage_of(c)]
        s["n"] += 1
        s["usd"] += float(c.get("cost_usd") or 0)
        s["unk"] += 0 if c.get("cost_known", True) else 1
        s["purp"].add(str(c.get("purpose") or "?").split(":")[0][:30])
    n_acc = len(chosen) + len(rest)
    tot = sum(s["usd"] for s in sc.values())
    L.append("\n### Cost by stage\n")
    L.append("| stage | calls | cost USD | share | cost / accepted item | calls without cost | purposes |")
    L.append("|---|---|---|---|---|---|---|")
    for k, s in sc.items():
        share = f"{s['usd'] / tot * 100:.0f}%" if tot else "n/a"
        per = f"${s['usd'] / n_acc:.4f}" if n_acc else "n/a"
        purp = ", ".join(sorted(s["purp"])[:6])
        L.append(f"| {k} | {s['n']} | {s['usd']:.4f} | {share} | {per} | {s['unk']} | {purp} |")
    L.append(f"| **total** | {sum(s['n'] for s in sc.values())} | {tot:.4f} | 100% | "
             f"{('$' + format(tot / n_acc, '.4f')) if n_acc else 'n/a (0 accepted)'} | "
             f"{sum(s['unk'] for s in sc.values())} | |")
    n_units = sum(1 for s in states for c in (s.get("clues") or {}).values() if c.get("verify"))
    if n_units:
        L.append(f"\nOpus verification: {n_units} units verified, ${sc['verification']['usd'] / n_units:.4f} per unit. "
                 "'extraction' covers every model call not tagged prescreen, write:* or verify.")
    L.append(f"\nTotal model cost: ${LEDGER.spent:.4f} (OpenRouter: usage.cost plus "
             "cost_details.upstream_inference_cost for BYOK). Per-call log: calls.jsonl.")
    tools = read_jsonl(os.path.join(W, "tools.jsonl"))
    tc = collections.Counter((t.get("tool"), t.get("cached")) for t in tools)
    L.append(f"DeepSeek tool calls (not in model cost): search {tc[('search', False)]} live / "
             f"{tc[('search', True)]} cached; fetch {tc[('fetch', False)]} live / {tc[('fetch', True)]} cached.\n")
    # --- failures and gaps
    errs = read_jsonl(os.path.join(W, "errors.jsonl"))
    L.append("## What failed or was not done\n")
    L.append(f"- Infrastructure errors (items left pending, retried on rerun): {len(errs)}"
             + (f"; last: `{errs[-1]['error'][:200]}`" if errs else ""))
    if len(chosen) < args.target:
        L.append(f"- Shortfall: {len(chosen)} items of {args.target} targeted. No open-ended re-harvest is done; "
                 "rerun with a larger --harvest-factor to add candidates.")
    L.append("- extra_acceptable_keys is empty: the design's different-family comparison of the clue's top 10 (C3) "
             "is not run here; Opus may only flag `other_fitting_work`, which drops the clue.")
    L.append("- Negative controls (section B) and the six 50-item blocks are not built by this script.")
    L.append("- Clue-level drops keep the item if another writer's clue was accepted; a key-level flag from Opus drops "
             "the item for every writer.")
    with open(os.path.join(W, "REPORT.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(L) + "\n")


# ----------------------------------------------------------------------------- setup + main
def setup(args):
    global W, SNAP, STATE, CANDS_DIR, EXTRACT_DIR, CLUE_DIR, VERIFY_DIR, LEDGER, ARGS
    ARGS = args
    W = os.path.abspath(args.workdir)
    SNAP = os.path.join(W, "snapshots")
    STATE = os.path.join(W, "state")
    CANDS_DIR = os.path.join(STATE, "cands")
    EXTRACT_DIR = os.path.join(W, "extractions")
    CLUE_DIR = os.path.join(W, "clues")
    VERIFY_DIR = os.path.join(W, "verify")
    for d in (W, SNAP, STATE, CANDS_DIR, EXTRACT_DIR, CLUE_DIR, VERIFY_DIR):
        os.makedirs(d, exist_ok=True)
    LEDGER = Ledger(os.path.join(W, "calls.jsonl"), args.max_usd)
    load_cands()
    for s in all_states():
        k = s.get("key")
        if k and s.get("drop", {}).get("rule") != "duplicate":
            _DUPS.setdefault(norm(k["title"]) + "|" + norm(k["author"]), s["cid"])


def main():
    p = argparse.ArgumentParser(description="Build verified answer keys for Battery 2.")
    p.add_argument("--target", type=int, default=300, help="items to keep")
    p.add_argument("--max-usd", type=float, default=None, help="cumulative model-cost cap (all runs in workdir)")
    p.add_argument("--stage", default="all", choices=["s", "a", "b", "c", "d", "e", "f", "g", "report", "all"])
    p.add_argument("--seed-file", default=None, metavar="JSONL",
                   help="seeded intake (stage s) instead of search harvest (stage a)")
    p.add_argument("--writers", default="sonnet,opus,deepseek", help="subset of sonnet,opus,deepseek")
    p.add_argument("--workdir", default=".")
    p.add_argument("--seed", default="battery2")
    p.add_argument("--harvest-factor", type=float, default=6.0, help="candidates harvested per target item")
    p.add_argument("--overshoot", type=float, default=1.25, help="stop intake at target*overshoot passing items")
    p.add_argument("--cutoff-year", type=int, default=2025, help="year from which items count as post-cutoff")
    p.add_argument("--workers", type=int, default=4)
    p.add_argument("--ds-price-in", type=float, default=None, help="DeepSeek native USD per 1M input tokens")
    p.add_argument("--ds-price-out", type=float, default=None, help="DeepSeek native USD per 1M output tokens")
    p.add_argument("--ds-price-cache", type=float, default=None, help="DeepSeek native USD per 1M cached input tokens")
    p.add_argument("--host-stats", action="append", default=[], metavar="PATH",
                   help="another run's tools.jsonl used for host steering in harvest (repeatable)")
    args = p.parse_args()
    args.writers = [w.strip() for w in args.writers.split(",") if w.strip()]
    bad = [w for w in args.writers if w not in WRITERS]
    if bad or not args.writers:
        p.error(f"unknown writers {bad}; choose from {list(WRITERS)}")
    missing = [h for h in args.host_stats if not os.path.isfile(h)]
    if missing:
        p.error(f"--host-stats file(s) not found: {missing}")
    args.host_stats = [os.path.abspath(h) for h in args.host_stats]
    if args.stage == "s" and not args.seed_file:
        p.error("--stage s needs --seed-file")
    if args.seed_file:
        if not os.path.isfile(args.seed_file):
            p.error(f"--seed-file not found: {args.seed_file}")
        args.seed_file = os.path.abspath(args.seed_file)
    setup(args)
    note = ""
    try:
        if args.seed_file and args.stage in ("s", "all"):
            stage_s(args)
            load_cands()
        elif args.stage in ("a", "all"):
            stage_a(args)
            load_cands()
        if args.stage in ("b", "c", "d", "e", "f"):
            run_candidates(args, [args.stage])
        elif args.stage == "all":
            run_candidates(args, ["b", "c", "d", "e", "f"])
        if args.stage in ("g", "all"):
            stage_g(args, all_states())
    except BudgetExceeded as e:
        note = f"stopped cleanly at the cost cap: {e}"
        print("[budget] " + note)
    except InfraError as e:
        note = f"stopped on an infrastructure error (rerun to resume): {e}"
        print("[infra] " + note)
    except KeyboardInterrupt:
        note = "interrupted by user (rerun to resume)"
        print("[stop] " + note)
    finally:
        finalize(args, note)


if __name__ == "__main__":
    main()
