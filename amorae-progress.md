# amorae — progress & what's on our plates

Living status file. The single place to see everything in flight, done, and
blocked. Updated as work lands. (Historical diary lives in `DAILY-LOG.md`;
this file is the forward-looking "what's on our plates".)

Last updated: 2026-08-09

---

## ✅ Done & live on amorae.ai

- Public TikTok-style vertical video feed (no login, 18+ gated), curated mock feed
- Creator profile pages (Tara/Mira/Nyx) + subscribe/checkout shell
- Age gate (anonymous, cookie-only) split from auth; provider seam for real AV
- App owns its CSP (derived from CDN config); edge dropped its header
- CVE-2026-54283 mitigated (request-body cap); security scan green
- Deploy pipeline fixed (`DEPLOY_SSH_KEY` secret was missing) — CI deploys work
- Chat (SSE, OpenRouter, own DB) built & deployed, gated at 401

## 🔨 In progress

- **CCBill/Segpay approval-readiness** — BUILT (PR open). Full policy set,
  cookie consent, functional subscribe flow with rebill disclosure + consent,
  support page, 2257/AUP, entity = GoBazzinga Inc from config. Deliverable:
  `docs/ccbill-readiness-2026-08-09.md`. **Waiting on Rishi for 5 env values**
  (country [hard gate], address, support email, billing descriptor, legal
  sign-off) — see checklist below. Nothing else blocks it going live.

## ⏳ Blocked / waiting on others (none blocking the web build)

- **Video service** — `duration_seconds` + `like_count` coming (cheap); `caption`
  dropped. `influencer_id` resolved (= `publisher_user_id`). No field owed.
- **Live feed data frozen since 2026-07-16** — stay on `FEED_SOURCE=mock`; do
  NOT point real traffic at upstream until ingestion is fixed (other session).
- **Adult CDN** — feed on `cdn-yral-sfw` (SFW bucket); needs own designated CDN
  before any adult video ships. One env var our side; infra work theirs.
- **Issue #9** — FastAPI 0.115→0.141 to clear suppressed starlette CVEs. Not urgent.

## 🧭 Open questions / findings for Rishi

- **Tara's videos: FOUND — different record than we had.** The live Tara is
  the video-creator profile **`elitesuperdeer`** (Tara, 22, Toronto, "Powered
  by AI", 3k followers, full video library) — NOT the `qi6gd`/"taaarraaah"
  Mumbai chat bot we'd hard-coded. Persona metadata corrected (Toronto/22/bio).
  **BLOCKED on Rishi:** need elitesuperdeer's PRINCIPAL id (Share → link on her
  profile) to resolve her videos + real avatar. No public username→principal
  lookup exists, so this is the one thing I can't derive.
- **Web chat is unreachable without the app.** Clicking "Chat with Tara" on the
  web needs a valet ticket from the mobile app; a pure-web visitor can't start a
  chat (no web login/signup). Product decision needed: anonymous web chat, or a
  web account system? Matters for the funnel AND for a processor reviewing the
  end-to-end experience.
- **Mira & Nyx** — placeholder letter-tiles; Rishi creating them next.

---

## CCBill/Segpay approval checklist (A–D gating + 1–17)

Legend: ☐ todo · ◐ built, needs Rishi input · ✅ done

### Gating requirements (A–D)
- ◐ **A. Business jurisdiction** — CCBill onboards US/CA/UK/EU only. GoBazzinga
  Inc's registered country must appear in footer/ToS. **RISHI: confirm country
  is one of these — hard requirement.**
- ✅ **B. Functional sales process** — content → Subscribe → plan/pricing → checkout
  page (price, rebill terms, ToS/refund acceptance, labelled payment step).
- ✅ **C. AUP compliance** (audited — content clean of banned keywords) — review ccbill.com/doc AUP; flag any concerns.
- ✅ **D. Site LIVE + functional** — amorae.ai is live.

### Content & billing transparency
- ✅ 1. Clear brand + product description (AI-companion / adult subscriptions)
- ✅ 2. Full pricing disclosure before purchase + on join page
- ✅ 3. Billing-descriptor disclosure
- ✅ 4. Recurring-billing / auto-renew consent language

### Policies (footer on every page)
- ✅ 5. Terms   ✅ 6. Privacy (GDPR+CCPA)   ✅ 7. Cookie Policy + banner
- ✅ 8. Refund/Cancellation   ✅ 9. Chargeback/Dispute
- ✅ 10. DMCA/content-removal   ✅ 11. Content-report mechanism (exists: /report)

### Adult-specific
- ✅ 12. 18+ gate + persistent warning + AV provider slot
- ✅ 13. USC 2257 statement (AI-generated, no real individuals; GoBazzinga Inc custodian)
- ✅ 14. Prohibited-content statement (fictional adults 18+, zero-tolerance CSAM)

### Support & trust
- ✅ 15. Support/Contact (email + form + response time + CCBill billing-support link)
- ✅ 16. Clear "how to cancel" instructions
- ◐ 17. Footer entity+address (renders once fields set) — GoBazzinga Inc + address + contact in footer

### Fields Rishi must fill (blanks in code, flagged DRAFT-FOR-LEGAL)
- [ ] GoBazzinga Inc registered **country** (must be US/CA/UK/EU) + full address
- [ ] Support email (+ optional phone)
- [ ] Final pricing per tier (currently placeholder $12.99–14.99/mo)
- [ ] Billing descriptor (what shows on the card statement)
- [ ] Legal review + sign-off on all DRAFT policy copy
