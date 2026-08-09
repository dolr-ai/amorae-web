# amorae-web — daily log

Append-only. Newest entry on top. What shipped, what's live, what's pending.

---

## 2026-08-09 — public video feed, creator surface, CSP ownership, security baseline

Shipped the discovery funnel and, in the process, found and fixed a broken
deploy pipeline and a reachable security bug.

### Merged & deployed to amorae.ai
- **#6** — public TikTok-style vertical video feed (works with no login),
  creator profile pages, subscribe/checkout shell. Age assurance split from
  authentication: the feed is browsable behind an anonymous 18+ gate;
  login is required only to interact. Video is consumed from the SAME
  `recommend-with-metadata` endpoint mobile uses, server-side. Also pinned
  `ruff==0.15.21` — unpinned ruff 0.16 had been silently failing main's CI.
- **#7** — CSP is now set by the app (`config.CONTENT_SECURITY_POLICY` +
  middleware), derived from `MEDIA_CDN_BASE`, so it follows the code and the
  CDN config instead of needing a Caddy edge round-trip. Byte-identical to
  the edge policy it replaces. Session 6 then dropped the edge CSP header —
  verified live: exactly one CSP header (the app's, complete), and the edge
  keeps `X-Frame-Options: DENY` so clickjacking protection does not depend on
  the app. amorae is now self-sufficient on CSP.
- **#8** — mitigated CVE-2026-54283 (starlette urlencoded form-limit DoS,
  reachable on the unauthenticated age gate) with a 256 KB request-body cap
  (`LimitRequestBody` ASGI middleware). Suppressed the two non-applicable
  starlette HIGHs with per-CVE justifications, corrected a stale one, and
  brought `.trivyignore` in line with `pip-audit-ignore.txt`.

### Infrastructure fixed
- **Deploy pipeline** had never succeeded — the `DEPLOY_SSH_KEY` repo secret
  did not exist, so every run failed `Permission denied (publickey)`. Created
  it from the existing `rishi-hetzner-ci-key` (already trusted on rishi-4/5/6;
  no rotation needed). First successful CI deploy followed.
- **Security workflow** went green for the first time — it had been "failing"
  on a missing `:stable` image (never published because deploy never ran),
  not on findings.

### Verified live on amorae.ai
Feed renders, posters + video load (no CSP violations), age gate leaks no
media to an ungated visitor, oversized-body DoS returns 413, subscribe flow
reaches the intent page.

### Pending / waiting on others
- **Video service** — needs `influencer_id` on each feed video, or every
  overlay renders a generic creator (funnel broken). Contract:
  `docs/video-feed-web-contract-2026-08-09.md`.
- **Adult CDN** — feed currently served from `cdn-yral-sfw` (SFW bucket).
  Needs its own designated CDN before any adult video ships. One env var our
  side (`MEDIA_CDN_BASE`); infra work theirs.
- **Session 6** — may drop the edge CSP header now the app owns it (optional).
- **Issue #9** — FastAPI 0.115 → 0.141 to clear the suppressed starlette CVEs
  properly. Not urgent (reachable risk is mitigated).
- **Persona video content** — the feed shows real YRAL AI-influencer clips,
  not Tara/Mira/Nyx. Real persona video is a content-production task.
- **Payments** — CCBill/Segpay underwriting; subscribe is a stub until a
  processor clears.
