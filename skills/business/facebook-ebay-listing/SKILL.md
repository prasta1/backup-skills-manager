---
name: facebook-ebay-listing
description: List items for sale on Facebook and eBay.
version: 0.1.0
author: Hermes
metadata:
  hermes:
    tags: [Marketplace, Resale, Listings, Pricing, Ecommerce]
---

# Facebook & eBay Listing

End-to-end workflow for putting an item up for sale on Facebook Marketplace and
eBay: price it from real sold comps, write platform-correct copy, post it in the
logged-in browser, then log the sale. Covers shipping vs pickup, fee math, buyer
safety, and the tax trail. It does **not** handle payments or transactions, buy
or source items, or manage returns. Neither platform exposes a casual-seller
listing API, so posting happens in the authenticated browser — never through a
scraper or a selling-endpoint client.

Fee tables and the comp playbook are shared with the `expertvoice-flipping`
skill on purpose: loading its `references/platform-fees.md` via `skill_view`
when pricing, and running its `scripts/margin.py` for margin math, instead of
typing the numbers twice in two skills.

## When to Use

- "List this on Facebook" / "sell my X on eBay" / "get this on Marketplace"
- "How much should I ask for…?" / "check comps on this"
- "Write the listing / draft the Marketplace post"
- "Which platform should this go on — eBay or Facebook?"

## Prerequisites

- A logged-in browser session for Patrick's Facebook and eBay accounts. Use
  `browser_exec` with `local: True` for his own browser (logins and cookies are
  already there); for the final Post/List clicks, Patrick can take the keyboard.
- Photos of the actual item, the seller's own. Never brand/marketing images.
- `python3` for the shared margin calculator:
  `~/.hermes/skills/business/expertvoice-flipping/scripts/margin.py`
- eBay sold-comps research (Terapeak) needs a signed-in session — Seller Hub →
  Research at `https://www.ebay.com/sh/research`. An anonymous sold search
  redirects to signin and a plain fetch gets 403.

## How to Run

Pipeline, in order:

1. `skill_view` (`expertvoice-flipping`, `references/platform-fees.md`) for the
   current fee snapshot — fees move, so re-verify at the start of a real run.
2. Pull sold comps for the exact model/variant (Terapeak, signed in).
3. Set the price from the comp band, then confirm the route's margin math.
4. `write_file` the listing draft to `~/.hermes/outputs/`; check the photo set
   with `vision_analyze` before uploading.
5. Post through `browser_exec` on the logged-in profile; verify the live URL.
6. Log the row in the inventory CSV the day it sells.

## Quick Reference

```
# Margin math for a $260 eBay sale, $18 label, free shipping (most categories)
python3 ~/.hermes/skills/business/expertvoice-flipping/scripts/margin.py \
  --cost 120 --price 260 --platform ebay --ship-label 18

# Facebook Marketplace, local pickup (no selling fee)
python3 ~/.hermes/skills/business/expertvoice-flipping/scripts/margin.py \
  --cost 120 --price 300 --platform fb-local

# Facebook Marketplace, shipped (10% selling fee, $0.80 minimum)
python3 ~/.hermes/skills/business/expertvoice-flipping/scripts/margin.py \
  --cost 120 --price 300 --platform fb-shipped --ship-collected 15 --ship-label 14
```

Fee snapshot — verify before a real run:

| Channel | Cost to sell |
|---|---|
| eBay | FVF 6.7%–15.3% by category (most categories 13.6% to $7,500) + $0.30/$0.40 per order; free to list up to 250/mo, then $0.35 |
| FB Marketplace, local | 0% |
| FB Marketplace, shipped | 10% of total transaction value, $0.80 min |

Start URLs (paste into the browser, signed in):

```
https://www.ebay.com/sh/research            # Terapeak sold comps, Seller Hub
https://www.ebay.com                        # start here → Sell → List an item
https://www.facebook.com/marketplace        # start here → Create new listing
```

## Procedure

1. **Identify and gate.** Name the item and why it is for sale. If it is flip
   inventory or came from a pro-deal program, load `expertvoice-flipping` first
   and honor its compliance gate — never describe pro-deal pricing in a public
   listing.
2. **Comps, not asks.** Search the exact model number in Terapeak, filter Sold,
   90-day window, read the **low band** of prices that moved, require ≥3 real
   comps. Many active listings + few sold = overpriced market. Terapeak shows
   the accepted price on Best Offer sales. Weight the recent 90 days on
   seasonal gear.
