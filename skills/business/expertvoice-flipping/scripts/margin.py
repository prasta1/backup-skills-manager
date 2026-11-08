#!/usr/bin/env python3
"""Net-margin calculator for reselling pro-deal goods.

Channels: eBay, Facebook Marketplace (shipped), Facebook Marketplace (local).
Stdlib only. All amounts USD.

Fee rules encoded here are a snapshot of the published 2026 schedules.
Re-verify against the live pages before a real run; use --fvf-override when
they have moved.

  eBay fees: https://www.ebay.com/sellercenter/selling/start-selling-on-ebay/seller-fees
  FB fees:   https://m.facebook.com/help/620680138523186
"""

import argparse
import json
import sys

# eBay final value fee, individual (non-Store) US seller.
# Each tier is (cumulative_cap, rate); the final tier uses None as "remainder".
EBAY_TIERS = {
    "most":         [(7500.0, 0.136)],
    "electronics":  [(2500.0, 0.0935)],   # cameras, cell phones, most consumer electronics
    "computers":    [(2500.0, 0.0735)],   # desktops, laptops, tablets, components
    "music-gear":   [(2500.0, 0.1035)],   # most musical instruments & gear
    "guitars":      [(7500.0, 0.067)],
    "consoles":     [(2500.0, 0.0735)],   # video game consoles
    "cards":        [(7500.0, 0.1325)],   # trading cards
    "books-media":  [(7500.0, 0.153)],    # books, movies & TV, music
    "handbags":     [(2000.0, 0.15)],     # women's bags & handbags
    "jewelry":      [(5000.0, 0.15)],     # jewelry & watches, except watches
    "watches":      [(1000.0, 0.15), (5000.0, 0.065)],  # watches, parts & accessories
}
EBAY_OVER_RATE = {          # rate applied to the portion above the last cap
    "most": 0.0235, "electronics": 0.0235, "computers": 0.0235,
    "music-gear": 0.0235, "guitars": 0.0235, "consoles": 0.0235,
    "cards": 0.0235, "books-media": 0.0235,
    "handbags": 0.09, "jewelry": 0.09, "watches": 0.03,
}

FB_SHIPPED_RATE = 0.10   # of total transaction value (item + shipping + tax)
FB_SHIPPED_MIN = 0.80


def ebay_fvf(total, category):
    """Final value fee on the total amount of the sale. Athletic shoes special-cased."""
    if category == "athletic-shoes":
        return round(total * (0.08 if total >= 150.0 else 0.136), 2)
    tiers = EBAY_TIERS[category]
    over = EBAY_OVER_RATE[category]
    fee, prev = 0.0, 0.0
    for cap, rate in tiers:
        if total <= prev:
            break
        slice_amt = min(total, cap) - prev
        fee += slice_amt * rate
        prev = cap
    if total > prev:
        fee += (total - prev) * over
    return round(fee, 2)


def ebay_per_order_fee(total, category):
    if category == "athletic-shoes" and total >= 150.0:
        return 0.0
    return 0.30 if total <= 10.0 else 0.40


def compute(platform, category, price, ship_collected, sales_tax, ship_label,
            ship_in, packaging, cogs, promoted_pct, fvf_override):
    gross_to_buyer = price + ship_collected
    taxable_base = gross_to_buyer + sales_tax  # platform collects tax, but FVF is charged on it

    if platform == "ebay":
        if fvf_override is not None:
            fvf = round(taxable_base * fvf_override / 100.0, 2)
        else:
            fvf = ebay_fvf(taxable_base, category)
        per_order = ebay_per_order_fee(taxable_base, category)
        promo = round(taxable_base * promoted_pct / 100.0, 2)
        platform_fees = round(fvf + per_order + promo, 2)
    elif platform == "fb-shipped":
        fvf = max(round(taxable_base * FB_SHIPPED_RATE, 2), FB_SHIPPED_MIN)
        per_order = 0.0
        promo = 0.0
        platform_fees = fvf
    elif platform == "fb-local":
        fvf = per_order = promo = platform_fees = 0.0
        ship_collected = 0.0
        ship_label = 0.0
    else:
        raise SystemExit("unknown platform: %s" % platform)

    costs = ship_label + ship_in + packaging + cogs
    net = round(gross_to_buyer - platform_fees - costs, 2)
    roi = round((net / cogs) * 100.0, 1) if cogs else None
    margin_pct = round((net / gross_to_buyer) * 100.0, 1) if gross_to_buyer else None
    return {
        "platform": platform,
        "category": category if platform == "ebay" else None,
        "price": price,
        "ship_collected": ship_collected,
        "sales_tax_collected": sales_tax,
        "gross_to_buyer": round(gross_to_buyer, 2),
        "fvf": fvf,
        "per_order_fee": per_order,
        "promoted_fee": promo,
        "platform_fees": platform_fees,
        "shipping_label": ship_label,
        "inbound_shipping": ship_in,
        "packaging": packaging,
        "cogs": cogs,
        "net_profit": net,
        "net_margin_pct": margin_pct,
        "roi_pct": roi,
    }


