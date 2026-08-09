"""Policy content for the CCBill/Segpay merchant review.

DRAFT boilerplate — adult-appropriate, entity = GoBazzinga Inc — written to be
reviewed by counsel, not shipped as final legal advice. `LEGAL_COPY_APPROVED`
gates the visible "pending legal review" banner.

Data-driven on purpose: one file a lawyer can read end to end, one template
that renders any policy, one route. Adding or editing a policy is a dict edit,
not a new template (repo rule 1: symmetry).

A block is a tuple:
    ("h2", "Heading")
    ("p",  "Paragraph. {entity} etc. are filled from config.")
    ("ul", ["item", "item"])
    ("note", "Rendered as a highlighted callout.")

`{placeholders}` are filled from config at render time. A REQUIRED value that
is still blank renders as a visible «TO BE COMPLETED — …» marker, so a missing
address is obvious to both the reviewer and to Rishi rather than silently empty.
"""

import config

UPDATED = "2026-08-09"


def _fields() -> dict:
    """Config values for interpolation, with visible markers for blanks that
    must be filled before the application goes in."""

    def required(value: str, label: str) -> str:
        return value or f"«TO BE COMPLETED — {label}»"

    return {
        "entity": config.LEGAL_ENTITY,
        "brand": config.BRAND_NAME,
        "domain": config.BRAND_DOMAIN,
        "country": required(
            config.LEGAL_ENTITY_COUNTRY, "registered country (US/CA/UK/EU)"
        ),
        "address": required(config.LEGAL_ENTITY_ADDRESS, "registered business address"),
        "support_email": required(config.SUPPORT_EMAIL, "support email"),
        "descriptor": config.BILLING_DESCRIPTOR,
        "ccbill_support": config.CCBILL_SUPPORT_URL,
        "custodian": config.RECORDS_CUSTODIAN,
    }


# ---------------------------------------------------------------------------
# Policies
# ---------------------------------------------------------------------------