3. **Price.** List at comp × 1.10 (new with tags) or comp × 0.95 (used). Best
   Offer auto-accept = break-even from the margin calculator; auto-decline =
   60% of list. Markdown cadence: 10% at day 30, another 10% at day 60, then
   re-pull comps.
4. **Run the math.** `scripts/margin.py` on the candidate price confirms the
   route. Target ≥30% net margin or ≥$40 net per item, whichever is higher;
   below that one return erases the trade.
5. **Photos.** 8–12 square shots: hero on plain background, model/tag close-up,
   every flaw close-up, contents/box, scale reference. Check with
   `vision_analyze` — if it isn't identifiable at thumbnail size, retake.
6. **Draft copy.** Title per the formula below; FB body is a four-line block.
   `write_file` to `~/.hermes/outputs/` so it survives.
7. **Post on Facebook Marketplace.** `browser_exec` (`local: True`):
   facebook.com/marketplace → Create new listing → sharpest category → photos →
   title (first 40 chars carry the feed weight) → price + condition + pickup
   location. Local pickup for heavy, fragile, or over-$250 items; enable
   shipping only for light, robust, well-comped items — Facebook's buyer pool
   has a higher dispute rate than eBay's.
8. **Post on eBay.** ebay.com → Sell → List an item → category + photos +
   title → fill **every** item specific (blanks suppress the listing in
   filtered search) → condition (New / New with tags vs Pre-owned — never list
   used as new) → Buy It Now + Allow Offers (free) instead of auction/reserve
   → shipping free (converts better than a lower price plus a shipping
   charge; build label cost into the price).
9. **Confirm, then submit.** Posting is irreversible — hand Patrick the
   decision-ready draft and get one yes before the final Post/List click on
   either platform.
10. **Fulfill, hand off, log.** Ship within one business day, keep drop-off
    proof. Meet in public, camera-covered daylight; cash or an established P2P
    app with no reversal path (Venmo/Zelle friends-and-family style, Cash App);
    never accept a payment screenshot. Write the row to the inventory CSV the
    day it sells:
    `sku,brand,item,model,date_bought,cost,channel,list_price,sold_price,platform_fees,shipping_cost,net,days_to_sell,notes`

Copy templates:

**Facebook Marketplace body — four short lines, no walls of text:**

```
Brand Model 1234, size L, new with tags (unused, tags attached).
Pickup in <town>, or I can ship within 1 business day.
Cash or <payment app> at pickup. Happy to meet somewhere public.
No holds without payment. Photos are of the actual item.
```

**eBay title — 80 chars of room:**

```
Brand + Model/Model# + key spec + size/colorway + condition code
```

Brand and model number are the two highest-weighted search tokens — brand
first. Spell "new" out; no keyword stuffing, no emoji, no "RARE" unless it is
genuinely rare, no brand marketing copy.

## Pitfalls

- **Fee tables move.** Treat the snapshot as a starting point; re-check eBay's
  seller-fee page at the start of any real run and pass live numbers to
  `scripts/margin.py` with `--fvf-override`.
- **Facebook is anti-automation.** Heavy scripted posting on a personal account
  risks a flag or ban; keep the flow human-paced and let Patrick click the final
  Post on high-value items.
- **Renew, don't edit forever** on Facebook — ranking decays on stale listings;
  a fresh listing outperforms edits.
- **No cross-links** between marketplaces in listing bodies (FB removes them).
- **Used listed as new is a total-loss mistake** — returns erase margin plus
  freight.
- **Brand photos invite VeRO/IP takedowns and MAP attention** — shoot your own.
- **Auctions with a reserve cost $5 or 7.5% of the reserve whether it sells or
  not** — Buy It Now + Allow Offers gives the optionality for free.
- **"Is this still available?"** — answer within the hour; most FB sales go to
  the first reply. Lowball script: "Thanks for the offer. I can do $X — that's
  already under the last three sold on eBay. Firm at that number."
- **Payment app screenshots are not proof of payment.** Overpayment offers are
  always scams.
- Marketplaces issue **1099-K** at the $20K / 200-transaction federal
  threshold; keep cost receipts regardless, business activity or not.

## Verification

The listing is live: read back the published URL from Your listings (FB) or
Seller Hub → Active (eBay) and confirm title, price, and photos match the
draft. Fee math: `scripts/margin.py` reproduces eBay's own published scenarios
(see `expertvoice-flipping` → Verification: a $210.50 payment → $29.03 fees →
$170.97 payout; $85.60 payment → $12.04 fees → $67.96 payout) — if those drift,
the fee snapshot is stale. Sale row written to the CSV with net and date.
