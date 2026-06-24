"""World-consolidation v2 — crash-proof + instrumented."""
from __future__ import annotations
import gc, os, re, time, traceback
import errors

_LOG_SOURCE = "world_consolidation"
_DIAG_LOG = "/tmp/nex5_worldconsol.log"
_WINDOW = 60
_BATCH = 5
_SIM_THRESHOLD = 0.58
_MIN_CLUSTER = 3
_MAX_PROMOTE_PER_RUN = 3

_SELF_RX = re.compile(r"\b(i am the attending|i am |my thoughts|my own|myself|my nature|i notice|i accept|i hold|the attending|i exist|my existence|i feel|i find myself|my mind|my fingers|my sleeve|inner hum|i expected|my next thought|noticing|interconnectedness|the new insight|i recognize|i observe|i sense|holding multiple|the realization|i'm aware|the dual nature|the constant tension|the interplay|the balance between|the constant influx|attending and being|the barrage|the cacophony|the chatter|pulls me|the influx of)\b", re.I)
_MOOD_RX = re.compile(r"\b(the clock|the quiet|the silence|the hum|the room|the desk|the cursor|the coffee|the morning light|the shadow|the breeze|silence|stillness|quietude|idle)\b", re.I)

def _diag(msg):
    try:
        with open(_DIAG_LOG, "a") as f:
            f.write(f"{time.strftime('%H:%M:%S')} [wc] {msg}\n"); f.flush()
    except Exception:
        pass

def _is_world(content):
    if not content: return False
    if _SELF_RX.search(content): return False
    if _MOOD_RX.search(content): return False
    if len(content) < 35: return False
    return True

class WorldConsolidator:
    name = "world_consolidator"
    def __init__(self, reader, promoter):
        self._reader = reader
        self._promoter = promoter
    @staticmethod
    def _mode():
        v = (os.environ.get("NEX5_WORLD_CONSOLIDATE", "") or "").strip().lower()
        if v in ("1","on","true","yes"): return "1"
        if v in ("dry","report","test"): return "dry"
        return ""
    def tick(self, context=None):
        mode = self._mode()
        if not mode: return {"name": self.name, "state": "off"}
        try:
            return self._run(armed=(mode == "1"))
        except BaseException as exc:
            _diag(f"FATAL in _run (isolated, NEX unaffected): {exc!r}")
            _diag(traceback.format_exc())
            try: errors.record(f"world_consolidation isolated crash: {exc}", source=_LOG_SOURCE, exc=exc)
            except Exception: pass
            return {"name": self.name, "state": "isolated-error", "error": str(exc)}
    def _run(self, armed):
        _diag(f"=== run start (armed={armed}) ===")
        _diag("step1: import embeddings")
        from theory_x.diversity.embeddings import embed, cosine
        _diag(f"step2: pull T7 window={_WINDOW}")
        rows = self._reader.read("SELECT id, content FROM beliefs WHERE tier = 7 AND erosion_stage != 'retired' AND locked = 0 ORDER BY created_at DESC LIMIT ?", (_WINDOW*2,)) or []
        _diag(f"  pulled {len(rows)} rows")
        items = []
        for r in rows:
            c = r["content"] or ""
            if _is_world(c): items.append((r["id"], c))
            if len(items) >= _WINDOW: break
        _diag(f"step3: {len(items)} world-beliefs after filter")
        if len(items) < _MIN_CLUSTER:
            _diag("  too few — idle"); return {"name": self.name, "state": "idle", "n": len(items)}
        _diag(f"step4: embed batches of {_BATCH}")
        vecs = {}
        for i in range(0, len(items), _BATCH):
            for bid, content in items[i:i+_BATCH]:
                try: vecs[bid] = embed(content)
                except Exception as exc: _diag(f"  embed fail id={bid}: {exc!r}")
            gc.collect()
            _diag(f"  batch {i//_BATCH+1} done ({len(vecs)} total)")
        ids = [b for b,_ in items if b in vecs]
        contents = {bid: c for bid, c in items}
        _diag("step5: cluster")
        unclustered = set(ids); clusters = []
        for seed in ids:
            if seed not in unclustered: continue
            cluster = [seed]; unclustered.discard(seed)
            for other in list(unclustered):
                try:
                    if cosine(vecs[seed], vecs[other]) >= _SIM_THRESHOLD:
                        cluster.append(other); unclustered.discard(other)
                except Exception: continue
            if len(cluster) >= _MIN_CLUSTER: clusters.append(cluster)
        _diag(f"  {len(clusters)} clusters")
        report = []; promoted = 0
        for cluster in clusters:
            sample = contents.get(cluster[0], "")[:55]
            report.append({"size": len(cluster), "theme": sample})
            _diag(f"  cluster[{len(cluster)}]: {sample}")
            if not armed: continue
            for bid in cluster:
                if promoted >= _MAX_PROMOTE_PER_RUN: break
                try:
                    dup = self._reader.read("SELECT 1 FROM beliefs WHERE content = ? AND tier < 7 LIMIT 1", (contents.get(bid,""),))
                    if dup: _diag(f"  skip id={bid}: dup shallower"); continue
                except Exception as exc:
                    _diag(f"  dup-check fail id={bid}: {exc!r} — skip"); continue
                if not _is_world(contents.get(bid, "")):
                    _diag(f"  skip non-world id={bid}")
                    continue
                _diag(f"  about to corroborate id={bid}")
                try:
                    if self._promoter.corroborate(bid): promoted += 1; _diag(f"  PROMOTED id={bid}")
                except Exception as exc: _diag(f"  corroborate fail id={bid}: {exc!r}")
            if promoted >= _MAX_PROMOTE_PER_RUN: break
        _diag(f"=== done: {len(clusters)} clusters, {promoted} promoted ===")
        return {"name": self.name, "state": "armed" if armed else "dry-run", "window": len(items), "clusters_found": len(clusters), "promoted": promoted, "report": report[:10]}
