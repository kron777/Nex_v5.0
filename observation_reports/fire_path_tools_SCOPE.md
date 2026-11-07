# Fire-path tool use — what "reachable outside a direct chat request" would actually mean

Not a pre-registration — nothing is built, nothing is proposed to arm. This
is the plain writeup Jon asked for before any work starts on this candidate,
so the decision whether to greenlight it gets made with full eyes open, not
after the fact. Read-only investigation; no code was written for this.

## 0. What exists today, exactly

`theory_x/stage_capability/tools.py` + `tool_caller.py` ("Theory X v2 Stage
B"). Three tools, already built, already live — **in the chat path only**
(confirmed by grep: `ToolCaller`/`ToolRegistry` are referenced nowhere in
`generator.py`, the fountain/fire loop):

1. **`web_fetch`** — HTTP GET, read-only, against an **allowlist of 12
   domains** (`news.ycombinator.com`, `arxiv.org`, `coindesk.com`,
   `decrypt.co`, `coingecko.com`, `openai.com`, `anthropic.com`,
   `deepmind.com`, `techcrunch.com`, `reuters.com`, `bbc.com`,
   `arstechnica.com`). Returns text. Cannot POST, cannot hit any other
   domain.
2. **`python_exec`** — runs Python in a subprocess. **Blocked imports**:
   `os`, `sys`, `subprocess`, `socket`, `requests`, `urllib`, `shutil`,
   `ftplib`, `http`, `smtplib`, `pickle`. **Allowed**: `math`, `statistics`,
   `json`, `datetime`, `re`, `collections`, `itertools`, `functools`,
   `string`, `random`, `decimal`. So: no filesystem access, no network from
   inside the sandbox, no subprocess-spawning-a-subprocess, no arbitrary
   package install — it can compute, not reach out or touch disk.
3. **`beliefs_query`** — read-only query against her own belief graph.

These safeguards (the allowlist, the import blocklist, the sandboxing) are
**per-call** and already in force regardless of who calls them. Exposing
these tools to the fire path would not remove or weaken any of them. What
would change is **who can trigger a call, and how often.**

## 1. What "reachable outside a direct chat request" means concretely

Today: a person asks something in chat → the chat path may decide a tool
call helps answer it → the tool runs once → the result goes into that
reply. There is a human on the other end of every call, and the call
happens because that specific person asked that specific thing.

The candidate would add a **second caller**: her autonomous fire loop
(`generator.py`, the fountain — the process that runs continuously, with no
person present, on its own cadence) would also be able to invoke the same
three tools, triggered by **something in her own internal state** — not a
person's request. Concretely, that's a new kind of decision that does not
exist in the codebase today: a mapping from "what she is currently thinking
about" to "whether to fetch something, compute something, or query her own
graph before finishing this thought."

## 2. When it would trigger — candidates, not a decision

Nothing is chosen. Plausible designs, each with a different risk profile:

- **Tied to open problems.** A fire that's working on an `open_problems` row
  could consult a tool before continuing — narrow, purpose-bound, already
  has a natural "why now" anchor.
- **Tied to uncertainty.** A fire flagged `uncertainty_stagnation` (an
  existing metacognition signal — an open problem that's been stuck, not
  resolving) could trigger a lookup — also narrow, and self-limiting (this
  signal is already rare, per this session's own exposure checks on
  similar metacognitive events).
- **Unconditional, any fire in a given mode** (e.g., every ARGUE or EXPLAIN
  fire gets a chance to consult a tool) — broad, and the one most likely to
  need a hard rate cap, since fire cadence is continuous (measured earlier
  this session at ~690/day).
- **A dedicated step before finalizing a thought** (draft → optionally
  consult → revise) — closest to how the chat path already uses tools, but
  a bigger structural change to the fire loop than the others.

## 3. What it could actually do, concretely, per tool

- **`web_fetch`** in the fire path: she could pull a page from one of the 12
  allowlisted domains and let its content inform an unprompted thought —
  genuinely new (broader sensing, on-demand instead of the fixed passive
  feed schedule), but bounded to the same 12 sources her sense adapters
  already poll from in large part.
- **`python_exec`** in the fire path: she could run a calculation
  mid-thought — verify a claim, check arithmetic, parse something — without
  the sandbox limits changing. This is the one most unlike anything she does
  today: computed, not generated, inside her own unprompted reasoning.
- **`beliefs_query`** in the fire path: she could look something up in her
  own graph before continuing a thought — the lowest-risk of the three,
  since it's read-only against data that's already hers and already
  retrieved into fires by other means; this is less a new capability than a
  more deliberate version of retrieval that already happens.

## 4. What stops it from running wild — and what's genuinely new risk

**Unchanged from today** (the existing, already-built safeguards): the
domain allowlist, the import blocklist, the subprocess sandbox. A fire-path
call is bound by exactly the same walls a chat-path call is.

**New, because the caller changes:**

- **No per-call human intent.** In chat, the person's own question bounds
  what's being fetched or computed — there's an implicit "why this, why
  now." In the fire path, the trigger is her own state, which means a new,
  untested inference step (state → tool call) has to exist and could
  misfire — fetch something unrelated to what's actually being thought
  about, or fixate on the same call repeatedly. This session already found
  two unrelated instances of exactly this failure shape this week (the
  metacognition digest's mis-scoped lookback, the harmonizer's LIMIT-200
  starvation) — a trigger-design mistake that looks fine in a unit test and
  then either never fires or fires on the wrong thing in production.
- **Volume.** The fire loop runs continuously and automatically
  (~690 fires/day measured this session). Even a modest per-fire trigger
  probability could produce far more outbound requests than any person
  would generate by hand — worth a hard cap (e.g., N calls/day) independent
  of whatever triggers it, not just a probability tuned by feel.
- **No one watching when it fires.** A chat tool call's result is read by
  the person who asked, immediately. An autonomous one isn't read by
  anyone unless something is built to surface it — without that, a fetched
  page or a computed result could shape an unprompted thought with nobody
  noticing it happened, let alone checking whether the result was sane.
- **`python_exec` specifically** is a qualitatively bigger step than the
  other two: even sandboxed, it's the one place "autonomous, unsupervised
  code execution" would be genuinely true of this system for the first
  time. `beliefs_query` triggered autonomously is comparatively the least
  new thing happening.

## 5. Questions worth answering before any build, not after

- All three tools, or start with just `beliefs_query` (lowest risk, least
  new) and treat `web_fetch`/`python_exec` as separate, later decisions?
- One flag for the whole capability, or one flag per tool — so, e.g.,
  `beliefs_query` could be armed independently of `python_exec` ever being
  considered?
- A hard daily call cap, set now, independent of whatever trigger design
  gets picked?
- Does every autonomous tool call get logged somewhere visible (the same
  idiom as r77's tripwire watch — a place Jon can check, not just an error
  log), so a fetch or a computation never silently shapes a thought
  unobserved?
- Is there a Step-0 exposure check available the way there was for Phase M
  and the harmonizer fix — i.e., can the proposed trigger condition's live
  base rate be measured *before* building, the same way `uncertainty_stagnation`
  or `open_problems` volume could be checked against the real corpus first?

Nothing above is built. This is the scope for Jon to decide against, not a
plan already in motion.
