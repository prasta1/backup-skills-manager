# CUSIP-to-Ticker Consensus Mapping

## Algorithm

1. Extract all `<SECINFO>` blocks from all source files' `<SECLIST>` sections
2. Group by `<UNIQUEID>` (CUSIP)
3. For each CUSIP, tally the `<TICKER>` values across files
4. Use the plurality winner as the consensus ticker
5. Record:
   - `ticker`: consensus value
   - `ticker_status`: resolution status
   - `notes`: provenance and corrections

## Status Values

| Status | Meaning | Action |
|--------|---------|--------|
| `resolved` | Consensus ticker from OFX SECLIST | Use directly |
| `corrected` | Web search proved OFX consensus wrong | Patch ticker, document in notes |
| `internal_fund` | No standard exchange ticker | Keep CUSIP, mark as internal |
| `unresolved` | No ticker found anywhere | Leave ticker blank |
| `conflict` | Multiple tickers with no plurality winner | Document both in notes |

## Provenance Fields

- `source_count`: number of files where this CUSIP appeared
- `ticker_count`: number of files where the consensus ticker appeared
- `all_tickers`: comma-separated list of all tickers seen

## Known Special Cases

### Wealthfront Internal Funds
- `74926P688` → `TIMXX` (RBC cash sweep fund)
- `90214Q873` → `WFRPX` (Wealthfront Risk Parity Fund, liquidated Jan 2025)

### Common Self-Mapped CUSIPs
Some CUSIPs appear as their own ticker in certain years. When a standard ticker exists externally, prefer it:
- `26614N102` → `DD` (DuPont de Nemours)
- `30231G102` → `XOM` (Exxon Mobil)
- `438516106` → `HON` (Honeywell)
- `G5494J103` → `LIN` (Linde plc)
- `931427108` → `WBA` (Walgreens)
- `09247X101` → `BLK` (BlackRock)

## Why Not External APIs

In batch OFX parsing:
- OpenFIGI requires API key and rate-limits unauthenticated requests
- FMP requires API key for CUSIP endpoint
- SEC-API requires token for bulk mapping
- CUSIP.com API requires account

The OFX `<SECLIST>` section already contains the authoritative CUSIP→ticker mapping from the broker. Use it as the primary source. Reserve external lookups for manual corrections only.

## Conflict Resolution

When the same CUSIP maps to different tickers across files:
1. If one value is a known exchange ticker and the other is a CUSIP or fund name, prefer the exchange ticker
2. If both look valid, use the plurality winner and set `conflict`
3. Document the discrepancy in `notes`

## Output Format

```csv
cusip,ticker,security_name,status,notes,source_count,ticker_count,all_tickers
037833100,AAPL,APPLE INC COM,resolved,Resolved from 9/9 OFX files,9,9,AAPL
74926P688,TIMXX,RBC FDS TR BLUEBAY CL 2,internal_fund,Wealthfront cash sweep fund,8,8,TIMXX
90214Q873,WFRPX,TWO RDS SHARED TR WLTHFRONT RS W,internal_fund,Wealthfront Risk Parity Fund,7,7,WFRPX
```
