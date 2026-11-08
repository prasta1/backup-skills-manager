# Platform Fees — Snapshot and Verification

Snapshot of published US fee schedules. **Fee tables move.** Re-check the source
URLs at the start of any real run; pass the new number to `scripts/margin.py`
with `--fvf-override` rather than editing the script in a hurry.

Sources:

- eBay individual fees: https://www.ebay.com/sellercenter/selling/start-selling-on-ebay/seller-fees
- eBay full schedule: https://www.ebay.com/help/selling/fees-credits-invoices/selling-fees?id=4822
- eBay Store fees: https://www.ebay.com/help/selling/fees-credits-invoices/store-selling-fees-managed-payments-sellers?id=4809
- FB Marketplace selling fee: https://m.facebook.com/help/620680138523186
- FB selling with shipping: https://m.facebook.com/help/773379109714742
- 1099-K thresholds: https://www.ebay.com/sellercenter/resources/changes-to-ebay-and-your-1099-k

## eBay — how the fee is built

- **Free to list.** No insertion fee for most casual sellers. After 250 listings
  in a month, $0.35 per additional listing. Category exclusions apply.
- **Final value fee (FVF)** is charged only when the item sells, as a percentage
  of **the total amount of the sale — item price, shipping charged to the buyer,
  sales tax, and other applicable fees** — plus a per-order fee.
- **Per-order fee**: $0.30 on orders $10.00 or less, $0.40 on orders over $10.00.
- **Promoted Listings** = optional ad rate, charged only if the item sells. This
  is a real margin line; model it with `--promoted`.
- Fees and dispute/refund costs are deducted from earnings. If earnings don't
  cover them, eBay charges your payment method within 14 days.

### FVF tiers, individual (non-Store) seller

| Category | FVF tiers |
|---|---|
| Most categories | 13.6% up to $7,500, then 2.35% |
| Cameras, cell phones, most consumer electronics | 9.35% up to $2,500, then 2.35% |
| Computers (desktops, laptops, tablets, components) | 7.35% up to $2,500, then 2.35% |
| Most musical instruments & gear | 10.35% up to $2,500, then 2.35% |
| Guitars & basses | 6.7% up to $7,500, then 2.35% |
| Video game consoles | 7.35% up to $2,500, then 2.35% |
| Trading cards | 13.25% up to $7,500, then 2.35% |
| Books, movies & TV, music (excl. vinyl) | 15.3% up to $7,500, then 2.35% |
| Women's bags & handbags | 15% to $2,000, then 9% |
| Most jewelry & watches (excl. watches) | 15% to $5,000, then 9% |
| Watches, parts & accessories | 15% to $1,000; 6.5% $1,000–$5,000; 3% over $5,000 |
| Athletic shoes | 8% if the sale is $150 or more (no per-order fee); 13.6% below $150 |
| Sneakers over $150 | 8%, no per-order fee |
| Heavy equipment | 3% to $15,000, then 0.5% |
| Bullion | 13.6% to $7,500, then 7% |

**Tier-cap conflict:** eBay's seller-center page lists most categories as
"up to $7,500" while the help page shows $2,500 caps for the same categories.
Trust the seller-center fee page and your actual payout statement. For anything
above ~$2,000 this difference is worth real money — verify before listing.

### eBay Store subscriptions (the discount lever)

| Store | Fixed-price free listings | Auction free listings | Most-category FVF |
|---|---|---|---|
| Basic | 1,000/mo | 250/mo | 12.7% to $2,500, then 2.35% |
| Premium | 10,000/mo | 500/mo | 12.7% to $2,500, then 2.35% |
| Anchor | 25,000/mo | 1,000/mo | 12.7% to $2,500, then 2.35% |
| Enterprise | 100,000/mo | 2,500/mo | 12.7% to $2,500, then 2.35% |

Starter Store subscribers get 13.6% to $7,500 on most categories. Electronics at
9.35%, computers at 7.35%, books/media at 15.3% for subscribers.

A Store only pays off past roughly the point where the FVF delta on your monthly
volume exceeds the subscription. Below ~$500/month in sales it is not worth it.

## eBay — optional costs that bite

- **Reserve price** (auctions): $5 or 7.5% of the reserve, whichever is greater,
  capped at $250 — **charged whether or not the item sells**. Avoid. Use Buy It
  Now plus "Allow Offers" (free) to get the same optionality.
- **Listing upgrades** (subtitle, etc.): charged at listing time regardless of sale.
- **Promoted Listings**: sale-contingent ad fee.
- Return shipping on a defect/SNAD claim lands on the seller.

## Facebook Marketplace

| Mode | Selling fee | Notes |
|---|---|---|
| Local pickup / dropoff | **0%** | No platform fee at all |
| Shipped (checkout on Marketplace) | **10%** of total transaction value, **$0.80 minimum per order** | Total value = item price + shipping + applicable taxes |

- Meta's help page states 10% / $0.80 minimum, effective April 2024. Third-party
  blogs still quote the older 5% / $0.40 — **use Meta's number**.
- Meta may offer promotional rates through qualifying seller programs.
- Payout goes to the bank account entered when shipping was set up.

**Prepaid shipping labels (Marketplace rates, approximate bands):**

| Weight | Cost band |
|---|---|
| Under 1 lb | $3.49 – $5.99 |
| 1–5 lbs | $5.99 – $10.99 |
| 5–20 lbs | $10.99 – $18.99 |
| Over 20 lbs | $18.99+ |

Ship-on-your-own is allowed (set your own shipping price, choose your own
carrier); the 10% selling fee still applies to the item price. Budget carriers
routinely beat the prepaid label rates on heavier parcels.

**Channel economics:** eBay keeps roughly $78 on a $100 shipped sale at 13.6% +
$0.40; FB shipped with a buyer-paid label at Marketplace rates nets more when the
item is light, and less once you absorb label cost on a heavy parcel.

## Nextdoor

- No listing or selling fee. Not the constraint — the constraint is policy. See
  `references/compliance-and-risk.md`: reseller and business listings are
  prohibited.
- Payment is buyer-to-seller P2P. Nextdoor recommends established apps (Venmo,
  PayPal, Zelle, Cash App), credit over debit, and monitoring statements. There
  is no marketplace purchase protection behind a Nextdoor sale.

## Tax trail

- Marketplaces are third-party settlement organizations and issue **Form 1099-K**
  when reportable payments exceed **$20,000 and more than 200 transactions**
  (federal threshold, permanently restored by the July 2025 tax bill; eBay's own
  page and the IRS confirm the same figure).
- Below that threshold there is still a reporting obligation if the activity is a
  business. Cost basis is on you to document — keep the ExpertVoice invoice and
  the payment record for every item.
- Marketplace-facilitated sales tax is collected and remitted by the platform; it
  is not your income, but eBay's FVF **is** charged on it, which is why
  `scripts/margin.py` accepts `--sales-tax`.

## Quick sanity numbers

| Sale | eBay "most" fees | Seller keeps (before COGS/shipping) |
|---|---|---|
| $50 | $6.80 + $0.40 = $7.20 | $42.80 |
| $100 | $13.60 + $0.40 = $14.00 | $86.00 |
| $260 | $35.36 + $0.40 = $35.76 | $224.24 |
| $500 | $68.00 + $0.40 = $68.40 | $431.60 |
