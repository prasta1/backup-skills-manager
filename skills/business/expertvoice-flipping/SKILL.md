---
name: expertvoice-flipping
description: Buy pro-deal gear and resell it across marketplaces.
version: 0.1.0
author: Hermes
metadata:
  hermes:
    tags: [Resale, Arbitrage, Marketplace, Pricing, Compliance]
---

# ExpertVoice → Marketplace Flipping

Turns industry pro-deal inventory into cash on eBay, Facebook Marketplace, and
Nextdoor: verify the deal is legal to resell, pull real sold comps, run the
landed cost through fee math, then route each item to the channel that keeps the
most money. It does **not** scrape marketplaces, log in to ExpertVoice, or post
listings on your behalf — you drive the browser and the account, the skill does
the qualification, pricing, and copy. Stdlib Python only, no API keys.

**The first rule is a compliance gate, not a pricing rule.** ExpertVoice's honor
code and individual brand rules restrict who the gear is for, and Nextdoor
prohibits reseller listings outright. Read the brand's own rules page before you
buy anything, and read `references/compliance-and-risk.md` before you list.

## When to Use

- "Is this ExpertVoice deal worth flipping?"
- "What should I list this for?" / "check comps on eBay"
- "What's my margin after fees?" / "what do I net on a $260 sale?"
- "Write the Facebook Marketplace listing for this."
- "Can I sell this on Nextdoor?"
- "Which platform should this go on?"

## Prerequisites

- **ExpertVoice membership** with brand access. The binding document is the
  brand's own rules/guidelines page inside ExpertVoice, not the generic honor
  code. Screenshot it when you buy — rules change per brand and per drop.
- **eBay seller account** with payouts configured. Sold-comps research lives in
  Seller Hub → Research (Terapeak), free with a seller account.
- **Facebook Marketplace**: local listings need nothing; shipped listings need
  bank + tax info set up before the first sale.
- **Nextdoor**: account tied to your real address. Note the reseller ban below.
- `python3` (3.8+) for `scripts/margin.py` — stdlib only, no install.
- A deal log CSV you keep yourself, e.g. `~/Dropbox/<project>/flip-inventory.csv`.
  Track: SKU, brand, date bought, cost, channel, list price, sold price, net, days-to-sell.

## How to Run

Invoke the calculator through the `terminal` tool. The skill lives at
`~/.hermes/skills/business/expertvoice-flipping/`, so run the script by full path
(or `cd` there first) — relative paths in the examples below assume that dir:

```
python3 ~/.hermes/skills/business/expertvoice-flipping/scripts/margin.py \
  --cost 120 --price 260 --platform ebay --category most --ship-label 18
```

Pipeline, in order:

1. `read_file` the brand rules / honor-code excerpt you saved, and gate on it.
2. `web_extract` the product page + the eBay sold-comps URL for the model number.
3. `terminal` → `scripts/margin.py` for each candidate price.
4. `write_file` the listing draft; you paste it into the platform yourself.

## Quick Reference

```
# eBay, most categories, $260 sale, $18 label, free shipping to buyer
python3 scripts/margin.py --cost 120 --price 260 --platform ebay --ship-label 18

# eBay with buyer-paid shipping and a 4% promoted-listings ad rate
python3 scripts/margin.py --cost 300 --price 480 --platform ebay \
  --category electronics --ship-collected 25 --ship-label 22 --promoted 4

# Facebook Marketplace, local pickup (no selling fee)
python3 scripts/margin.py --cost 120 --price 300 --platform fb-local

# Facebook Marketplace, shipped (10% selling fee, $0.80 minimum)
python3 scripts/margin.py --cost 120 --price 300 --platform fb-shipped --ship-collected 15 --ship-label 14

# Machine-readable
python3 scripts/margin.py --cost 120 --price 260 --platform ebay --json
```

Flags: `--cost` (landed COGS, required), `--price` (expected sale price,
required), `--platform {ebay,fb-shipped,fb-local}`, `--category <eBay tier>`,
`--ship-collected`, `--ship-label`, `--ship-in`, `--packaging`, `--promoted`
(percent), `--sales-tax` (buyer tax remitted by the platform; it still draws FVF),
`--fvf-override` (force a rate when live eBay numbers differ), `--json`.

| Channel | Cost to sell | Notes |
|---|---|---|
| eBay | FVF 6.7%–15.3% by category + $0.30/$0.40 per order | Free listing to 250/mo, then $0.35 |
| FB Marketplace, local | 0% | Pickup only, cash in hand |
| FB Marketplace, shipped | 10% of total transaction value, $0.80 min | Fraud/dispute rate runs higher than eBay |
| Nextdoor | 0% | **Reseller listings prohibited** — personal items only |

Research URLs (paste into `browser_navigate`, not scrapers):

```
https://www.ebay.com/sh/research            # Terapeak sold comps, Seller Hub
https://www.ebay.com/sellercenter/selling/start-selling-on-ebay/seller-fees
https://www.ebay.com/help/selling/fees-credits-invoices/selling-fees?id=4822
```

## Procedure

1. **Compliance gate — hard stop.** Open the brand's rules page on ExpertVoice.
   If it bans resale, transfer, or commercial use, stop; that item is buy-for-self
   only. Never share or describe your ExpertVoice pricing in a listing, DM, or
   store. Details and the exact Nextdoor rule: `references/compliance-and-risk.md`.
