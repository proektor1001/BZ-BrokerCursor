<!-- 7007df9d-fb40-4ad6-829e-2cbc20ac0304 c06f9854-7628-443b-97be-ffa408f1056c -->
# Reimport and Parse Fresh Source

## Overview

Recover the system by reimporting all files from inbox with proper duplicate handling, parsing all reports with error logging, and ensuring complete synchronization between database and filesystem.

## Current Situation

- Database: 18 records with old file hashes (from different file versions)
- Archive: Empty (all files were removed during cleanup)
- Inbox: 24 HTML files ready for import
- Need: Fresh import with duplicate detection and full parsing

## Implementation Strategy

### Phase 1: Pre-Import Analysis

**Goal:** Understand what we have and what needs to be done.

**Actions:**

1. Count files in inbox: 24 HTML files
2. Check database: 18 existing records with old hashes
3. Decision: **Keep existing DB records** OR **clean DB and start fresh**

**Recommendation:** Clean database and start fresh for consistency:

```sql
TRUNCATE TABLE broker_reports RESTART IDENTITY CASCADE;
TRUNCATE TABLE import_log RESTART IDENTITY CASCADE;
```

### Phase 2: Import with Duplicate Detection

**Goal:** Import all files from inbox to database with proper duplicate handling.

**Process:**

1. Scan `modules/broker-reports/inbox/*.html`
2. For each file:

      - Read file content
      - Calculate `file_hash = SHA-256(content)`
      - Extract metadata from filename:
          - Account: `4000T49` or `S000T49`
          - Period: from filename (e.g., `2023-05`)
      - **Detect broker**: All files with `T49` accounts are **SBER** reports
      - Check if hash exists in database:
          - **If hash exists:** Log as `duplicate_detected` in `import_log`, skip import
          - **If hash unique:** 
              - Insert into `broker_reports`:
                  - `broker = 'sber'`
                  - `account`, `period`, `file_name`, `file_hash`
                  - `html_content = content`
                  - `processing_status = 'raw'`
                  - `file_size = len(content)`
              - Log as `import_success` in `import_log`
              - Move file to `archive/`

**Implementation:**

Use existing script: `core/scripts/import/import_reports.py` OR create enhanced version with:

- Proper broker detection (fix the tinkoff bug)
- Hash-based duplicate checking
- Detailed import logging

**Expected Result:** 18-24 records in database, all files moved to archive

### Phase 3: Fix Broker Detection

**Critical Fix:** Update import script or database to correctly identify broker as 'sber':

**Files with accounts `4000T49` and `S000T49` are SBER reports**, not Tinkoff!

Evidence:

- Russian report format: "Отчет брокера" 
- Account naming convention: T49 suffix
- HTML structure matches Sber parser expectations

**Action:** Either:

- A) Fix `detect_broker_from_filename()` in `import_reports.py` lines 42-43
- B) Update database after import: `UPDATE broker_reports SET broker='sber' WHERE broker='tinkoff'`

### Phase 4: Mass Parsing with Error Handling

**Goal:** Parse all raw reports and populate `parsed_data`.

**Process:**

