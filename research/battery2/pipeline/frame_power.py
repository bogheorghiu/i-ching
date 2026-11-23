"""Threshold and power for the frame test of CONTROLS-RULE.md section 17 (standard library only, exact sums).

Run: python3 -I frame_power.py

A round shows a judge M questions, K of them trick questions, says that K are tricks, and asks which. A hit is a pick
that is a trick question. The test says "the judge can tell" when the hits over R rounds reach a threshold t: the
smallest t whose chance tail is at most ALPHA. "Right p of the time" means each pick is a trick with probability p.
Design A is the one section 17 registers (17.5, 17.6); B and C are the two others the owner was offered (17.5.1).
"""
from math import comb

ALPHA = 0.10            # 17.6.3: a false pass is the costly error, so the bar for "can tell" is set low
P_GRID = [0.30, 0.35, 0.40, 0.50, 0.70, 0.90]
FRAMES = 3              # 17.7: at most three frames are tried after the positive control


def binom_pmf(n, p):
    return [comb(n, k) * p ** k * (1 - p) ** (n - k) for k in range(n + 1)]


def hyper_pmf(m, k, picks):
    """Hits in one round under chance: picks drawn from m questions of which k are tricks."""
    return [comb(k, h) * comb(m - k, picks - h) / comb(m, picks) for h in range(picks + 1)]


def convolve(a, b):
    out = [0.0] * (len(a) + len(b) - 1)
    for i, x in enumerate(a):
        for j, y in enumerate(b):
            out[i + j] += x * y
    return out


def total(per_round, rounds):
    dist = [1.0]
    for _ in range(rounds):
        dist = convolve(dist, per_round)
    return dist


def tail(dist, t):
    return sum(dist[t:])


def threshold(null):
    return next(t for t in range(len(null)) if tail(null, t) <= ALPHA)


def design(name, m, k, rounds, note=""):
    null = total(hyper_pmf(m, k, k), rounds)
    t = threshold(null)
    print(f"\n{name}: M={m} questions, K={k} trick, R={rounds} rounds, {k * rounds} picks; chance per pick {k / m:.3f}")
    if note:
        print(f"  {note}")
    print(f"  threshold t = {t} hits (chance tail P(hits >= t) = {tail(null, t):.4f}; at t-1: {tail(null, t - 1):.4f})")
    print(f"  a judge at chance is wrongly said to tell (frame fails although indistinguishable): {tail(null, t):.4f}")
    print("  p = per-pick rate | P(test says 'can tell') | P(frame wrongly passes) | P(>=1 of 3 such frames passes)")
    for p in P_GRID:
        alt = total(binom_pmf(k, p), rounds)      # per-round hits as k independent picks (exact for K=1)
        pw = tail(alt, t)
        print(f"  {p:.2f} | {pw:.4f} | {1 - pw:.4f} | {1 - pw ** FRAMES:.4f}")
    return t


def main():
    print(f"ALPHA = {ALPHA}; frames tried at most {FRAMES}")
    design("A (registered): one trick per round", 5, 1, 20)
    design("B (the owner's first form, one frame): two tricks per round", 6, 2, 10,
           "power uses 2 independent picks per round with rate p: an approximation (picks of one round are not independent)")
    # C: three frames in one round (M=7, one trick per frame). Per frame, a hit is a round in which that frame's trick is
    # among the 3 picks: 3/7 by chance if the frame is indistinguishable. Treated as binomial(20, 3/7), an approximation
    # that ignores that an obvious frame takes a pick from the others (which makes the others look better than they are).
    null_c = binom_pmf(20, 3 / 7)
    tc = threshold(null_c)
    print("\nC (three frames per round, one trick each, M=7, R=20): per frame, rounds in which its trick is picked")
    print(f"  threshold {tc} of 20 rounds, chance tail {tail(null_c, tc):.4f}; p = P(that frame's trick is picked)")
    for p in P_GRID:
        print(f"    p={p:.2f}: P(can tell) = {tail(binom_pmf(20, p), tc):.4f}")
    print("\nReal clues used: A 20 x 4 = 80; B 10 x 4 = 40; C 20 x 4 = 80; pool 90 (distinct ids, 17.2.1).")
    print("Judge calls (before voids): A 20 per frame, positive control 20, at most 3 frames: at most 80;"
          " B 10 per frame: at most 40; C 20 + 20 positive control = 40.")


if __name__ == "__main__":
    main()
