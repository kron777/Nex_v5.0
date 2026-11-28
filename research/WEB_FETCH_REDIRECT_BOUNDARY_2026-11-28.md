# Web-fetch URL and redirect boundary — 28 November 2026

**Base:** `kron777/Nex_v5.0` main at `3d7205536588e34a887939784d436ec70e8c6777` (after #378 request-drain merge).  
**Scope:** bounded hardening of the existing read-only `web_fetch` capability. No feature flag, capability list, prompt policy, runtime deployment or governing document changed.

## 1. Source finding

`theory_x/stage_capability/tools.py` checked the initial URL against `_ALLOWED_DOMAINS`, then called `urllib.request.urlopen()`. Python's default redirect handler follows HTTP redirects automatically. The allowlist was therefore applied to the initial host, not to the final network destination. An allowlisted origin able to redirect could cause the tool to request a destination that had not passed the allowlist.

The original host parsing also used `parsed.netloc.lstrip("www.")`. `lstrip` removes any leading characters from a character set, not one exact prefix; `netloc` also includes optional user-info and port. This could reject legitimate allowlisted hostnames with ports and did not explicitly reject embedded URL credentials or non-HTTP schemes.

The existing tests covered an unknown initial domain, but did not characterize redirect handling, explicit ports, credentials or scheme validation.

## 2. Bounded correction

- Parse with `urlsplit` and validate the scheme as `http` or `https`.
- Reject URLs containing username/password components.
- Compare the normalized `hostname` (lowercase, trailing dot removed) against the existing exact/subdomain allowlist; the port no longer contaminates hostname matching.
- Supply a custom `HTTPRedirectHandler` whose `redirect_request` returns `None`. Redirect responses therefore fail rather than silently requesting a second destination.
- Preserve the existing 10-second request timeout, 8 KiB read cap, HTML-tag stripping and 2,000-character result cap.
- Add tests for an allowlisted subdomain with an explicit port, the no-redirect handler, embedded credentials and unsupported schemes.

## 3. Security and capability boundary

This closes the specific automatic-redirect bypass. It does **not** establish a complete network sandbox:

- DNS resolution is not pinned or independently checked against private/reserved address ranges; DNS rebinding and a compromised/repurposed allowlisted domain remain outside this increment.
- The allowlisted page body remains untrusted external content. This change does not solve prompt injection or establish a trusted-content policy for model consumption.
- The capability remains an HTTP GET/read operation. This change does not add a general operation schema, approval authority, consequential action executor or post-execution verifier.
- No new domain, tool or external action was added.

## 4. Validation

The new unit tests assert the hostname/port acceptance path, reject credentials and non-HTTP schemes before opener construction, and verify that the configured redirect handler refuses a 302 target. Exact-head full-suite CI and baseline verification are required before merge.

## 5. Follow-on questions

1. Decide whether NEX should pin resolved addresses and reject loopback, link-local, private, multicast and other non-global destinations, accounting for DNS rebinding and TOCTOU.
2. Define how untrusted fetched text is delimited and treated in the model prompt, with adversarial prompt-injection tests.
3. Before adding consequential tools, introduce an explicit typed operation representation and keep capability validation, approval authority, execution and post-execution verification as separate stages. Mind Aspects remain interpretive inputs and do not gate or authorize the operation.
