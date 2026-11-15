## Round 5 — Does the same-topic draw rate exceed what the pool predicts?

**Repo:** `/home/rr/Desktop/Desktop/nex5/`
**Date:** 2026-11-14
**Direction:** Beam AI, same thread, correcting Round 4's (`pool_exhaustion.txt`) reasoning about fire 3271.

**Append-only discipline starts with this entry**: this entry is permanent once written. Any later correction to it becomes a new dated entry below, not an edit to this one. Real queries and real raw output are inlined below, not condensed into conclusions.

### Why this round exists

Round 4 found 3 unrelated candidates sitting in fire 3271's eligible pool when a same-topic quote got drawn anyway, and read that as suggestive of preference. Beam corrected that: at fire 3271 the pool was already 67%-ish same-topic, so an unbiased random draw of 2 items would hit at least one same-topic item ~92% of the time purely by chance. One example proves nothing either way. This round runs the real test — control for each fire's own pool composition, across every fire the mechanism ever fired on — and checks whether the shortlist-building step itself (before any random pick) is where skew could enter.

### Falsifying-result statement — written before the full 2994-fire computation ran

*(Disclosure: one prior check had already run this round by this point — a single-fire validation of the shortlist-reconstruction method against fire 3271, done to reconcile with Beam's own 6-of-9 correction before trusting the method at scale. The statement below was written before the FULL computation ran, and was not adjusted after seeing its output.)*

> WOULD SHOW BIAS beyond pool composition: if, summed across all classifiable fires, the OBSERVED count of same-topic draws comes out MEANINGFULLY HIGHER than the EXPECTED count predicted by summing each fire's own hypergeometric P(at least one same-topic draw | that fire's actual pool size N and same-topic count K at that moment). A gap of a few fires out of thousands would not be meaningful; a gap large enough that it could not plausibly be explained by the sampling noise of running this many independent draws would be the signal that something beyond pool composition is pushing same-topic items through.
>
> WOULD SHOW NO BIAS beyond pool composition: if the observed count sits close to the expected count — consistent with the mechanism behaving like a genuinely pool-blind random draw once each fire's own realized pool make-up is accounted for, exactly as Beam's correction to last round's fire-3271 read already predicts should be the case in general, not just for that one fire.
>
> I will report the real observed-vs-expected numbers against this line, not adjust the line after seeing them.

**Result against this statement:** observed (629, 21.0%) is not higher than predicted (924.34, 30.9%) — it is *lower*, by 295 fires / 9.86 percentage points. This matches the "NO BIAS" branch even more cleanly than that branch anticipated (it said "close to," not "below"). Reported exactly as found.

### Task A — how is the shortlist actually built?

**A.1 — exact code**, `theory_x/stage6_fountain/generator.py`, `_build_recent_striking_block()`:

Step 1, raw eligible set (lines 2682-2688):
```python
now = time.time()
tag_rows = self._conversations_reader.read(
    "SELECT fountain_event_id, score FROM genius_tags "
    "WHERE class = 'STRIKING' AND tagged_at > ? AND tagged_at < ? "
    "ORDER BY score DESC LIMIT 200",
    (now - 24 * 3600, now - 300),
)
```
Sorted by `score` DESC — the tagger's own score, not recency-within-window or topic frequency.

Step 2, fetch text, re-impose order (lines 2699-2712):
```python
cand_ids = tuple(int(r["fountain_event_id"]) for r in tag_rows)
_cand = self._dynamic_reader.read(
    f"SELECT id, thought FROM fountain_events "
    f"WHERE id IN ({placeholders}) "
    f"AND thought IS NOT NULL AND length(thought) > 10",
    cand_ids,
)
_by_id = {int(r["id"]): r for r in (_cand or [])}
_ranked = [_by_id[i] for i in cand_ids if i in _by_id]
```
Only a length filter; no topic filtering.

