# Listing Playbook

From comps to published listing to paid. Use `browser_navigate` for the research
pages, `write_file` for the copy you will paste, `vision_analyze` to check your
photos against the comps.

## 1. Comp research (do this before you buy, not after)

Tool: **eBay Seller Hub → Research (Terapeak)**.

```
https://www.ebay.com/sh/research
```

Method:

1. Search the **exact model number**, not a generic description. "Brand Model
   1234" beats "brand jacket". Model numbers are what buyers search.
2. Filter to **Sold** and set the window to **90 days** (730 days is available;
   weight the recent end).
3. Sort by date-last-sold. Read the **low band** of prices that actually moved.
4. Require **at least ~3 real comps** for the exact variant. Under that you are
   guessing, and the guess is usually optimistic.
5. Compare the sold graphic against the active-listing count. Many active listings
   and few sold = the market is asking too much and you should price to the sold
   band, not the ask.
6. Discard obvious outliers in both directions (the $800 Pyrex jar and the
   $10 one). Terapeak shows the **actual accepted price** on Best Offer sales,
   which is why Terapeak and the listing page can disagree — the listing shows the
   ask, Terapeak shows what was paid.

**Seasonality:** outerwear, bikes, ski gear, and hunting optics move in season and
collapse out of it. A comp from last November is not a comp in June.

### Variant mattering

Size, colorway, and generation change price more than condition does. Comp the
variant you actually hold. If the item is a size XL in a discontinued colorway,
your comp set is not "the same model in any size."

## 2. Pricing ladder

| Number | Value |
|---|---|
| Comp low band (90d sold) | C |
| List price | C × 1.10 if the item is new-with-tags; C × 0.95 if used |
| Best Offer auto-accept floor | break-even price from `scripts/margin.py` |
| Best Offer auto-decline | 60% of list |
| Sale-price floor over 30 days | C × 0.90 |
| Markdown trigger | no movement in 30 days |

Rules:

- **Price to the sold band, not the asking band.** The asking band is aspirational
  inventory that hasn't sold.
- **Free shipping converts better than a lower price with shipping added.** A $50
  item with free shipping outsells a $42 item with $8 shipping at the same total.
  Build the label cost into the price, then check the net with `scripts/margin.py`.
- **Never list below the brand's street price.** Under-pricing is what attracts MAP
  attention and VeRO scrutiny.
- Use **Buy It Now + Allow Offers** instead of auctions. Auctions on mid-value gear
  realize less than the comp band more often than they beat it, and Best Offer is
  free where a reserve is not.
- Markdown cadence: 10% at day 30, another 10% at day 60, then re-evaluate against
  a fresh Terapeak pull.

## 3. Title formula (eBay, 80 characters of room)

```
Brand + Model/Model# + key spec + size/colorway + condition code + "- NWT/NIB"
```

- Brand name and model number are the two highest-weighted tokens. Put brand first.
- Spell the word **new** out; abbreviations like NWT/NIB/BIN are used by real
  buyers but "new" is the token that matches search phrasing.
- No keyword stuffing, no emoji, no "L@@K", no "RARE" unless it is genuinely rare.
- No brand marketing copy — that is what triggers IP takedowns.

## 4. Photo set (you shoot these; never reuse brand assets)

1. Hero: full item, plain background, natural light, tag visible if NWT.
2. Model/size tag close-up.
3. Flaw close-ups — every scratch, scuff, and seam. Under-report condition and
   over-shoot photos; this is what prevents item-not-as-described claims.
4. Contents: box, inserts, accessories, original packaging.
5. Scale reference (coin, ruler, or a hand) for anything whose size is ambiguous.

8–12 photos, square, first photo the hero. Check the result with `vision_analyze`
before uploading — if the item isn't obviously identifiable at thumbnail size,
retake it.

## 5. Condition statement (eBay item specifics, not prose)

- New with tags in hand → **New with tags** / **New**.
- Worn twice → **Pre-owned**, and say exactly what was done in it.
- Never list a used item as new. The return rate on that mistake is total, and it
  costs you the margin plus return freight.
- Fill every item specific eBay offers for the category. Blank specifics suppress
  the listing in filtered search, which is most buyers.

## 6. Facebook Marketplace listing template

**Title** (first 40 chars carry the weight in the feed): model number first,
condition second, price implicitly by category.

**Body** — four short lines, no walls of text:

```
Brand Model 1234, size L, new with tags (unused, tags attached).
Pickup in <town>, or I can ship within 1 business day.
Cash or <payment app> at pickup. Happy to meet somewhere public.
No holds without payment. Photos are of the actual item.
```

- Pick the sharpest category FB offers. Choose "Sell" + local pickup for anything
  heavy, fragile, or over ~$250.
- Enable shipping only for light, robust, well-comped items — FB's buyer pool has
  a higher dispute rate than eBay's, and there's no seller-side equivalent of eBay
  feedback history to lean on.
- Renew/refresh over editing the same listing forever; FB ranking decays.
- Don't include links to other marketplaces in the body.

## 7. Nextdoor — personal items only

Resale inventory is prohibited (see `references/compliance-and-risk.md`). When
listing a genuinely personal item, use the **Sell or give away** option, not a
plain feed post, or it gets reported and removed. Body:

```
Neighbor, I have a <item> that I no longer need. <Condition, 1 line>.
<Price>. Porch pickup on <street area>, or I can meet at <public spot>.
Cash or Venmo. First come, no holds.
```

One listing per item. No reposting for visibility. No cross-links. Buy here, sell
elsewhere.

## 8. Buyer messages

**Lowball:** "Thanks for the offer. I can do $X — that's already under the last
three sold on eBay. Firm at that number."

**"Is this still available?"** Answer within the hour with a one-liner and a
pickup window. Most FB sales go to whoever replies first.

**"Will you ship?"** (local listing) "Happy to ship — $X total delivered, paid
before it goes out."

**Bundling:** "Two-for-$Y if you take both at pickup." Bundle discount should
never cross the break-even line; re-run `scripts/margin.py` first.

## 9. Local handoff safety

- Meet in a public, camera-covered spot during daylight: police-station exchange
  areas, grocery-store entry, the town green.
- Cash in hand, or an established P2P app with no reversal path (Venmo/Zelle
  friends-and-family style, Cash App). Never accept a screenshot of a payment.
- Cashier's-check scams and overpayment scams are the two standard patterns. If a
  buyer offers more than asking, it is a scam.
- For porch pickup, don't post the house number in the listing; share it in DM
  when the pickup is confirmed.

## 10. Logging (the discipline that makes this a business)

Write the row the day the item sells. Columns:

```
sku,brand,item,model,date_bought,cost,channel,list_price,sold_price,platform_fees,shipping_cost,net,days_to_sell,notes
```

Hold the ExpertVoice invoice alongside it. That CSV is your cost basis when a
1099-K lands or an audit question arrives, and it is the only way to learn which
brands and categories actually print money for you versus which ones just felt
like good deals at purchase time.
