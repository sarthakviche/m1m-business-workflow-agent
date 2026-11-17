# Brief — Munim SaaS explainer

- **Request:** "Make an engaging SaaS explainer product demo video for Munim, 45 seconds. Use the brand colors."
- **Format:** 1920×1080, 30 fps, ~45 s. Language: English (product supports English/Hinglish input). Sound: not specified → music bed + light UI sounds proposed in stage 3.
- **Audience:** Owners and sales staff at Indian SMEs (traders, distributors, manufacturers) who make quotations and GST invoices by hand or in spreadsheets.
- **Core message:** Type a request in plain English/Hinglish → Munim produces a GST-correct quotation, converts it to a tax invoice, checks stock, and hands back a PDF.
- **CTA:** Pending — no public URL/sign-up found in the repo. Placeholder "Munim.ai" end card; ask the user for the CTA line/URL in stage 2.

## Brand (from code)

| Token | Value | Source |
| --- | --- | --- |
| Primary orange | `#f97316` (brand-500), `#ea580c` (brand-600) | `frontend/tailwind.config.js` |
| Accent orange | `#E8792A` / dark `#c8621d` | `m1m.orange` in tailwind config |
| Light washes | `#fff7ed`, `#ffedd5` | brand-50/100, `hero-gradient` |
| Gradient | `135deg #ea580c → #f97316 → #fb923c` | `brand-gradient` |
| Ink / UI neutrals | Tailwind slate (`#0f172a`, `#64748b`, `#f8fafc`) | app UI |
| Type | Plus Jakarta Sans (display), Inter (UI/body) | `index.css`, tailwind `fontFamily` |
| Logo | Orange "M" mark with dot | `whatsapp-demo/public/munim-logo.png` → `assets/brand/munim-logo.png`; app uses orange rounded tile "M" |

## Evidence

| Content / use | Source | Evidence type | Usable asset / state | Gap |
| --- | --- | --- | --- | --- |
| Chat → quotation from plain language | `README.md`, `FEATURE_INVENTORY_AND_ROADMAP.md`, Assistant page | Implemented feature (code + docs); UI observed | `assets/ui/assistant/page.png` (empty state with real prompt suggestions) | Live result state not captured (would write to local DB); card redrawn from `DocumentResultCard.tsx` |
| Quotation-to-invoice conversion, deterministic GST (CGST/SGST vs IGST) | README, `gst_calculator.py`, inventory doc | Implemented feature | Card redraw with real numbers | Capture live in stage 3 |
| Representative example | Seed data + app's own suggestion "Quotation for Ramesh Traders, 10 TMT Steel Rod 12mm" | Direct observation: Q-202611-001 · Ramesh Traders · ₹580.00 on dashboard | 10 kg × ₹58, HSN 7213, GST 18% → intra-state invoice CGST ₹52.20 + SGST ₹52.20 = ₹684.40 (computed) | — |
| Dashboard (sales, to collect, open quotations, recent docs) | Dashboard page | Direct observation (seed/test data) | `assets/ui/dashboard/page.png` | Figures are fictional test data — label as illustrative |
| Stock check / catalog lookup | README, Assistant suggestion "price and stock of MS Hex Bolt" | Implemented feature | Redraw in stage 3 | Live answer not captured |
| Telegram channel, customer web app | Latest commit `5f1d1c2` | Implemented per commit message | — | Not inspected; optional |

**Excluded (roadmap, not shown as working):** two-sided marketplace / AI buyers (value-prop graphic), WhatsApp payment reminders, dues collection, Tally/Zoho sync, e-invoicing/IRN, e-way bills.

All business names, GSTINs and amounts are seeded fictional test data (`backend/scripts/seed.py`).