2. **Pull comps, not asking prices.** eBay Seller Hub → Research → search the
   exact model number, filter to Sold, look at 90 days. Read the **low band** of
   real sold prices, not the top outlier. Skip anything with fewer than ~3 comps.
   Method and filtering rules: `references/listing-playbook.md`.
3. **Landed cost.** `cost = price paid + inbound shipping + sales tax you paid`.
   Pro deals often ship free, so this is usually just the invoice total.
4. **Run the math.** `scripts/margin.py` with the price you plan to list at.
   Target **≥30% net margin or ≥$40 net per item**, whichever is higher — below
   that, one return or one bad buyer erases the trade.
5. **Route the item.** Local-only if it's heavy, fragile, or over ~$250 (FB local,
   0% fee, no shipping risk). Shippable and comped ≥$60 → eBay. Nextdoor gets
   personal items only, never flip stock.
6. **List.** Copy formula and photo set per channel: `references/listing-playbook.md`.
   For eBay use Buy It Now + free shipping + "Allow Offers" (free) instead of a
   reserve (reserve fees are $5 or 7.5% of reserve, whichever is greater).
7. **Fulfil.** Ship within one business day; keep the receipt/proof of drop-off.
   For local handoffs meet in public, cash or an established P2P app, and follow
   Nextdoor's own guidance on payment safety.
8. **Log and track tax.** Write the row to your CSV the day it sells. Marketplaces
   issue a 1099-K at the federal threshold; keep cost receipts regardless.

## Pitfalls

- **Fee tables move.** Treat the numbers in `references/platform-fees.md` as a
  snapshot, not gospel; re-check eBay's fee page at the start of any real run and
  use `--fvf-override` when it has changed.
- eBay's own pages disagree with each other on tier caps ($2,500 vs $7,500 for the
  same category depending on seller-center page vs help page). Verify against the
  fee page and your actual payout statement.
- Facebook Marketplace fee sources conflict (5% vs 10%); Meta's own help page
  states 10% with an $0.80 minimum. Use Meta's number.
- Selling used gear as new, or with the brand's marketing photos, invites a VeRO
  intellectual-property takedown. Shoot your own photos.
- **Sold-listings search needs a signed-in session.** An anonymous fetch of
  `/sch/i.html?_nkw=...&LH_Sold=1&LH_Complete=1` redirects to
  `signin.ebay.com`, and a plain `curl` gets eBay's "Error Page" (HTTP 403).
  Comps come from Terapeak in Seller Hub or from the browser while logged in —
  never from an anonymous scrape. Public category/deals pages still fetch fine.
- Terapeak Product Research supports preset ranges from **7 days** to 3 years
  plus a custom range, so a sub-90-day window (a "last 10 days" question) is a
  custom range or the 7-day preset. eBay publishes no public ranked
  top-sellers list by category, so Terapeak is the only item-level answer.
- Prior-year sold comps drift fast on seasonal gear. Weight the last 90 days.
- Thin-margin categories (books/media at 15.3%, handbags and jewelry at 15%) eat
  the deal alive — run the numbers before you buy, not after.
- Nextdoor moderators remove reseller listings and can place the account on
  read-only access or suspend it. Not worth the inventory.
- A single eBay return on a $40-margin item is a loss once you pay return shipping.

## Verification

The calculator must reproduce **both** of eBay's own published selling-fee
scenarios. Run these through the `terminal` tool and compare:

```
# Payment $210.50 ($200 item + $10.50 buyer tax) -> fees $29.03 -> payout $170.97
python3 scripts/margin.py --cost 0 --price 200 --sales-tax 10.50 --platform ebay --category most --json

# Payment $85.60 ($80 item + $5.60 buyer tax) -> fees $12.04 -> payout $67.96
python3 scripts/margin.py --cost 0 --price 80 --sales-tax 5.60 --platform ebay --category most --json
```

Case 1 must report `fvf` `28.63`, `per_order_fee` `0.40`, `platform_fees` `29.03`,
`net_profit` `170.97`. Case 2 must report `platform_fees` `12.04` and
`net_profit` `67.96`. If either drifts, the tier table in `scripts/margin.py` is
stale — re-check it against the live fee page before trusting any other output.

## Reference Files

Load on demand with `skill_view(name="expertvoice-flipping", file_path="references/<file>")`:

- `references/platform-fees.md` — eBay final-value-fee tiers, insertion and
  per-order fees, FB Marketplace fees, shipping-label cost bands, 1099-K. Load
  when pricing or when you need the exact fee line for a category.
- `references/compliance-and-risk.md` — ExpertVoice honor code and brand rules,
  the Nextdoor reseller prohibition, MAP/VeRO risk, account-suspension paths,
  tax trail. **Load before buying any item you intend to resell.**
- `references/account-brand-list.md` — how to read the account's own brand-access
  list off the signed-in session: attaching over CDP (including the Chrome >= 136
  default-profile block), tab targeting, the `/xapi/...` endpoints behind
  shopping vs learning access, and the reconciliation checks. Load when asked what
  brands the account can shop, or before a sourcing run.
- `references/listing-playbook.md` — comp research method, pricing ladder, title
  and photo formulas, per-channel copy templates, buyer-message scripts, local
  handoff and logging. Load when writing a listing.
- `scripts/margin.py` — landed-cost + fee + margin calculator, break-even solver.
