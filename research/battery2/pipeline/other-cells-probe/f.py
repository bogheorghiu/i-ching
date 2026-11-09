"""fetch a URL through one fetch API; save raw response; print status + size + head."""
import json, sys, hashlib, os, urllib.request, urllib.error, time
API = {"ds": "https://api.deepseek.com/v1/tools/fetch", "ms": "https://api.moonshot.ai/v1/tools/fetch"}
def fetch(which, url, force=False):
    fn = f"snap/{which}_{hashlib.sha256(url.encode()).hexdigest()[:16]}.json"
    os.makedirs("snap", exist_ok=True)
    if os.path.exists(fn) and not force:
        return json.load(open(fn))
    req = urllib.request.Request(API[which], data=json.dumps({"url": url}).encode(), method="POST",
        headers={"Content-Type": "application/json", "Authorization": "Bearer placeholder"})
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            st, raw = r.status, r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        st, raw = e.code, e.read().decode("utf-8", "replace")
    except Exception as e:
        st, raw = -1, repr(e)
    try: js = json.loads(raw)
    except Exception: js = None
    snap = {"which": which, "url": url, "status": st, "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "response": js if js is not None else raw[:50000]}
    json.dump(snap, open(fn, "w"), ensure_ascii=False)
    with open("calls.jsonl", "a") as f: f.write(json.dumps({"which": which, "url": url, "status": st, "ts": snap["ts"]}) + "\n")
    return snap
def text(snap):
    js = snap["response"]
    if not isinstance(js, dict): return str(js)
    parts = []
    for d in (js, js.get("data") if isinstance(js.get("data"), dict) else {}):
        for k in ("title", "content", "text", "markdown"):
            if isinstance(d.get(k), str): parts.append(d[k])
    return "\n".join(parts) if parts else json.dumps(js, ensure_ascii=False)
if __name__ == "__main__":
    which, url = sys.argv[1], sys.argv[2]
    n = int(sys.argv[3]) if len(sys.argv) > 3 else 600
    for w in (["ds", "ms"] if which == "both" else [which]):
        s = fetch(w, url); t = text(s)
        print(f"== {w} status={s['status']} len={len(t)}\n{t[:n]}\n")
