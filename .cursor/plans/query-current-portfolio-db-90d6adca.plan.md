<!-- 90d6adca-35bd-4f94-8eca-e2f0f2d0da46 c4b3d47d-a057-420e-9b7e-be6074380902 -->
# Fix Securities Portfolio Parser

## Overview

The parser is failing because it searches for "Портфель Ценных Бумаг" inside a `<td>` element, but in the actual HTML, this text is in a `<p>` tag before the table. We need to fix the search logic and then reparse all reports.

## Root Cause Analysis

Current code looks for:

```python
table.find('td', string=lambda x: x and 'Портфель Ценных Бумаг' in x)
```

Actual HTML structure:

```html
<p style="line-height:0.7;">
<br>Портфель Ценных Бумаг</br>
...
</p>
<table>...</table>
```

## Implementation Steps

### 1. Fix Parser Logic

Modify `core/parsers/sber_html_parser.py`:

**Current broken approach:**

- Searches for text inside table `<td>` elements

**New working approach:**

- Find the `<p>` tag containing "Портфель Ценных Бумаг"
- Get the next `<table>` sibling element
- Parse that table with the correct column mapping
- Handle 18-column table structure (including "Площадка" separator rows)

**Key fixes:**

- Use `soup.find('p', string=lambda x: x and 'Портфель Ценных Бумаг' in str(x))` or search in text
- Use `find_next('table')` to get the portfolio table
- Skip rows with `class="table-header"` and `class="rn"` (row numbers)
- Skip rows starting with "Площадка:" (colspan rows)
- Parse 18-column data rows correctly

### 2. Create Reparse Script

Create `core/scripts/parse/reparse_sber_reports.py` that:

- Fetches all reports with `broker='sber'` and `parser_version='2.0'`
- Re-extracts `html_content` from database
- Runs updated parser
- Updates `parsed_data` with new `securities_portfolio`
- Logs statistics (before/after portfolio lengths)
- Generates diagnostic report

### 3. Generate Diagnostic Report

Output `diagnostics/securities_portfolio_fix_summary.md` with:

- Total reports processed
- Reports with portfolios before: 0
- Reports with portfolios after: X
- Sample securities extracted
- Any parsing errors encountered

### 4. Verification

Run the fixed `fetch_portfolio.py` to confirm:

- Non-empty `securities_portfolio` arrays
- Actual securities data (GOLD ETF, etc.)
- Proper field extraction

## Files to Modify/Create

- **Modify**: `core/parsers/sber_html_parser.py` (fix `_extract_securities_portfolio()`)
- **Create**: `core/scripts/parse/reparse_sber_reports.py` (~150 lines)
- **Generate**: `diagnostics/securities_portfolio_fix_summary.md`
- **Generate**: `diagnostics/parsed_reports_after_fix.json` (20 sample reports)
- **Generate**: `diagnostics/securities_portfolio_errors.json` (error log)
- **Update**: `Makefile` (add `reparse-sber-portfolio` target)
- **Test**: Run `python core/scripts/query/fetch_portfolio.py` after fix

## Makefile Integration

Add target in `Makefile`:

```makefile
reparse-sber-portfolio:
	@echo "Reparsing Sber reports to fix securities_portfolio..."
	python core/scripts/parse/reparse_sber_reports.py
```

## Success Criteria

- ✅ Minimum 50% of reports have non-empty `securities_portfolio`
- ✅ Each security has valid `name`, `isin`, `quantity_end`, `price_end`
- ✅ Numeric fields properly converted (float/int or None)
- ✅ Parser tested on multiple report formats
- ✅ JSON export contains verifiable sample data
- ✅ SQL verification: `fetch_portfolio.py` returns ≥10 securities
- ✅ Exit code 0 on success, 1 on failure (<50% success rate)

## Expected Results

After fix:

- 53 reports with non-empty `securities_portfolio` arrays
- Each report contains actual securities: GOLD ETF, SBGB ETF, RSHE ETF, etc.
- Portfolio query returns actual current holdings
- Total portfolio value calculated correctly

### To-dos

- [ ] Create core/scripts/query/fetch_portfolio.py with SQL query logic to extract securities_portfolio from latest reports per broker/account
- [ ] Generate diagnostics/current_portfolio_report.md with portfolio table and source verification
- [ ] Save the actual SQL query to diagnostics/sql_portfolio_query.sql for transparency
- [ ] Add query-portfolio target to Makefile for easy execution
- [ ] Run the script and verify output reports contain valid portfolio data from database