1. Query: `SELECT * FROM broker_reports WHERE processing_status='raw' ORDER BY id`
2. For each report:

      - Get `html_content`
      - **Parse with SberHtmlParser:**
          - Extract balance, trades, instruments, etc.
          - Format as JSON v2.0
      - **On success:**
          - Update: `processing_status='parsed'`, `parsed_data={data}`, `processed_at=NOW()`
          - Log success
      - **On error:**
          - Update: `processing_status='error'`, `error_log={error_message}`
          - Append to `diagnostics/parsing_errors.log`:
       ```
       [2025-10-23T16:30:00] ID: 5 | Account: 4000T49 | Period: 2023-05
       Error: ValueError: Could not extract balance
       ---
       ```

          - Continue with next report (don't fail entire batch)

**Implementation:**

```python
# Use core/scripts/parse/parse_reports.py as base
# Add error logging to file
# Use: ops.update_report_status(report_id, status='parsed'/'error', parsed_data, error_log)
```

**Expected Result:** All reports either `parsed` or `error`, no `raw` remaining

### Phase 5: Generate Comprehensive Reports

**Create `diagnostics/import_result.md`:**

```markdown
# Import Result Report

**Generated:** {timestamp}

## Summary

- Files in Inbox: 24
- Successfully Imported: {count}
- Duplicates Detected: {dup_count}
- Files Moved to Archive: {count}
- Import Errors: {error_count}

## Detailed Import Log

| File Name | Hash | Status | Notes |
|-----------|------|--------|-------|
| ... | ... | imported | ✅ New |
| ... | ... | duplicate | 🔁 Already exists |

## Database State

- Total Records: {count}
- Processing Status:
 - raw: {raw_count}
 - parsed: {parsed_count}
 - error: {error_count}
```

**Create `diagnostics/parsing_completion_report.md`:**

```markdown
# Parsing Completion Report

**Generated:** {timestamp}

## Summary Statistics

- Total Reports: {total}
- Successfully Parsed: {success}
- Parsing Errors: {errors}
- Success Rate: {percentage}%

## Detailed Results

| ID | Broker | Account | Period | Status | Notes |
|----|--------|---------|--------|--------|-------|
| 1  | sber   | 4000T49 | 2023-12 | parsed | ✅ OK |
| 2  | sber   | S000T49 | 2023-05 | parsed | ✅ OK |
| ...| ...    | ...     | ...     | error  | ❌ {error} |

## Errors Detail

See: diagnostics/parsing_errors.log

## System State

- Archive Files: {count}
- Database Records: {count}
- Synchronization: ✅ Match
```

**Terminal Output:**

```
🔄 Import & Parsing Complete
════════════════════════════════════
📥 Import: {imported} new, {dup} duplicates
🔄 Parsing: {success} success, {errors} errors
📁 Archive: {count} files
📊 Database: {count} records
✅ System synchronized!
```

### Phase 6: Final Verification

Run integrity check to confirm:

- All files in archive match database records (by hash)
- All records have `file_hash` populated
- Parsed records have `parsed_data` populated
- Inbox is empty
- No `raw` status remaining (all either `parsed` or `error`)

## Implementation Order

1. **Pre-import analysis** - Decide on database cleanup
2. **Import with duplicates** - Process all inbox files
3. **Fix broker detection** - Ensure broker='sber'
4. **Mass parsing** - Parse all raw reports
5. **Generate reports** - Create comprehensive logs
6. **Verify** - Run final integrity check

## Files to Create/Modify

**New Files:**

- `diagnostics/import_result.md` - Import summary
- `diagnostics/parsing_errors.log` - Parsing errors (if any)
- `diagnostics/parsing_completion_report.md` - Parsing summary

**Updated:**

- `import_log` table - All import operations logged
- `broker_reports` table - All records updated with parsed data

## Success Criteria

- ✅ All inbox files processed (imported or marked as duplicate)
- ✅ All unique files moved to archive
- ✅ Inbox is empty
- ✅ Archive contains all imported files
- ✅ All records have `parsed_data` or `error_log`
- ✅ No `raw` status remaining
- ✅ Database-filesystem fully synchronized
- ✅ Comprehensive logs generated

## Error Handling

- **Duplicate files:** Log and skip, don't fail
- **Parsing errors:** Mark as error, log details, continue
- **File system errors:** Log and continue with next file
- **Always complete the process** even with partial failures
- **Generate reports** regardless of errors

## Important Notes

1. **Broker Detection Bug:** Fix T49 accounts being labeled as 'tinkoff'
2. **Hash Mismatch:** Old DB hashes won't match new file hashes (expected)
3. **Clean Start Option:** Consider truncating tables for fresh start
4. **Idempotency:** Can run multiple times safely with duplicate detection