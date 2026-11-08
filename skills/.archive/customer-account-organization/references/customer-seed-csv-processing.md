# HubSpot CSV Seed Processing

The customer account organization skill can process CSV exports from CRM systems like HubSpot to seed the markdown-based customer directory.

## Key Considerations

1. **Field Mapping**: The script maps HubSpot fields to the markdown frontmatter schema:
   - Company name → `name`
   - Account Risk Level → `health` (mapped from "Very High Risk" to red, etc.)
   - Renewal Date → `renewal`
   - Total Active CARR → `arr`
   - Last Activity Date → `last_touch`
   - CSM Owner/Company owner → `tsh`

2. **Data Normalization**
   - Dates are normalized to ISO format (YYYY-MM-DD)
   - ARR values are cleaned and formatted with $ prefix
   - Risk levels are mapped to health categories (red/yellow/green/unknown)
   - Customer names are slugified for filesystem-safe folder names

3. **Empty Fields Handling**
   - Empty renewal dates or next_touch_due fields are handled gracefully by the dashboard script
   - The seed script creates files even when some fields are missing or blank

## Example Workflow

1. User provides a CSV export (e.g., `hubspot-crm-exports-cs-all-customers-2026-07-13.csv`)
2. The seed script processes the CSV and creates customer directories:
   ```
   customers/
   ├── masco-corporation/
   │   └── index.md
   ├── nestle-purina-petcare-global-resources-inc/
   │   └── index.md
   ├── zwift-inc/
   │   └── index.md
   └── ...
   ```

3. The dashboard script parses all customer files and generates a prioritized view:
   ```
   # Customer Dashboard — 2026-07-13
   Total accounts: 19
   Health: {'green': 1, 'yellow': 1, 'red': 0, 'unknown': 0}

   No renewals in the next 30 days.

   No overdue touches.

   ## Top priority
   - Tridonic GmbH & Co KG [yellow] renewal=2026-10-15
   - Polar Electro Oy [green] renewal=soon
   ```

## User Preference Alignment

The user prefers:
1. **Concise output**: The dashboard is designed to return just the essential information without fluff
2. **Direct results**: No meta-commentary or process descriptions unless explicitly requested
3. **Clean, portable structure**: Markdown files with YAML frontmatter provide maximum portability and readability

## Pitfalls to Avoid

1. **App-specific formats**: Don't use Tolaria or Obsidian schemas until the user needs them
2. **Overcomplicated directory structures**: Keep one subfolder per customer with simple index.md files
3. **Inconsistent field handling**: Ensure all CSV fields are mapped to the frontmatter schema consistently
4. **Blank field crashes**: The dashboard script must handle empty or missing fields gracefully

## Sample Output from Seed Script

```
Created 19 customers, skipped 0 existing.
```

The seed script handles edge cases like:
- Duplicate customer names (slugified to avoid conflicts)
- Missing or malformed date fields
- Empty ARR values that can't be parsed as numbers