def breakeven(platform, category, ship_collected, sales_tax, ship_label, ship_in,
              packaging, cogs, promoted_pct, fvf_override):
    """Lowest sale price with net >= 0. Net is monotonic in price, so bisect."""
    lo, hi = 0.01, 100000.0
    for _ in range(80):
        mid = (lo + hi) / 2.0
        r = compute(platform, category, mid, ship_collected, sales_tax, ship_label,
                    ship_in, packaging, cogs, promoted_pct, fvf_override)
        if r["net_profit"] < 0:
            lo = mid
        else:
            hi = mid
    return round(hi, 2)


def money(v):
    return "-" if v is None else "$%0.2f" % v


def main():
    p = argparse.ArgumentParser(description="Resale net-margin calculator")
    p.add_argument("--cost", type=float, required=True, help="landed COGS: price paid + inbound shipping + tax paid")
    p.add_argument("--price", type=float, required=True, help="expected sale price")
    p.add_argument("--platform", choices=["ebay", "fb-shipped", "fb-local"], default="ebay")
    p.add_argument("--category", default="most",
                   choices=sorted(list(EBAY_TIERS.keys()) + ["athletic-shoes"]),
                   help="eBay fee tier")
    p.add_argument("--ship-collected", type=float, default=0.0)
    p.add_argument("--ship-label", type=float, default=0.0)
    p.add_argument("--ship-in", type=float, default=0.0)
    p.add_argument("--packaging", type=float, default=0.0)
    p.add_argument("--sales-tax", type=float, default=0.0)
    p.add_argument("--promoted", type=float, default=0.0, help="eBay promoted-listings ad rate, percent")
    p.add_argument("--fvf-override", type=float, default=None, help="force final value fee percent")
    p.add_argument("--json", action="store_true")
    a = p.parse_args()

    r = compute(a.platform, a.category, a.price, a.ship_collected, a.sales_tax,
                a.ship_label, a.ship_in, a.packaging, a.cost, a.promoted, a.fvf_override)
    be = breakeven(a.platform, a.category, a.ship_collected, a.sales_tax, a.ship_label,
                   a.ship_in, a.packaging, a.cost, a.promoted, a.fvf_override)

    if a.json:
        r["breakeven_price"] = be
        print(json.dumps(r, indent=2))
        return 0

    print("platform: %s%s" % (a.platform, " / " + a.category if a.platform == "ebay" else ""))
    print("sale price                 %s" % money(r["price"]))
    if r["ship_collected"]:
        print("shipping collected         %s" % money(r["ship_collected"]))
    if r["sales_tax_collected"]:
        print("sales tax (remitted)       %s" % money(r["sales_tax_collected"]))
    print("gross to buyer             %s" % money(r["gross_to_buyer"]))
    if r["fvf"]:
        print("  final value fee          -%s" % money(r["fvf"])[1:])
    if r["per_order_fee"]:
        print("  per order fee            -%s" % money(r["per_order_fee"])[1:])
    if r["promoted_fee"]:
        print("  promoted listings        -%s" % money(r["promoted_fee"])[1:])
    if r["shipping_label"]:
        print("  shipping label           -%s" % money(r["shipping_label"])[1:])
    if r["inbound_shipping"]:
        print("  inbound shipping         -%s" % money(r["inbound_shipping"])[1:])
    if r["packaging"]:
        print("  packaging                -%s" % money(r["packaging"])[1:])
    print("  cost of goods            -%s" % money(r["cogs"])[1:])
    print("net profit                %s" % money(r["net_profit"]))
    print("net margin                %s%%" % r["net_margin_pct"])
    print("ROI on cost              %s%%" % r["roi_pct"])
    print("breakeven sale price      %s" % money(be))
    verdict = "PASS" if (r["net_profit"] and r["net_profit"] >= 40
                         and r["net_margin_pct"] >= 30) else "FAIL (need >=$40 net and >=30% margin)"
    print("gate                      %s" % verdict)
    return 0


if __name__ == "__main__":
    sys.exit(main())
