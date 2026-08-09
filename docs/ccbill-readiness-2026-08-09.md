# CCBill/Segpay merchant-review readiness — amorae.ai

**Date:** 2026-08-09
**Goal:** amorae.ai passes an adult payment processor's merchant review so the
approval long-pole can start.
**Entity:** GoBazzinga Inc (named everywhere; driven from config, not hard-coded).

---

## TL;DR for Rishi

The compliance surface is **built and live-able**. Before the application goes
in, set **5 real values** (below) and get the DRAFT legal copy reviewed. Two
items need your confirmation — the business **country** (hard CCBill gate) and
the **billing descriptor**.

---

## 1. EXACT fields you must fill

These are env vars (Swarm secret or compose env). Until set, policy pages show a
visible `«TO BE COMPLETED — …»` marker so nothing ships silently blank.

| Env var | What | Notes |
|---|---|---|
| `LEGAL_ENTITY_COUNTRY` | GoBazzinga Inc's registered country | **HARD GATE — must be US / CA / UK / EU.** Confirm this first. |
| `LEGAL_ENTITY_ADDRESS` | Full registered business address | Shown in footer, 2257, Privacy. |
| `SUPPORT_EMAIL` | A monitored support inbox | e.g. support@amorae.ai — must actually be answered. |
| `BILLING_DESCRIPTOR` | What appears on the card statement | Default `AMORAE.AI`. CCBill assigns/approves the final string — confirm. |
| `LEGAL_COPY_APPROVED` | `true` once counsel signs off the DRAFT copy | Hides the "DRAFT — pending legal review" badge. |

Already sensible defaults (override only if needed): `LEGAL_ENTITY`
(GoBazzinga Inc), `CCBILL_SUPPORT_URL`, `RECORDS_CUSTODIAN`.

**Also confirm (not a code field):** final per-tier pricing. Placeholder is
$14.99/mo (monthly), $12.74/mo (3-mo), $10.49/mo (annual) — set in
`routes/creator.py::TIERS`.

---

## 2. Gating requirements A–D

| | Requirement | Status |
|---|---|---|
| A | Business in US/CA/UK/EU, country stated on site | ◐ **built — RISHI confirm country** (renders from `LEGAL_ENTITY_COUNTRY`) |
| B | Full functional sales process, reviewable end-to-end | ✅ content → Subscribe → plan → billing terms → labelled payment step → consent |
| C | Complies with CCBill Acceptable Use Policy | ✅ AUP page + content audited (see §4) |
| D | Site live + functional for review | ✅ amorae.ai is live |

---

## 3. Items 1–17

**Content & billing transparency**
- ✅ 1. Brand + product description (AI-companion / adult subscriptions) — in ToS, AUP, checkout
- ✅ 2. Full pricing disclosure before purchase — plan cards + live "Billing terms" panel
- ✅ 3. Billing-descriptor disclosure — checkout, chargeback policy, support (`{descriptor}`)
- ✅ 4. Recurring-billing / auto-renew consent — required checkbox + explicit language

**Policies (footer on every page)**
- ✅ 5. Terms of Service — `/legal/terms`
- ✅ 6. Privacy Policy (GDPR + CCPA) — `/legal/privacy`
- ✅ 7. Cookie Policy + consent banner — `/legal/cookies` + banner (analytics off until accept)
- ✅ 8. Refund / Cancellation — `/legal/refunds` (clear cancel steps, weighted most)
- ✅ 9. Chargeback / Dispute — `/legal/chargebacks`
- ✅ 10. DMCA / Content Removal — `/legal/dmca` (48h non-consensual removal)
- ✅ 11. Content-report mechanism — `/report`

**Adult-specific**
- ✅ 12. 18+ gate on entry + persistent warning + AV-provider seam (`AGE_ASSURANCE_MODE`)
- ✅ 13. USC 2257 — AI-generated, NO real individuals; GoBazzinga Inc custodian — `/legal/2257`
- ✅ 14. Prohibited-content statement — fictional adults 18+, zero-tolerance CSAM — `/legal/aup`

**Support & trust**
- ✅ 15. Support/Contact — `/support` (email + form + 2-day response + CCBill billing portal link)
- ✅ 16. Clear "how to cancel" — refund policy + support page + checkout link
- ◐ 17. Entity + address + contact in footer — **renders once §1 fields are set**

Legend: ✅ done · ◐ built, needs Rishi input

---

## 4. AUP concerns flagged (item C)

Reviewed against how CCBill/Segpay assess adult merchants. Nothing blocking;
these are the things to be aware of.

1. **Banned-keyword risk — currently CLEAN.** Processors auto-flag "teen",
   "young", "underage", "incest", "step-sis/bro", "barely legal", etc. Audited
   persona bios, captions and UI copy: none present. Personas are stated as
   24/26, unambiguously adult. **Keep this discipline in future persona and
   caption content** — it's the fastest way to trip a review.
2. **Age assurance is self-attestation, not verified AV.** The 18+ gate is a
   confirm-your-age interstitial (what most of the world allows), with a
   `AGE_ASSURANCE_MODE=provider` seam ready for a real verifier. Some reviewers
   in some regions want verified AV; if asked, we flip the seam to a provider
   (Persona/Yoti/VerifyMy). Not a blocker for the CCBill application itself, but
   know the answer.
3. **No NSFW before the gate — satisfied.** No adult media or feed markup is
   sent to a browser that hasn't passed the gate (there's a test asserting zero
   media URLs leak). This is a specific thing reviewers check.
4. **AI-only is favourable, state it loudly — done.** The 2257 and AUP pages
   lead with "all content AI-generated, no real performers." For an AI site
   this is an advantage over human-performer sites (no 2257 records burden);
   we're not hiding it.
5. **Card data never touches our server.** The checkout's payment step is a
   labelled mount for the processor's hosted form, with copy stating we never
   see or store card numbers. Do not let anyone add a real card field to our
   page — it's prohibited and would fail PCI/underwriting.

**Confirm before filing** (legal's track, not code): 2257 custodian wording,
DMCA registered-agent name, governing-law clause, and any region addenda
(Quebec Law 25, etc.). All DRAFT copy is marked as such until
`LEGAL_COPY_APPROVED=true`.

---

## 5. How to go live for review

```
# In the Swarm compose env / secrets for amorae_web:
LEGAL_ENTITY_COUNTRY="United States"        # or CA/UK/EU — HARD GATE
LEGAL_ENTITY_ADDRESS="<registered address>"
SUPPORT_EMAIL="support@amorae.ai"
BILLING_DESCRIPTOR="AMORAE.AI"              # confirm with CCBill
LEGAL_COPY_APPROVED=false                    # flip true after legal sign-off
```

Everything else is already deployed. Setting these + a redeploy renders the
footer/policies complete. The site is then a live, functional, professional URL
with an end-to-end reviewable subscribe flow — which is what starts the CCBill /
Segpay underwriting clock.

**What the processor's account exec does after approval:** wires their hosted
payment form into the labelled payment step (`payment-mount` in
`subscribe.html`). No rebuild — it's a drop-in.