Step 3, DEDUP to top-10 "distinct" (lines 2716-2743):
```python
_DEDUP_TH = 0.5
def _first_sentence_grams(_t):
    _s = re.split(r"(?<=[.!?])\s+", (_t or "").strip())
    _w = re.findall(r"[a-z0-9']+", (_s[0] if _s else "").lower())
    return {tuple(_w[i:i+5]) for i in range(len(_w) - 4)}
_kept_rows, _kept_grams = [], []
for _r in _ranked:
    if len(_kept_rows) >= 10:
        break
    _g = _first_sentence_grams(_r["thought"])
    _dupe = False
    for _kg in _kept_grams:
        _u = len(_g | _kg)
        if _u and len(_g & _kg) / _u >= _DEDUP_TH:
            _dupe = True
            break
    if _dupe:
        continue
    _kept_rows.append(_r)
    _kept_grams.append(_g)
```
Greedy, highest-score-first; a candidate is dropped only if its **first sentence's** 5-gram set overlaps an already-kept one by ≥50%. Surface-text near-duplicate filter, not topic-aware.

Step 4 (downstream of this round's scope, but relevant below): `sample(2)` from the deduped list, then a groove filter drops picks matching an active severe `groove_alert` pattern or a hardcoded chronic-phrase list, before anything is written into the prompt.

**A.2 — plain yes/no: YES.** The dedup step is a real, confirmed mechanical pathway for topical skew to enter the shortlist before any random pick happens. "Distinct" there is judged by first-sentence phrasing, not topic — a topic that keeps getting freshly reworded (confirmed earlier in this investigation: "all 15 fires are distinct text... each a paraphrase") will have genuinely different first sentences each time, so its own restatements won't dedupe against each other even though they're the same topic. Confirmed directly, not just reasoned about:

```
Validation: reconstructed fire 3271's real-time shortlist
(SQL window + dedup above, now = fire 3271's own ts = 1794344991.216032)

fire 3271 post-dedup shortlist size: 9
  3263 same_topic=True : 'I notice this fire engaged the world directly (branch: emerging_tech):'
  3255 same_topic=False: 'The item mentions the death of French wartime resistance heroine Solan'
  3257 same_topic=False: 'The November 3 Wikipedia featured article discusses updates to the con'
  3262 same_topic=True : '"This item discusses 'Our Most Aligned Model Yet,' highlighting twelve'
  3265 same_topic=True : "To make progress on both the investigation into 'Our Most Aligned Mode"
  3266 same_topic=True : 'Given the current signals and prior work, a concrete next step to make'
  3267 same_topic=True : 'Given the comparative analysis prior work, an additional next step wou'
  3247 same_topic=False: 'The evolving nature of language fascinates me. It shapes our understan'
  3261 same_topic=True : 'The item you provided discusses "Our Most Aligned Model Yet," highligh'
shortlist same-topic count: 6 of 9
```
This exactly matches Beam's own 6-of-9 correction once the dedup step is correctly included (Round 4's number, 7-of-10, had skipped dedup entirely and used the raw pre-dedup SQL rows — corrected here).

### Task B — the real test

**Method:** for every fire where the mechanism fired (`fountain_prompt_blocks.prefix LIKE 'Recent voice of yours%'`) with a non-null `focal_item`, rebuilt its exact real-time shortlist (same SQL + dedup as Task A, `now` = that fire's own ts, not the live clock), classified each shortlist candidate as same-topic by exact substring containment of a distinctive (≥4-char) word from the fire's own `focal_item`, computed N (pool size, ≤10), K (same-topic count), n = min(2, N), and the hypergeometric P(≥1 same-topic draw) = `1 - C(N-K, n) / C(N, n)`. Matched the fire's real stored quote back to the specific shortlist candidate it came from (within that fire's own small reconstructed shortlist, no cross-fire ambiguity) to get the OBSERVED outcome — which reflects the full pipeline including the downstream groove filter, not just the draw in isolation.

