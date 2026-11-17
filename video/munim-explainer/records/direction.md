# Direction v1

Same content in all three: the app's own example prompt "Quotation for Ramesh Traders, 10 TMT Steel Rod 12mm" → quotation card Q-202611-001 (10 kg × ₹58.00, HSN 7213, ₹580.00, Download PDF), headline "Type the order. Munim does the paperwork.", Munim orange/white palette, Plus Jakarta Sans + Inter.

| Candidate | Image | Distinct design choices |
| --- | --- | --- |
| A Warm Studio | `assets/directions/a.png` | Warm white → peach gradient (the app's `hero-gradient`), real Assistant screen as a floating window, frosted composer and soft-shadow result card layered over it. Calm, premium, product-led. |
| B Ledger Swiss | `assets/directions/b.png` | Flat paper-and-ink grid, oversized type, one full-height orange signal block; no shadows or gradients; numbers become typography (₹580). Bold, editorial, kinetic-type film. |
| C Night Shift | `assets/directions/c.png` | Warm near-black stage lit by an orange glow; chat bubble and a lit, slightly tilted card in close-up. Cinematic, dramatic. |

**Recommendation: A.** It carries real interface evidence on screen, matches the white-and-orange look the app already ships (so the film and product feel the same), and gives the most room to enlarge each UI step (prompt → quotation → GST invoice → PDF) per E04. B is the most distinctive and would suit a punchy social cut, but shows less of the product. C is striking, but a dark stage moves away from the orange-on-white brand.

**Tradeoffs / asset feasibility**
- All three: the live result card must be recaptured in stage 3 (sending a chat writes to the local `m1m.db`; not done without permission). Current card is a faithful redraw of `DocumentResultCard.tsx`.
- A: relies on real screenshots — already captured at 2× (`assets/ui/`).
- B: mostly type and redrawn UI; lowest asset risk, highest motion-design effort.
- C: glow/blur scenes are heavier to render; text contrast on dark needs care.

Current selection: A (agent-selected under delegation; see Decision)
Confirmation basis: explicit delegation, quoted below.

## Decision

Agent selected **A · Warm Studio**; basis: the user said "Use the logo of Munim not the random M in orange logo. Smooth ui animations give me final finished film" — read as explicit delegation to decide the direction and script and finish the film, including export. Applicable version: direction v1.

Change from v1 frames: the orange "M" tile is replaced everywhere by the real Munim mark (`assets/brand/munim-mark.png`, cut from `whatsapp-demo/public/munim-logo.png` with `tools/logo-alpha.mjs`; shapes and colours unchanged).