POLICIES: dict[str, dict] = {
    "terms": {
        "title": "Terms of Service",
        "summary": "The agreement between you and {entity} for using {brand}.",
        "blocks": [
            (
                "p",
                "Welcome to {brand} ({domain}), operated by {entity}, a company "
                "registered in {country}. By accessing or using {brand} you agree "
                "to these Terms of Service. If you do not agree, do not use the site.",
            ),
            ("h2", "1. Eligibility — adults only"),
            (
                "p",
                "{brand} is an adult website. You must be at least 18 years old, or "
                "the age of majority in your jurisdiction, whichever is greater. By "
                "using the site you represent and warrant that you meet this "
                "requirement and that adult content is legal where you live.",
            ),
            ("h2", "2. Nature of the service"),
            (
                "p",
                "{brand} offers AI-generated adult companionship — chat and media "
                "featuring fictional AI personas. Every persona is artificially "
                "generated. No real individuals are depicted, and all personas are "
                "portrayed as fictional adults aged 18 or over.",
            ),
            ("h2", "3. Accounts and subscriptions"),
            (
                "p",
                "Some features require a paid subscription. Pricing, billing "
                "interval and renewal terms are disclosed before you purchase and "
                "on the checkout page. Subscriptions renew automatically until "
                "cancelled — see the Refund & Cancellation Policy.",
            ),
            ("h2", "4. Payments"),
            (
                "p",
                "Payments are processed by our third-party payment processor. Your "
                "card statement will show the descriptor «{descriptor}». {entity} "
                "does not store your full card details.",
            ),
            ("h2", "5. Acceptable use"),
            (
                "p",
                "You agree not to misuse the service. Prohibited conduct is set out "
                "in the Acceptable Use & Prohibited Content Policy, which forms part "
                "of these Terms. We may suspend or terminate access for violations.",
            ),
            ("h2", "6. Intellectual property"),
            (
                "p",
                "All content on {brand} is owned by {entity} or its licensors. You "
                "receive a personal, non-transferable, non-commercial licence to "
                "view content while your subscription is active. You may not "
                "redistribute, resell or publicly display it.",
            ),
            ("h2", "7. Disclaimers and liability"),
            (
                "p",
                'The service is provided "as is". To the fullest extent permitted '
                "by law, {entity} disclaims all warranties and limits its liability "
                "for any indirect or consequential loss.",
            ),
            ("h2", "8. Changes and contact"),
            (
                "p",
                "We may update these Terms; material changes will be posted here. "
                "Questions: {support_email}.",
            ),
            (
                "note",
                "DRAFT for legal review. {entity} to confirm governing law and "
                "jurisdiction (registered in {country}).",
            ),
        ],
    },
    "privacy": {
        "title": "Privacy Policy",
        "summary": "How {entity} collects, uses and protects your data (GDPR + CCPA).",
        "blocks": [
            (
                "p",
                "This Privacy Policy explains how {entity} ({domain}) handles "
                "personal data. We are the data controller. It is written to meet "
                "the EU/UK GDPR and the California Consumer Privacy Act (CCPA).",
            ),
            ("h2", "1. Data we collect"),
            (
                "ul",
                [
                    "Account data: email and login identifiers.",
                    "Age-assurance signal: a record that you confirmed you are 18+.",
                    "Transaction data: subscription plan and billing status (card "
                    "details are held by our payment processor, not by us).",
                    "Usage data: pages viewed, device and approximate region, cookies.",
                ],
            ),
            ("h2", "2. How we use it"),
            (
                "ul",
                [
                    "To provide the service and your subscription.",
                    "To verify age and eligibility.",
                    "To process payments and prevent fraud and chargebacks.",
                    "To comply with legal obligations and respond to support requests.",
                ],
            ),
            ("h2", "3. Legal bases (GDPR)"),
            (
                "p",
                "We rely on contract (to provide the service), legal obligation "
                "(age and tax rules), and legitimate interest (security and fraud "
                "prevention). You may withdraw consent for non-essential cookies at "
                "any time via the cookie banner.",
            ),
            ("h2", "4. Your rights"),
            (
                "p",
                "Under GDPR you may access, correct, delete, restrict or port your "
                "data, and object to processing. Under CCPA you may know, delete, "
                'and opt out of "sale" of personal information — we do not sell '
                "personal information. Exercise any right via {support_email}.",
            ),
            ("h2", "5. Sharing"),
            (
                "p",
                "We share data only with processors that run the service (payment "
                "processing, hosting, age verification) under contract, and where "
                "required by law. We never sell your data.",
            ),
            ("h2", "6. Retention and security"),
            (
                "p",
                "We keep data only as long as needed for the service and legal "
                "requirements, then delete or anonymise it. We use encryption in "
                "transit and access controls.",
            ),
            ("h2", "7. Contact"),
            (
                "p",
                "Data controller: {entity}, {address}. Privacy requests: "
                "{support_email}.",
            ),
            (
                "note",
                "DRAFT for legal review. Confirm DPO/representative and any "
                "region-specific addenda (e.g. Quebec Law 25).",
            ),
        ],
    },
    "cookies": {
        "title": "Cookie Policy",
        "summary": "What cookies {brand} uses and how to control them.",
        "blocks": [
            (
                "p",
                "{brand} uses a small number of cookies. This policy explains which "
                "and why, and how you can control them via the cookie banner.",
            ),
            ("h2", "Strictly necessary (always on)"),
            (
                "ul",
                [
                    "Age-assurance cookie — remembers that you confirmed you are 18+.",
                    "Session cookie — keeps you signed in to your account.",
                    "Feed key — a random, non-identifying token so your feed is stable.",
                    "Cookie-consent choice — remembers your banner selection.",
                ],
            ),
            ("h2", "Analytics (optional, off until you accept)"),
            (
                "p",
                "If you accept, we may use privacy-respecting analytics to "
                "understand usage. These are disabled until you opt in and can be "
                "withdrawn any time by reopening the cookie banner.",
            ),
            ("h2", "Managing cookies"),
            (
                "p",
                "Use the cookie banner to accept or decline non-essential cookies. "
                "You can also block cookies in your browser, though the site may not "
                "function correctly without the strictly-necessary ones.",
            ),
            ("note", "DRAFT for legal review."),
        ],
    },
    "refunds": {
        "title": "Refund & Cancellation Policy",
        "summary": "How to cancel, and when refunds apply. Cancel any time.",
        "blocks": [
            (
                "note",
                "You can cancel at any time. Cancelling stops the next renewal; "
                "you keep access until the end of the paid period.",
            ),
            ("h2", "1. How to cancel"),
            (
                "ul",
                [
                    "From your account: open Billing and choose Cancel Subscription.",
                    "By email: contact {support_email} and we will cancel for you.",
                    "Via the payment processor: manage or cancel any subscription "
                    "through the processor's consumer support portal ({ccbill_support}).",
                ],
            ),
            (
                "p",
                "Cancellation takes effect at the end of the current billing "
                "period. You will not be charged again after you cancel.",
            ),
            ("h2", "2. Refunds"),
            (
                "p",
                "If you were charged in error, charged after cancelling, or could "
                "not access what you paid for, contact {support_email} within 30 "
                "days and we will review and, where appropriate, refund you. "
                "Because access is granted immediately, we do not generally refund "
                "for a period already used, except as required by law or the "
                "processor's rules.",
            ),
            ("h2", "3. Free trials and promotions"),
            (
                "p",
                "If a plan includes a trial, the renewal price and date are shown "
                "before you subscribe. Cancel before the trial ends to avoid the "
                "charge.",
            ),
            ("h2", "4. Contact"),
            (
                "p",
                "Billing questions: {support_email}, or the processor's billing "
                "support at {ccbill_support}.",
            ),
            (
                "note",
                "DRAFT for legal review — confirm the refund window and any "
                "processor-mandated terms.",
            ),
        ],
    },
    "chargebacks": {
        "title": "Chargeback & Dispute Policy",
        "summary": "Talk to us first — most disputes are resolved in minutes.",
        "blocks": [
            (
                "p",
                "If you do not recognise a charge or believe it is wrong, please "
                "contact us before filing a chargeback with your bank. Most issues "
                "— an unexpected renewal, a descriptor you didn't recognise — are "
                "resolved quickly and, where appropriate, refunded.",
            ),
            ("h2", "The statement descriptor"),
            (
                "p",
                "Charges from {brand} appear on your statement as «{descriptor}». "
                "Recognising this often clears up a disputed charge immediately.",
            ),
            ("h2", "How to raise a dispute"),
            (
                "ul",
                [
                    "Email {support_email} with the date and amount.",
                    "Or contact the payment processor's billing support: {ccbill_support}.",
                ],
            ),
            ("h2", "Fraudulent charges"),
            (
                "p",
                "If you believe your card was used without authorisation, contact "
                "us and your bank immediately. We cooperate fully with genuine "
                "fraud investigations.",
            ),
            ("note", "DRAFT for legal review."),
        ],
    },
    "dmca": {
        "title": "DMCA & Content Removal",
        "summary": "How to report content for removal, including non-consensual imagery.",
        "blocks": [
            (
                "p",
                "{entity} respects intellectual property and personal rights. "
                "{brand}'s content is AI-generated and does not depict real people, "
                "but if you believe material on the site infringes your copyright or "
                "otherwise should be removed, tell us and we will act promptly.",
            ),
            ("h2", "Copyright (DMCA) notices"),
            (
                "p",
                "Send a notice to {support_email} including: identification of the "
                "work, the URL of the material, your contact details, a good-faith "
                "statement, a statement under penalty of perjury that you are "
                "authorised, and your signature.",
            ),
            ("h2", "Non-consensual or personal-rights removal"),
            (
                "p",
                "We remove reported non-consensual imagery within 48 hours of a "
                "valid report and operate a repeat-infringer policy. Use the same "
                "address or the on-site report form.",
            ),
            ("h2", "Counter-notice and repeat infringers"),
            (
                "p",
                "We will forward valid counter-notices and terminate access for "
                "repeat infringers.",
            ),
            ("note", "DRAFT for legal review — name the registered DMCA agent."),
        ],
    },
    "2257": {
        "title": "18 U.S.C. § 2257 Statement",
        "summary": "All content is AI-generated. No real performers appear on {brand}.",
        "blocks": [
            (
                "p",
                "All visual and textual content on {brand} is wholly "
                "computer-generated. It is created by artificial-intelligence "
                "systems and does not depict any real human being.",
            ),
            ("h2", "No real performers"),
            (
                "p",
                "Because no actual human beings are depicted in any content on "
                "{brand}, the record-keeping requirements of 18 U.S.C. § 2257 and "
                "28 C.F.R. Part 75 do not apply: there are no performers, and no "
                "sexually explicit conduct by real persons, for which records could "
                "exist. Every persona is fictional and is portrayed as an adult "
                "aged 18 or older.",
            ),
            ("h2", "Records custodian"),
            (
                "p",
                "For any inquiry regarding content and age representations, the "
                "designated custodian of records is {custodian}, {address}.",
            ),
            (
                "note",
                "DRAFT for legal review. Stating AI-only + no-real-performers is "
                "favourable, but counsel should confirm the exact wording and "
                "custodian designation before filing.",
            ),
        ],
    },
    "aup": {
        "title": "Acceptable Use & Prohibited Content",
        "summary": "Fictional adults only. Zero tolerance for illegal content.",
        "blocks": [
            (
                "note",
                "All content on {brand} is AI-generated and depicts only "
                "fictional adults aged 18 or over. We have ZERO tolerance for "
                "child sexual abuse material (CSAM) or any depiction of minors.",
            ),
            ("h2", "All personas are fictional adults"),
            (
                "p",
                "Every persona on {brand} is artificially generated and portrayed "
                "as a fictional adult aged 18 or older. No real person is depicted. "
                "Content is generated with controls that block minor-presenting "
                "output in both images and text.",
            ),
            ("h2", "Strictly prohibited"),
            (
                "ul",
                [
                    "Any content that sexualises minors, or depicts anyone under 18 "
                    "(real or fictional) — zero tolerance, reported to authorities.",
                    "Non-consensual content, or content depicting real, identifiable "
                    "people without authorisation.",
                    "Bestiality, incest, rape or content promoting violence or harm.",
                    "Any content illegal in the jurisdictions where we operate.",
                ],
            ),
            ("h2", "Reporting"),
            (
                "p",
                "Report anything that violates this policy via the report form or "
                "{support_email}. We review reports promptly and cooperate with law "
                "enforcement.",
            ),
            ("h2", "User conduct"),
            (
                "p",
                "You may not attempt to generate, solicit or share prohibited "
                "content, scrape the service, or resell access. Violations result "
                "in immediate termination.",
            ),
            (
                "note",
                "DRAFT for legal review. Aligned with CCBill's Acceptable Use "
                "Policy — confirm against the current ccbill.com/doc version.",
            ),
        ],
    },
}


def get(slug: str) -> dict | None:
    policy = POLICIES.get(slug)
    if not policy:
        return None
    fields = _fields()
    rendered_blocks = []
    for kind, value in policy["blocks"]:
        if kind == "ul":
            rendered_blocks.append((kind, [item.format(**fields) for item in value]))
        else:
            rendered_blocks.append((kind, value.format(**fields)))
    return {
        "slug": slug,
        "title": policy["title"],
        "summary": policy["summary"].format(**fields),
        "blocks": rendered_blocks,
        "updated": UPDATED,
        "approved": config.LEGAL_COPY_APPROVED,
    }


# Footer/nav order — grouped the way a reviewer scans them.
POLICY_ORDER = [
    "terms",
    "privacy",
    "cookies",
    "refunds",
    "chargebacks",
    "dmca",
    "2257",
    "aup",
]


def nav() -> list[dict]:
    return [{"slug": s, "title": POLICIES[s]["title"]} for s in POLICY_ORDER]
