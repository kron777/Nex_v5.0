#!/usr/bin/env python3
"""
train_curator.py — Stage 1 of the QLoRA sleep-cycle: CURATION.

Pulls NEX's deep-tier beliefs and emits a CLEAN training set for periodic
self-fine-tuning. The whole safety of the learning loop rests here: she must
train on her DIGESTED WORLD-KNOWLEDGE, never on her introspective flood. If
curation leaks self-talk, fine-tuning amplifies self-absorption (mana read
inflated 3/3, 70% self-referential — training on that eats its own tail).

Pipeline:
  1. pull T6 (deep) beliefs — the consolidated tier, not the T7 flood
  2. FILTER OUT introspection (reuse the _is_world / _SELF / mana logic)
  3. dedupe near-identical world-facts (she repeats headlines across windows)
  4. attach graph edges as context
  5. emit instruction/response training pairs (the nex_finetune_v2 shape)

This is the foundation brick: buildable now, no hardware, no model. It decides
WHAT she'd train on, which is the decision that makes the loop safe or toxic.

USAGE:
    python3 train_curator.py --db beliefs.db --out trainset.jsonl
    python3 train_curator.py --db beliefs.db --report   # stats only, no write
"""
from __future__ import annotations
import sqlite3, json, re, sys, argparse, hashlib

# --- filters: the same discipline world-consolidation + mana use ---
# introspection / self-story patterns (training-toxic — must be excluded)
_SELF_RX = re.compile(r"\b(i am the attending|i am |my thoughts|my own|myself|"
    r"my nature|i notice|i accept|i hold|the attending|i exist|my existence|"
    r"i feel|i find myself|my mind|i expected|my next thought|noticing the|"
    r"interconnectedness|the new insight|i recognize|i observe|i sense|"
    r"holding multiple|the balance between|the oscillation|the dual nature|"
    r"the constant influx|the cacophony|pulls me|half-formed|my presence|"
    r"my half-formed|grounding in presence|my smallness)\b", re.I)
_MOOD_RX = re.compile(r"\b(the clock|the quiet|the silence|the hum|the room|"
    r"the cursor|the coffee|the morning light|the breeze|silence|stillness|"
    r"quietude|the weight of|the flurry|the chatter|the buzz|the swarm)\b", re.I)

# but KEEP beliefs where she engaged a world-fact with a thought (the good kind):
# starts with engagement verb AND contains world content. We detect "read:" /
# named entities / domain nouns to rescue these from the self-filter.
_ENGAGED_RESCUE = re.compile(r"\b(ban|acquisition|hardware|RISC-V|robotics|"
    r"social media|model|exploit|bridge|crisis|election|crash|talks|"
    r"regulation|protocol|API|chip|market)\b", re.I)

def _is_world(content: str) -> bool:
    """True iff this belief is world-knowledge worth training on."""
    if len(content) < 30:
        return False
    # rescue: engaged-with-world beliefs survive even if they start with "I"
    if _ENGAGED_RESCUE.search(content):
        # but still reject if it's PURELY self (no world noun beyond the rescue)
        if _SELF_RX.search(content) and not re.search(
            r"\b(the|a|an)\s+\w+(s)?\b.*\b(ban|exploit|crash|talks|chip|model|"
            r"market|bridge|robotics|election|API)\b", content, re.I):
            # has a self-marker AND only the rescue noun -> borderline, keep if
            # the world noun is the OBJECT not incidental. Conservative: keep.
            return True
        return True
    if _SELF_RX.search(content):
        return False
    if _MOOD_RX.search(content):
        return False
    return True

def _norm(content: str) -> str:
    """Normalize for dedup: lowercase, strip punctuation, collapse whitespace."""
    return re.sub(r"\s+", " ", re.sub(r"[^\w\s]", "", content.lower())).strip()