**Raw numbers:**
```
total STRIKING tags preloaded: 1663
total fires where the marker fired: 4357

classifiable fires (non-null focal_item, non-empty pool): 2994
unclassifiable (null focal_item): 1363
average pool size N: 9.71
average same-topic count K: 2.20
average same-topic FRACTION of pool: 22.677%

OBSERVED same-topic draws: 629 / 2994 = 21.009%
POOL-PREDICTED (sum of per-fire hypergeometric P(>=1 same-topic)): 924.34
  out of 2994 = 30.873%
difference: observed - predicted = -295.34 fires (-9.86 percentage points)

sanity check: of 2994 classifiable fires, 0 had a stored quote prefix
that did NOT match any reconstructed shortlist candidate
```

**Sample of the real per-fire table** (fire_id, focal_item, N, K, model P(≥1 same-topic), observed_same_topic, matched_to_shortlist):
```
(6, "Sebastian Raschka's from-scratch video course on building reasoning models", 1, 0, 0.0, False, True)
(8, 'He Wants AI Benchmarking To Be a Science, Not a Dark Art', 1, 0, 0.0, False, True)
(9, 'See Inside Cells Like Never Before in These Vivid Microscopic Images', 1, 1, 1.0, True, True)
(12, "In Leaked Audio, Flock CEO Tells Cops Backlash to the Company Isn't Real", 1, 0, 0.0, False, True)
(14, 'Storm Boelo leaves 22,000 without power as Met Office issues new wind warning', 1, 0, 0.0, False, True)
(16, 'Show HN: Hob - Open-source, on device alternative to Claude Cowork and ChatGPT', 1, 0, 0.0, False, True)
(17, 'Somebody please stop the spam texts', 1, 0, 0.0, False, True)
(19, "Sebastian Raschka's from-scratch video course on building reasoning models", 1, 0, 0.0, False, True)
(21, 'Oscar-winning producer says BBC gave her £400,000 payout after she raised antisemitism concerns', 1, 0, 0.0, False, True)
(22, 'Concerning behavior from a popular open-weight AI model', 2, 2, 1.0, True, True)
(23, 'Oscar-winning producer says BBC gave her £400,000 payout after she raised antisemitism concerns', 2, 0, 0.0, False, True)
(28, 'Israel and the US are both going to the polls - the consequences will be global', 3, 1, 0.6667, False, True)
(29, 'Fixing Tool-Call Accuracy in vLLM', 3, 0, 0.0, False, True)
(32, 'Israel and the US are both going to the polls - the consequences will be global', 3, 2, 1.0, False, True)
(33, 'Show HN: Hob - Open-source, on device alternative to Claude Cowork and ChatGPT', 3, 0, 0.0, False, True)
```
(Full 2994-row table retained in the session's working data for this round, `pool_bias_rows.json`, for anyone who wants to redo or audit this.)

**Straight comparison:** observed 21.0% vs. pool-predicted 30.9%. Not close to equal in the "biased toward" direction Beam was testing for — observed is *below* the pool-blind prediction, a 9.86-point gap in the opposite direction.

**On why the gap exists in that direction** (disclosed as a plausible reading, not independently confirmed further this round): the "predicted" number here models only the random-draw stage. It does not include the downstream groove-pattern filter (Task A, Step 4), whose entire design purpose is catching repeated/same-topic content. Since OBSERVED reflects the full pipeline including that filter while PREDICTED does not, a filter that disproportionately strips same-topic picks would mechanically produce exactly this shape of gap. Not simulated further this round — not needed to answer whether the draw rate *exceeds* the pool-predicted rate (it does not, by a wide margin, in either accounting).

### Confirmations

- Neither frozen file (`gui/server.py`, `theory_x/world_bridge/selector.py`) was touched or even read this round.
- `git diff --stat`: `theory_x/stage6_fountain/generator.py | 446 +++...`, 1 file changed, 446 insertions — identical to the diff that has existed since the Task-0 rename round. Zero edits made this round.
- No writes to any production/live table — every query used a read-only `file:...?mode=ro` URI connection.
- No detector, threshold, or recommendation proposed in this entry.
