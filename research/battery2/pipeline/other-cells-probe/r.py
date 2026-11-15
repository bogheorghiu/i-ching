"""retry wrapper: up to 3 tries on 5xx/-1; prints status+head."""
import sys, time
sys.path.insert(0, sys.argv[0].rsplit('/',1)[0])
import f
def get(which, url, tries=3):
    for i in range(tries):
        s = f.fetch(which, url, force=i > 0)
        if s["status"] not in (-1, 500, 502, 503, 504) and not (which=="ds" and s["status"]==404 and "failed to fetch" in str(s["response"])): return s, i+1
        time.sleep(3)
    return s, tries
if __name__ == "__main__":
    which, url = sys.argv[1], sys.argv[2]; n = int(sys.argv[3]) if len(sys.argv) > 3 else 800
    s, t = get(which, url); print(f"== {which} status={s['status']} tries={t}\n{f.text(s)[:n]}\n")