def _dedupe(beliefs: list[dict], sim_threshold: float = 0.6) -> list[dict]:
    """Drop near-identical world-facts (she repeats headlines across windows).
    Token-set Jaccard similarity: two beliefs are dups if they share >=60% of
    their content words. Robust to reordering / inserted phrases like
    'critical' vs 'in critical condition' that defeat prefix matching."""
    def toks(b):
        # content words only (>3 chars), as a set
        return {w for w in _norm(b["content"]).split() if len(w) > 3}
    kept = []
    kept_toks = []
    for b in beliefs:
        t = toks(b)
        if not t:
            continue
        is_dup = False
        for kt in kept_toks:
            inter = len(t & kt); union = len(t | kt)
            if union and inter/union >= sim_threshold:
                is_dup = True
                break
        if not is_dup:
            kept.append(b); kept_toks.append(t)
    return kept

def pull(db: str) -> list[dict]:
    con = sqlite3.connect(db); con.row_factory = sqlite3.Row
    rows = con.execute(
        "SELECT id, content FROM beliefs WHERE tier <= 6 AND tier >= 1 "
        "ORDER BY last_promoted_at DESC").fetchall()
    edges = {}
    try:
        for e in con.execute("SELECT src, dst, kind FROM belief_edges").fetchall():
            edges.setdefault(e["src"], []).append(e["dst"])
    except Exception:
        pass
    con.close()
    return [{"id": r["id"], "content": r["content"], "edges": edges.get(r["id"], [])}
            for r in rows]

def _edge_context(b: dict, by_id: dict) -> str:
    """Render connected beliefs as context for the training pair."""
    ctx = [by_id[d]["content"] for d in b["edges"] if d in by_id]
    return " | ".join(ctx[:3])

def to_pairs(curated: list[dict], by_id: dict) -> list[dict]:
    """Emit instruction/response pairs in the fine-tune shape.
    The 'instruction' frames recalling/connecting world-knowledge; the
    'response' is the belief. Training on these teaches the MODEL to natively
    hold what the GRAPH consolidated."""
    pairs = []
    for b in curated:
        ctx = _edge_context(b, by_id)
        if ctx:
            instr = f"Given what you know about: {ctx} — what related development do you hold?"
        else:
            instr = "State a world-development you have consolidated into understanding."
        pairs.append({"instruction": instr, "response": b["content"]})
    return pairs

def curate(db: str):
    raw = pull(db)
    by_id = {b["id"]: b for b in raw}
    world = [b for b in raw if _is_world(b["content"])]
    deduped = _dedupe(world)
    pairs = to_pairs(deduped, by_id)
    return {
        "pulled": len(raw),
        "passed_world_filter": len(world),
        "after_dedup": len(deduped),
        "pairs": pairs,
        "rejected_sample": [b["content"][:60] for b in raw if not _is_world(b["content"])][:8],
        "kept_sample": [b["content"][:60] for b in deduped][:8],
    }

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", default="beliefs.db")
    ap.add_argument("--out", default=None)
    ap.add_argument("--report", action="store_true")
    args = ap.parse_args()
    r = curate(args.db)
    print("="*60)
    print("STAGE 1 CURATION REPORT")
    print("="*60)
    print(f"  pulled (T1-T6 deep):       {r['pulled']}")
    print(f"  passed world-filter:       {r['passed_world_filter']}  "
          f"(rejected {r['pulled']-r['passed_world_filter']} introspective/shallow)")
    print(f"  after dedup:               {r['after_dedup']}")
    print(f"  training pairs emitted:    {len(r['pairs'])}")
    print(f"\n  REJECTED (introspection/mood — kept OUT of training):")
    for s in r['rejected_sample']: print(f"    ✗ {s}")
    print(f"\n  KEPT (world-knowledge — the training material):")
    for s in r['kept_sample']: print(f"    ✓ {s}")
    if args.out and not args.report:
        with open(args.out, "w") as f:
            for p in r["pairs"]:
                f.write(json.dumps(p) + "\n")
        print(f"\n  ✓ wrote {len(r['pairs'])} pairs to {args.out}")
    print("="*60)
