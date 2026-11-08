#!/usr/bin/env python3
"""
Wealthfront QFX -> CSV converter + TradingAgents PortfolioStore importer.

Proven in a real session (2026-08): converted a synthetic Wealthfront QFX
(sgml format, <INVPOSLIST>/<POSSTOCK> + <SECLIST>) to CSV with CUSIP->ticker
resolution, and imported into TradingAgents' PortfolioStore.

Usage:
    pip install ofxparse
    # Convert QFX to CSV
    python wealthfront_import.py convert ~/Downloads/wealthfront.qfx --output ~/wealthfront_positions.csv
    # Import CSV into TradingAgents portfolio + watchlist
    python wealthfront_import.py import ~/wealthfront_positions.csv
    # One-liner: convert + import
    python wealthfront_import.py convert-import ~/Downloads/wealthfront.qfx
"""

from __future__ import annotations

import argparse
import csv
import sys
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from typing import Optional

try:
    from ofxparse import OfxParser
except ImportError:
    print("Error: ofxparse not installed. Run: pip install ofxparse", file=sys.stderr)
    sys.exit(1)


@dataclass
class Position:
    symbol: str
    name: str
    quantity: float
    unit_price: Optional[float]
    market_value: Optional[float]
    currency: str = "USD"


def parse_qfx(qfx_path: Path) -> tuple[list[Position], dict]:
    """Parse Wealthfront QFX file.

    Returns (positions, summary). QFX positions carry a security uniqueid
    (usually CUSIP); the <SECLIST> section maps that to a ticker + name,
    which we resolve here.
    """
    with open(qfx_path, "rb") as f:
        ofx = OfxParser.parse(f)

    # uniqueid -> (ticker, name) map from the security list.
    sec_map: dict[str, tuple[str, str]] = {}
    for sec in ofx.security_list or []:
        ticker = (sec.ticker or sec.uniqueid).upper()
        name = sec.name or ticker
        sec_map[sec.uniqueid] = (ticker, name)

    positions: list[Position] = []
    total_nav = Decimal("0")
    total_cash = Decimal("0")

    for account in ofx.accounts:
        stmt = account.statement
        if stmt is None:
            continue
        total_cash += Decimal(getattr(stmt, "available_cash", 0) or 0)

        for pos in stmt.positions:
            uniqueid = pos.security
            ticker, name = sec_map.get(uniqueid, (uniqueid.upper(), uniqueid.upper()))
            units = pos.units or 0
            unit_price = pos.unit_price or 0
            market_value = pos.market_value or 0
            total_nav += Decimal(market_value)

            if units > 0:
                positions.append(Position(
                    symbol=ticker,
                    name=name,
                    quantity=float(units),
                    unit_price=float(unit_price) if unit_price else None,
                    market_value=float(market_value) if market_value else None,
                ))

    summary = {
        "nav": float(total_nav),
        "cash": float(total_cash),
        "accounts": len(ofx.accounts),
        "positions": len(positions),
    }
    return positions, summary


def write_csv(positions: list[Position], output_path: Path) -> None:
    """Write positions to CSV with TradingAgents-friendly columns."""
    fieldnames = ["symbol", "name", "quantity", "unit_price", "market_value", "currency"]
    with open(output_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for pos in sorted(positions, key=lambda p: p.market_value or 0, reverse=True):
            writer.writerow({
                "symbol": pos.symbol,
                "name": pos.name,
                "quantity": pos.quantity,
                "unit_price": pos.unit_price if pos.unit_price is not None else "",
                "market_value": pos.market_value if pos.market_value is not None else "",
                "currency": pos.currency,
            })
    print(f"Wrote {len(positions)} positions to {output_path}")


def import_to_portfolio_store(csv_path: Path) -> None:
    """Import positions CSV into TradingAgents PortfolioStore.

    Each position becomes a portfolio entry (ticker, shares, cost_basis) and
    is also added to the watchlist so the console surfaces it.
    """
    project_root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(project_root))

    from tradingagents.command_center.portfolio_store import PortfolioStore

    store = PortfolioStore()
    existing = {p["ticker"].upper() for p in store.get_portfolio()}

    added, updated = 0, 0
    with open(csv_path, newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            symbol = (row.get("symbol") or "").upper().strip()
            if not symbol:
                continue
            try:
                shares = float(row.get("quantity") or 0)
            except ValueError:
                shares = 0.0
            try:
                cost_basis = float(row.get("unit_price") or 0)
            except ValueError:
                cost_basis = 0.0

            if symbol in existing:
                updated += 1
            else:
                added += 1
                existing.add(symbol)
            store.add_position(symbol, shares=shares, cost_basis=cost_basis)
            store.add_to_watchlist(symbol)

    portfolio = store.get_portfolio()
    print(f"Portfolio: {added} added, {updated} updated (total {len(portfolio)} positions)")
    print("Tickers:", ", ".join(sorted(p["ticker"] for p in portfolio)))


def main():
    parser = argparse.ArgumentParser(description="Wealthfront QFX converter + importer")
    subparsers = parser.add_subparsers(dest="command", required=True)

    p_convert = subparsers.add_parser("convert", help="Convert QFX to CSV")
    p_convert.add_argument("qfx_file", type=Path, help="Path to Wealthfront QFX file")
    p_convert.add_argument("--output", "-o", type=Path, help="Output CSV path (default: <qfx_stem>.csv)")

    p_import = subparsers.add_parser("import", help="Import CSV into PortfolioStore")
    p_import.add_argument("csv_file", type=Path, help="Path to positions CSV")

    p_both = subparsers.add_parser("convert-import", help="Convert QFX to CSV and import")
    p_both.add_argument("qfx_file", type=Path, help="Path to Wealthfront QFX file")
    p_both.add_argument("--output", "-o", type=Path, help="Output CSV path (default: <qfx_stem>.csv)")

    args = parser.parse_args()

    if args.command in ("convert", "convert-import"):
        qfx_path = args.qfx_file
        if not qfx_path.exists():
            print(f"Error: {qfx_path} not found", file=sys.stderr)
            sys.exit(1)
        output = args.output or qfx_path.with_suffix(".csv")
        positions, summary = parse_qfx(qfx_path)
        print(f"Account summary: NAV=${summary['nav']:,.2f} cash=${summary['cash']:,.2f} "
              f"({summary['positions']} positions across {summary['accounts']} account(s))")
        if not positions:
            print("Warning: No positions found in QFX", file=sys.stderr)
            sys.exit(1)
        write_csv(positions, output)

        if args.command == "convert-import":
            import_to_portfolio_store(output)

    elif args.command == "import":
        csv_path = args.csv_file
        if not csv_path.exists():
            print(f"Error: {csv_path} not found", file=sys.stderr)
            sys.exit(1)
        import_to_portfolio_store(csv_path)


if __name__ == "__main__":
    main()
