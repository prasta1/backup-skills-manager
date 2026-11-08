# OFX 1.02 SGML Structure Notes

## Key Tags

### Header
```
OFXHEADER:100
DATA:OFXSGML
VERSION:102
```

### Account Statement
- `<INVSTMTMSGSV1>` — investment statement messages
- `<INVSTMTTRNRS>` — transaction response wrapper
- `<INVSTMTRS>` — investment statement response
- `<INVACCTFROM>` — account identification
  - `<BROKERID>` — broker ID
  - `<ACCTID>` — account number
- `<INVTRANLIST>` — transaction list
  - `<DTSTART>` — period start
  - `<DTEND>` — period end
  - Transactions: `<INCOME>`, `<BUYMF>`, `<SELLMF>`, `<BUYSTOCK>`, `<SELLSTOCK>`, `<REINVEST>`, `<DIV>`, `<INVBANKTRAN>`
- `<INVPOSLIST>` — position list (may be empty)
- `<INVBAL>` — balances
  - `<AVAILCASH>`
  - `<MARGINBALANCE>`
  - `<SHORTBALANCE>`

### Transaction Fields
Each transaction wrapper contains:
- `<INVTRAN>` or `<INVBUY>`/`<INVSELL>`
  - `<FITID>` — unique transaction ID
  - `<DTTRADE>` — trade date
  - `<DTSETTLE>` — settlement date
- `<SECID>` — security identification
  - `<UNIQUEID>` — CUSIP or other ID
  - `<UNIQUEIDTYPE>` — `CUSIP`, `ISIN`, etc.
- Transaction-specific:
  - `<UNITS>` — quantity
  - `<UNITPRICE>` — price per unit
  - `<TOTAL>` — total amount (negative for buys)
  - `<INCOMETYPE>` — `DIV`, `INT`, `LT_CG`, `ST_CG`
  - `<BUYTYPE>` — `BUY`, `BUYTOCOVER`
  - `<SELLTYPE>` — `SELL`, `SELLSHORT`
  - `<SUBACCTSEC>` — `CASH`, `MARGIN`
  - `<SUBACCTFUND>` — `CASH`, `MARGIN`

### Security List (Mapping Source)
- `<SECLISTMSGSV1>` — security list messages
- `<SECINFO>` — individual security info
  - `<SECID>`
    - `<UNIQUEID>` — CUSIP
    - `<UNIQUEIDTYPE>` — `CUSIP`
  - `<SECNAME>` — full security name
  - `<TICKER>` — ticker symbol

### Positions
- `<INVPOSLIST>` — may contain `<POSMF>` or `<POSSTOCK>` blocks
- Or at statement end: `<POSSTOCK>`, `<POSMF>`
  - `<POSINV>`
    - `<SECID>`
    - `<UNITS>`
    - `<UNITPRICE>`
    - `<MKTVAL>` — market value
    - `<DTPRICEASOF>` — price date
    - `<MEMO>` — optional description

## Parsing Notes

1. **SGML, not XML:** Tags may be indented, split across lines, or have whitespace between them. Regex is more robust than XML parsers.
2. **Whitespace:** `<TAG>value</TAG>` may appear as:
   ```
   <TAG>
       value
   </TAG>
   ```
   Strip whitespace from extracted values.
3. **Empty sections:** `<SECLIST/>`, `<INVPOSLIST/>` are valid empty markers.
4. **Date format:** `YYYYMMDDHHMMSS.000` or `YYYYMMDDHHMMSS.000[±TZ]`
   - Strip non-digits, take first 8 chars for date part.
   - Time portion is often `.000` and can be ignored.

## Wealthfront-Specific Quirks

- Cash sweep fund: CUSIP `74926P688`, ticker `TIMXX`, name `RBC FDS TR BLUEBAY CL 2`
- Risk parity fund: CUSIP `90214Q873`, ticker `WFRPX`, name `TWO RDS SHARED TR WLTHFRONT RS W`
- Some years encode the CUSIP as the ticker in SECINFO when the security lacks an exchange symbol
- Fund transactions often use `<BUYMF>`/`<SELLMF>` with `UNITPRICE` of `1.00` and `UNITS` reflecting fractional share amounts
