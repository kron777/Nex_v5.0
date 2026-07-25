"""Feed 11 — PhilPapers philosophy of mind RSS. Poll interval: 7200s.

REMOVED FROM build_scheduler() 2026-07-25: philpapers.org returns a
genuine Cloudflare "Attention Required" JS-challenge page (not a UA
check) -- confirmed by inspecting the response body directly, which
loads a Cloudflare challenge script (`__CF$cv$params`,
`/cdn-cgi/challenge-platform/scripts/jsd/main.js`) requiring JavaScript
execution to pass. No HTTP header (UA, Referer, cookie) resolves this
from a plain HTTP client. This box's outbound IP (whois: "Datacamp
Limited" / CDN77, a hosting/CDN ASN, not residential) is exactly the
class of address Cloudflare bot-mitigation commonly blocks by default,
which is the likely trigger. Unfixable from here short of a headless
browser or a residential-IP proxy. Class kept for its structure/tests
and in case philpapers.org's Cloudflare config changes. Do not re-add
to build_scheduler() without confirming a plain GET no longer returns
a Cloudflare challenge page.
"""
from __future__ import annotations

from typing import Optional

from substrate import Writer
from theory_x.stage1_sense.base import Adapter, RequestFn, SenseEvent
from ._helpers import parse_rss

THEORY_X_STAGE = 1

_URL = "https://philpapers.org/rss/min_areas.pl?area=phi"


class PhilPapers(Adapter):
    id = "philpapers"
    stream = "cognition.philpapers"
    poll_interval_seconds = 7200
    provenance = _URL

    def __init__(self, writer: Writer, *, request_fn: Optional[RequestFn] = None) -> None:
        super().__init__(writer, request_fn=request_fn)

    def poll(self) -> list[SenseEvent]:
        raw = self._fetch(_URL)
        return parse_rss(raw, self.stream, self.provenance)
