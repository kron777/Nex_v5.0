# Web-fetch URL and redirect boundary — 28 November 2026

**Base:** `kron777/Nex_v5.0` main at `81ec438a7be7fe3cc81112cbb39c715b76ffe026` (after #378 request-drain and #381 cognitive-characterization merges).  
**Scope:** bounded hardening of the existing read-only `web_fetch` capability. No feature flag, capability list, prompt policy, runtime deployment or governing document changed.

## 1. Source finding

`theory_x/stage_capability/tools.py` checked the initial URL against `_ALLOWED_DOMAINS`, then called `urllib.request.urlopen()`. Python's default redirect handler follows HTTP redirects automatically. The allowlist was therefore applied to the initial host, not to the final network destination. An allowlisted origin able to redirect could cause the tool to request a destination that had not passed the allowlist.

The original host parsing also used `parsed.netloc.lstrip("www.")`. `lstrip` removes any leading characters from a character set, not one exact prefix; `netloc` also includes optional user-info and port. This could reject legitimate allowlisted hostnames with ports and did not explicitly reject embedded URL credentials or non-HTTP schemes.

The existing tests covered an unknown initial domain, but did not characterize redirect handling, explicit ports, credentials or scheme validation. A second trace found that `ToolCaller.should_use_tool()` selected `web_fetch` for generic current/factual questions even though the fetcher only accepts an explicit URL or a small supported CoinGecko symbol map. The chat route passed `[]` as the beliefs argument, so the generic `not beliefs` fallback always treated the belief context as absent. Those generic calls then failed with `no URL to fetch`. The correction removes that unused selector argument and updates the chat call site, rather than retaining a misleading placeholder. The CoinGecko builder also used substring matching, so `eth` inside an unrelated word such as `whether` could be mistaken for a symbol.

## 2. Bounded correction

- Parse with `urlsplit` and validate the scheme as `http` or `https`.
- Reject URLs containing username/password components.
- Compare the normalized `hostname` (lowercase, trailing dot removed) against the existing exact/subdomain allowlist; the port no longer contaminates hostname matching.
- Supply a custom `HTTPRedirectHandler` whose `redirect_request` returns `None`. Redirect responses therefore fail rather than silently requesting a second destination.
- Require a concrete fetch target in `ToolCaller`: an explicit URL, or a supported CoinGecko symbol paired with explicit price wording. Generic current/factual questions and unsupported price targets no longer select a fetcher that cannot satisfy them. Remove the unused beliefs-list parameter and the route's literal empty-list argument. This does not add general web search.
- Match CoinGecko symbols as whole words, avoiding substring false positives.
- Preserve the existing 10-second request timeout, 8 KiB read cap, HTML-tag stripping and 2,000-character result cap.
- Add tests for an allowlisted subdomain with an explicit port, the no-redirect handler, embedded credentials, unsupported schemes, generic query selection, explicit URL selection, unsupported price targets and whole-word coin matching.

## 3. Security and capability boundary

This closes the specific automatic-redirect bypass and the known selection/fetch-target mismatch. It does **not** establish a complete network sandbox:

- DNS resolution is not pinned or independently checked against private/reserved address ranges; DNS rebinding and a compromised/repurposed allowlisted domain remain outside this increment.
- The allowlisted page body remains untrusted external content. This change does not solve prompt injection or establish a trusted-content policy for model consumption.
- The capability remains an HTTP GET/read operation. This change does not add a general operation schema, approval authority, consequential action executor or post-execution verifier.
- No new domain, tool or external action was added.

## 4. Validation

The new unit tests assert the hostname/port acceptance path, reject credentials and non-HTTP schemes before opener construction, verify that the configured redirect handler refuses a 302 target, and characterize supported versus unsupported ToolCaller fetch targets, including the distinction between crypto-price and crypto-news queries. Exact-head full-suite CI and baseline verification are required before merge.

## 5. Follow-on questions

1. Decide whether NEX should pin resolved addresses and reject loopback, link-local, private, multicast and other non-global destinations, accounting for DNS rebinding and TOCTOU.
2. Define how untrusted fetched text is delimited and treated in the model prompt, with adversarial prompt-injection tests.
3. Before adding consequential tools, introduce an explicit typed operation representation and keep capability validation, approval authority, execution and post-execution verification as separate stages. Mind Aspects remain interpretive inputs and do not gate or authorize the operation.
