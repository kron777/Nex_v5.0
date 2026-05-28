#!/usr/bin/env python3
"""Pre-registered confirm/deny test: does cross-domain BREADTH at fire-time
separate genius from ordinary fires?

Thresholds fixed in advance (2026-05-28) so we cannot move goalposts:
  CONFIRMED : p < 0.05  AND  Cohen's d >= 0.4
  DENIED    : p > 0.20  OR   Cohen's d < 0.2
  PENDING   : anything in between, OR genius n < 30 (underpowered)

Circularity control: also reports the ACTIVITY (tempo) half. If activity is
also significant, the breadth result is flagged as possibly tempo-confounded.

Run: .venv/bin/python3 -m tools.test_breadth
"""
import sqlite3, statistics as st, math, sys

DB = "/home/rr/Desktop/nex5/data/dynamic.db"
MIN_GENIUS_N = 30
CONFIRM_P, CONFIRM_D = 0.05, 0.40
DENY_P, DENY_D = 0.20, 0.20

def welch_t(xs, ys):
    nx, ny = len(xs), len(ys)
    if nx < 2 or ny < 2:
        return 0.0, 1.0
    mx, my = st.mean(xs), st.mean(ys)
    vx, vy = st.variance(xs), st.variance(ys)
    if vx == 0 and vy == 0:
        return 0.0, 1.0
    se = math.sqrt(vx/nx + vy/ny)
    if se == 0:
        return 0.0, 1.0
    t = (mx - my) / se
    # Welch-Satterthwaite df
    df = (vx/nx + vy/ny)**2 / ((vx/nx)**2/(nx-1) + (vy/ny)**2/(ny-1))
    # two-sided p via normal approx (df usually large enough)
    p = 2 * (1 - 0.5*(1+math.erf(abs(t)/math.sqrt(2))))
    return t, p

def cohens_d(xs, ys):
    sx = st.pstdev(xs) if len(xs)>1 else 0
    sy = st.pstdev(ys) if len(ys)>1 else 0
    pooled = math.sqrt((sx**2+sy**2)/2) or 1e-9
    return (st.mean(xs)-st.mean(ys))/pooled

def main():
    con = sqlite3.connect(DB); con.row_factory = sqlite3.Row
    fires = [{"ts": float(f["ts"]), "hot_branch": f["hot_branch"]}
             for f in con.execute("SELECT ts, hot_branch FROM fountain_events WHERE ts IS NOT NULL")]
    def breadth(t):
        w = [f for f in fires if t-300 <= f["ts"] <= t]
        return len({f["hot_branch"] for f in w})
    def tempo(t):
        return len([f for f in fires if t-300 <= f["ts"] <= t])

    snaps = con.execute(
        "SELECT s.retention_tier AS tier, f.ts AS fts "
        "FROM substrate_snapshots s JOIN fountain_events f ON s.fountain_event_id=f.id "
        "WHERE s.retention_tier IS NOT NULL AND f.ts IS NOT NULL").fetchall()
    con.close()

    g_breadth = [breadth(float(s["fts"])) for s in snaps if s["tier"]=="genius"]
    o_breadth = [breadth(float(s["fts"])) for s in snaps if s["tier"]=="ordinary"]
    g_tempo   = [tempo(float(s["fts"]))   for s in snaps if s["tier"]=="genius"]
    o_tempo   = [tempo(float(s["fts"]))   for s in snaps if s["tier"]=="ordinary"]

    print(f"=== BREADTH confirm/deny test (pre-registered thresholds) ===\n")
    print(f"  genius n={len(g_breadth)}   ordinary n={len(o_breadth)}")
    if len(g_breadth) < MIN_GENIUS_N:
        print(f"\n  VERDICT: PENDING — genius n={len(g_breadth)} < {MIN_GENIUS_N} (underpowered)")
        print(f"  Need {MIN_GENIUS_N - len(g_breadth)} more genius snapshots. Re-run later.")
        return

    t, p = welch_t(g_breadth, o_breadth)
    d = cohens_d(g_breadth, o_breadth)
    tt, tp = welch_t(g_tempo, o_tempo)
    td = cohens_d(g_tempo, o_tempo)

    print(f"\n  BREADTH (branches): genius={st.mean(g_breadth):.2f} ordinary={st.mean(o_breadth):.2f}")
    print(f"    t={t:.2f}  p={p:.4f}  d={d:+.2f}")
    print(f"  TEMPO (fires, control): genius={st.mean(g_tempo):.2f} ordinary={st.mean(o_tempo):.2f}")
    print(f"    t={tt:.2f}  p={tp:.4f}  d={td:+.2f}")

    print()
    if p < CONFIRM_P and abs(d) >= CONFIRM_D:
        verdict = "CONFIRMED — breadth separates genius from ordinary"
        if tp < 0.05:
            verdict += "\n  WARNING: tempo ALSO significant — possible tempo confound, interpret with care"
    elif p > DENY_P or abs(d) < DENY_D:
        verdict = "DENIED — breadth does not separate; joins the null pile"
    else:
        verdict = f"PENDING — in-between zone (p={p:.3f}, d={d:.2f}); keep accumulating"
    print(f"  VERDICT: {verdict}")

if __name__ == "__main__":
    main()
