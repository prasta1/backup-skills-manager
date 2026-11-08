---
name: financial-export
description: "Convert OFX/QFX exports to analysis-ready CSVs."
---

# Financial Export Conversion

Convert proprietary broker export formats into analyzable CSVs with full identifier provenance. Covers OFX 1.02 SGML investment statements and similar dumps.

## Trigger

- "convert my QFX/OFX files"
- "export my transactions to CSV"
- "parse my bank/broker statements"
- "make my financial data analyzable"
- User attaches `.qfx`, `.ofx`, `.qbo`, `.qif` files

## Output Shape

Produce up to three files, all CSV:

1. **Transactions CSV** — one row per buy/sell/dividend/transfer
2. **Positions CSV** — holdings snapshots by statement date
3. **Mapping CSV** — CUSIP→ticker resolution with status and provenance

Never overwrite originals. Write new files with clear names.

## Workflow

### 1. Inventory

List matching files in the target directory. Read each file's header to extract:
- Format version (`OFXHEADER:100`, `DATA:OFXSGML`, `VERSION:102`)
- Account ID
- Date range
- Whether transactions/positions are present or empty

Flag empty files early. Multi-year exports often include empty year-boundary shells; note them but do not reprocess.

### 2. Parse

OFX 1.02 SGML is tag-delimited with whitespace/newlines between tags. Treat as structured text, not XML.

**Transaction wrappers:** `<BUYSTOCK>`, `<SELLSTOCK>`, `<BUYMF>`, `<SELLMF>`, `<INCOME>`, `<DIV>`, `<REINVEST>`, `<INVBANKTRAN>`
**Fields:** `<FITID>`, `<DTTRADE>`, `<DTSETTLE>`, `<SECID>`, `<UNITS>`, `<UNITPRICE>`, `<TOTAL>`
**Positions:** `<INVPOSLIST>`, `<POSSTOCK>`, `<POSMF>`
**Balances:** `<AVAILCASH>`, `<MARGINBALANCE>`, `<SHORTBALANCE>`

**Date handling:**
OFX dates are `YYYYMMDDHHMMSS.000`. Strip non-digits, take first 8 chars, format as `YYYY-MM-DD`.

### 3. Consensus Mapping

Do not call external APIs for CUSIP→ticker resolution.

1. Extract every `<SECINFO>` block from every file's `<SECLIST>` section
2. Group by `<UNIQUEID>` (CUSIP)
3. Take the most frequent `<TICKER>` value as the consensus
4. Record source count and total count for provenance

**Conflicts:** When the same CUSIP gets different tickers across files, set `ticker_status = "conflict"`, document in `notes`, and use the plurality winner.

**Internal/non-standard securities:**
- If ticker equals the CUSIP itself, the security has no exchange symbol
- Common wrappers: `74926P688` (TIMXX cash sweep), `90214Q873` (WFRPX risk parity fund)
- Mark these `ticker_status = "internal_fund"` and keep the CUSIP in `ticker_or_cusip`

**Manual corrections:** If external verification proves a consensus ticker is wrong, patch it and set `ticker_status = "corrected"`. Document in `notes`.

### 4. Enrich

Add to each transaction/position row:
- `ticker` — resolved symbol, blank if unresolved
- `ticker_status` — `resolved`, `corrected`, `internal_fund`, `unresolved`, `conflict`
- `security_name` — from `<SECNAME>` in SECINFO

Always keep original `ticker_or_cusip` and `id_type` columns.

## Pitfalls

- **Empty statements:** First and last year-boundary files often have zero transactions. Parse them but they contribute no rows.
- **Year-boundary dates:** OFX statements often use `YYYY0101` as end date for the prior year. This is correct.
- **Duplicate FITIDs:** Different statement files may reuse the same FITID space. Combine with `source_file` and `statement_end` for uniqueness.
- **MF vs STOCK:** Mutual funds use `<BUYMF>`/`<SELLMF>`; stocks use `<BUYSTOCK>`/`<SELLSTOCK>`. Do not conflate them.
- **External API limits:** OpenFIGI, FMP, SEC-API, and CUSIP.com all require keys or hit rate limits. Do not depend on them for batch jobs. The SECLIST data in the OFX files is the authoritative source.

## Output Columns

### Transactions
`date`, `settle_date`, `category`, `transaction_type`, `ticker_or_cusip`, `ticker`, `id_type`, `units`, `unit_price`, `total`, `subacct_sec`, `subacct_fund`, `fitid`, `memo`, `source_file`, `account`, `statement_start`, `statement_end`, `cash_balance_end`, `margin_balance_end`, `short_balance_end`, `ticker_status`, `security_name`

### Positions
`statement_end`, `statement_start`, `account`, `position_type`, `ticker_or_cusip`, `ticker`, `id_type`, `units`, `unit_price`, `market_value`, `price_date`, `memo`, `source_file`, `cash_balance_end`, `margin_balance_end`, `short_balance_end`, `ticker_status`, `security_name`

## References

- `references/ofx-structure.md` — OFX 1.02 tag inventory and parsing gotchas
- `references/cusip-mapping.md` — SECLIST extraction and consensus algorithm
