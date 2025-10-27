<!-- a9539a99-996f-464b-b49b-e57d39c7bf02 86c4fc84-cc84-4207-be8f-1d860a6bf8f8 -->
# Fix Invalid Report Periods

## Overview

Create script `core/scripts/verify/fix_invalid_periods.py` to:

1. Identify records with invalid `period` values (outside 2000-01 to 2025-12)
2. Fix using `parsed_data->>'period_start'[:7]`
3. Log all changes to `diagnostics/fixed_invalid_periods.log`

## Implementation Strategy

### Detection Logic

Identify problematic records:

- `period < '2000-01' OR period > '2025-12'` - outside valid range
- Skip records where `parser_version IS NULL` (unparsed)
- Only process records with valid `parsed_data->>'period_start'`

### Correction Algorithm

For each invalid record:

1. Extract `period_start` from `parsed_data->>'period_start'`
2. Validate format (YYYY-MM-DD)
3. Generate corrected period: `period_start[:7]` (YYYY-MM)
4. Update `broker_reports.period` if different
5. Log: report_id, old_period, new_period, reason

### Logging Format

```
[TIMESTAMP] ID=<id> | OLD='<old>' | NEW='<new>' | REASON='<reason>' | FILE='<filename>'
```

### Database Operations

Use `BrokerReportOperations.execute_raw_query()` for:

- SELECT: Find invalid records
- UPDATE: Fix period values with transaction safety

Update query:

```sql
UPDATE broker_reports 
SET period = %s, updated_at = NOW() 
WHERE id = %s
```

## Files to Create/Modify

- **Create**: `core/scripts/verify/fix_invalid_periods.py` - main script
- **Create**: `diagnostics/fixed_invalid_periods.log` - change log
- **Modify**: `Makefile` - add `fix-periods` target

## Validation

After execution:

- Count fixed records
- Verify no periods outside 2000-2025 range remain
- Check log file completeness

### To-dos

- [ ] Create core/scripts/query/fetch_summary.py with SQL query execution and markdown formatting
- [ ] Add fetch-summary target to Makefile